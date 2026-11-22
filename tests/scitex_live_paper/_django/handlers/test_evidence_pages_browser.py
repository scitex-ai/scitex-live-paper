"""Actual Django HTTP pages, authenticated assets and claim graphs in Chromium."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import os
import shutil
import struct
import threading
import zipfile
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.handlers.wsgi import WSGIHandler

from .test_evidence_pages import evidence_host  # noqa: F401 - shared real host fixture

if os.environ.get("LP_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright
else:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


class QuietHandler(WSGIRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def mounted_browser():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:
            if os.environ.get("LP_REQUIRE_BROWSER") == "1":
                raise
            pytest.skip(f"Chromium unavailable: {str(error).splitlines()[0]}")
        try:
            yield browser
        finally:
            browser.close()


@pytest.mark.parametrize("width,color", [(1440, "light"), (390, "light"), (390, "dark")])
def test_mounted_manuscript_graph_and_private_assets(evidence_host, mounted_browser, width, color):
    # Arrange
    server = make_server("127.0.0.1", 0, WSGIHandler(), handler_class=QuietHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}/mounted/paper/"
    try:
        context = mounted_browser.new_context(
            viewport={"width": width, "height": 850}, color_scheme=color,
            extra_http_headers={"Authorization": "Bearer alice"},
        )
        page = context.new_page()
        errors, failures, violations = [], [], []
        observed = {}
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("requestfailed", lambda request: failures.append(request.url))
        page.add_init_script("""document.addEventListener('securitypolicyviolation',
            event => window.cspViolations = [...(window.cspViolations || []),
                event.violatedDirective + ': ' + event.blockedURI]);""")
        # Act
        response = page.goto(base + "paper.html?project=alice&working_dir=selected")
        observed["paper_status"] = response.status
        page.wait_for_selector("html[data-lp-paper-ready]", state="attached")
        observed["stated_value"] = page.locator("mark#claim-value").inner_text().startswith("20")
        observed["author_images"] = page.locator("img").count()
        page.click("mark#claim-value a")
        page.wait_for_selector("#lp-claim-panel [data-lp-rendered] svg")
        panel = page.locator("#lp-claim-panel")
        observed["state"] = panel.get_attribute("data-support")
        observed["values_differ"] = "20" in panel.inner_text() and "21" in panel.inner_text()
        observed["panel_failures"] = page.locator("#lp-claim-panel g.node[data-lp-failure]").count()
        page.keyboard.press("Escape")
        observed["closed"] = panel.is_hidden()
        observed["focus_restored"] = page.locator("mark#claim-value a").evaluate("e => e === document.activeElement")
        screenshots = os.environ.get("LP_SCREENSHOT_DIR")
        if screenshots:
            Path(screenshots).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(screenshots) / f"django-paper-{width}-{color}.png"))
        violations.extend(page.evaluate("window.cspViolations || []"))
        page.goto(base + "graph.html?project=alice&claim_id=value&working_dir=selected")
        page.wait_for_selector("g.node[data-lp-failure]")
        observed["graph_failures"] = page.locator("g.node[data-lp-failure]").count()
        page.locator("g.node[data-lp-failure]").click()
        observed["node_details"] = page.locator("#lp-dag-overlay").is_visible()
        violations.extend(page.evaluate("window.cspViolations || []"))
        refused = page.goto(base + "assets?project=bob&name=assets/paper.js")
        observed.update(refused_status=refused.status, errors=errors, failures=failures, violations=violations)
        context.close()
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    # Assert
    assert observed == {
        "paper_status": 200, "stated_value": True, "author_images": 0,
        "state": "not_supported", "values_differ": True, "panel_failures": 1,
        "closed": True, "focus_restored": True, "graph_failures": 1,
        "node_details": True, "refused_status": 403, "errors": [], "failures": [], "violations": [],
    }


@pytest.mark.parametrize("width,embed", [(1440, False), (390, True)])
def test_reader_layout_keeps_pdf_and_claim_evidence_connected(
    evidence_host, mounted_browser, width, embed
):
    # Arrange
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "rich-provider.pdf"
    root = evidence_host.roots["alice"]
    shutil.copyfile(fixture, root / "manuscript.pdf")
    registry = root / "claims.json"
    claims = json.loads(registry.read_text())
    claims["claims"][0].update(claim_id="value", claim_type="value")
    registry.write_text(json.dumps(claims))
    claim_id = "value"
    (root / "pdf-anchors.json").write_text(json.dumps({
        "pdf_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "anchors": {claim_id: {"page": 1, "bbox": [50, 200, 100, 220]}},
    }))
    script = b"print('computed value')\n"
    (root / "analysis.py").write_bytes(script)
    graph = evidence_host.reports["alice"]["claims"][0]["graph"]
    graph["nodes"].append({
        "id": "p1", "kind": "process", "label": "recorded-run",
        "script": {"file": "analysis.py", "hash": hashlib.sha256(script).hexdigest()},
    })
    grids = gzip.compress(struct.pack(">IIII", 2051, 10, 2, 2) + bytes(range(40)))
    (root / "samples.gz").write_bytes(grids)
    graph["nodes"].append({
        "id": "data", "kind": "input", "label": "samples.gz",
        "hash": hashlib.sha256(grids).hexdigest(),
    })
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("notes.txt", "Archived source notes")
    stored_archive = archive_bytes.getvalue()
    (root / "sources.zip").write_bytes(stored_archive)
    graph["nodes"].append({
        "id": "archive", "kind": "input", "label": "sources.zip",
        "hash": hashlib.sha256(stored_archive).hexdigest(),
    })
    graph["edges"].append({"source": "archive", "target": "p1"})
    graph["edges"].append({"source": "data", "target": "p1"})
    graph["edges"].append({"source": "p1", "target": "output"})
    server = make_server(
        "127.0.0.1", 0, StaticFilesHandler(WSGIHandler()), handler_class=QuietHandler
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    context = mounted_browser.new_context(
        viewport={"width": width, "height": 850},
        extra_http_headers={"Authorization": "Bearer alice"},
    )
    try:
        # Act
        page = context.new_page()
        base = f"http://127.0.0.1:{server.server_port}/mounted/paper/"
        response = page.goto(base + f"?project=alice&embed={int(embed)}")
        document = page.get_by_role("region", name="Manuscript", exact=True)
        document.locator("canvas").first.wait_for()
        page.get_by_role("link", name="Download PDF", exact=True).wait_for()
        inspector = page.get_by_role("complementary", name="Claim evidence")
        row = inspector.locator(".scitex-rich-pdf-feed button").first
        pdf = document.bounding_box()
        if embed:
            arrangement_ok = not inspector.is_visible()
            toggle = page.get_by_role("button", name="Claim evidence", exact=True)
            toggle.click()
            row.wait_for()
            navigation_ok = inspector.evaluate(
                "node => getComputedStyle(node).position === 'absolute'"
            )
            toggle.click()
        else:
            row.wait_for()
            evidence = inspector.bounding_box()
            arrangement_ok = (
                abs(evidence["y"] - pdf["y"]) < 2
                and evidence["x"] >= pdf["x"] + pdf["width"]
            )
            navigation_ok = pdf["width"] > 600
        scroller = document.evaluate("""node => ({
            document: node.scrollTop,
            host: window.scrollY,
            evidence: document.querySelector('#live-paper-claims').scrollTop,
        })""")
        page.mouse.move(pdf["x"] + pdf["width"] / 2, pdf["y"] + pdf["height"] / 2)
        page.mouse.wheel(0, 450)
        page.wait_for_function(
            "document.querySelector('.lp-reader-document').scrollTop > 0"
        )
        isolated_scroll = document.evaluate("""(node, before) =>
            window.scrollY === before.host &&
            document.querySelector('#live-paper-claims').scrollTop === before.evidence
        """, scroller)
        overlay = document.locator('[data-overlay-id="value"]')
        overlay.wait_for()
        mark_status = overlay.get_attribute("data-status")
        status_color = page.wait_for_function("""() => {
            const element = document.querySelector('[data-overlay-id="value"]');
            if (!element) return false;
            const style = getComputedStyle(element);
            const verified = style.getPropertyValue("--lp-status-verified").trim();
            return Boolean(verified) && style.getPropertyValue("--lp-rich-mark").trim() === verified;
        }""").json_value()
        overlay.scroll_into_view_if_needed()
        page.wait_for_timeout(190)
        snapped = overlay.evaluate("""button => {
            const rect = button.getBoundingClientRect();
            return document.elementFromPoint(rect.left - 3, rect.top + rect.height / 2) === button;
        }""")
        overlay.evaluate("""button => {
            document.dispatchEvent(new Event('scroll'));
            button.dispatchEvent(new PointerEvent('pointerenter', {pointerType: 'mouse'}));
        }""")
        page.wait_for_timeout(190)
        preview = inspector.get_by_role("region", name="Claim detail")
        hover_during_scroll = preview.count() > 0
        overlay.hover()
        preview.get_by_role("heading", name="Evidence graph (recorded-test-evidence)").wait_for()
        graph = preview.locator(".lp-claim-dag svg")
        graph.wait_for()
        reference = preview.get_by_role("button", name="Run analysis.py", exact=True)
        reference.hover()
        preview.get_by_text("print('computed value')", exact=True).wait_for()
        graph.locator("g.lp-source-highlight").wait_for()
        language = preview.locator("pre code").get_attribute("class")
        preview_has_background = preview.locator(".lp-source-preview pre").evaluate(
            "node => getComputedStyle(node).backgroundColor !== 'rgba(0, 0, 0, 0)'"
        )
        comment_height = preview.get_by_role("button", name="Comment", exact=True).evaluate(
            "node => node.getBoundingClientRect().height"
        )
        source_lists = preview.get_by_text("Browse sources", exact=True).count()
        source_link_is_claim_bound = "claim_id=value" in preview.get_by_role(
            "link", name="Open full evidence graph"
        ).get_attribute("href")
        trace_summary = page.get_by_role("link", name="Calculation traces", exact=False)
        trace_summary.wait_for()
        marked = overlay.get_attribute("data-appearance") == "highlight"
        source_selected = reference.get_attribute("aria-pressed")
        reference.click()
        gzip_node = preview.get_by_role("button", name="Input samples.gz", exact=True)
        gzip_node.hover()
        page.wait_for_timeout(110)
        pinned_source = preview.get_by_text("print('computed value')", exact=True).is_visible()
        gzip_node.click()
        preview.get_by_text("Gzip-compressed file.", exact=False).wait_for()
        guessed_images = preview.locator(".lp-source-preview canvas, .lp-source-preview img").count()
        preview.get_by_role("button", name="Input sources.zip", exact=True).click()
        archive_member = preview.get_by_role("button", name="notes.txt", exact=True)
        archive_member.click()
        preview.get_by_text("Archived source notes", exact=True).wait_for()
        preview.get_by_role("button", name="Archive contents", exact=True).click()
        archive_member.wait_for()
        archive_round_trip = archive_member.is_visible()
        page.keyboard.press("Escape")
        preview.wait_for(state="hidden")
        overlay.focus()
        overlay.press("Enter")
        preview.wait_for()
        page.keyboard.press("Escape")
        preview.wait_for(state="hidden")
        focus_restored = overlay.evaluate("button => button === document.activeElement")
        if embed:
            toggle.click()
        row.click()
        overlay_selected = overlay.get_attribute("aria-current") == "true"
        with page.expect_download() as pending:
            page.get_by_role("link", name="Download PDF", exact=True).click()
        download = pending.value
        page.get_by_text("PDF variants", exact=True).click()
        exports = []
        page_count = document.locator(".stx-pdf-page").count()
        for title in ("With highlights", "With highlights and selected graph"):
            with page.expect_download() as generated:
                page.get_by_role("button", name=title, exact=True).click()
            file = generated.value.path().read_bytes()
            count = page.evaluate("""async encoded => {
                const pdfjs = await import('/static/live_paper/pdfjs/pdf.min.mjs');
                pdfjs.GlobalWorkerOptions.workerSrc = '/static/live_paper/pdfjs/pdf.worker.min.mjs';
                const data = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
                const pdf = await pdfjs.getDocument({data}).promise;
                const count = pdf.numPages;
                await pdf.destroy();
                return count;
            }""", base64.b64encode(file).decode())
            exports.append((generated.value.suggested_filename, count, file != fixture.read_bytes()))
        bookmarks = page.locator(".lp-pdf-bookmarks")
        bookmarks.locator("summary").click()
        bookmarks.get_by_role("button", name="References").click()
        reference = document.locator(".lp-bibliography-highlight", has_text="Second page destination")
        reference.wait_for(state="attached")
        reference.scroll_into_view_if_needed(timeout=5000)
        bookmarks_work = bookmarks.evaluate("node => !node.open") and reference.is_visible()
        observed = (
            response.status, arrangement_ok, navigation_ok, isolated_scroll,
            row.get_attribute("aria-current"),
            preview.is_visible(),
            page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
            overlay_selected,
            download.suggested_filename,
            download.path().read_bytes() == fixture.read_bytes(),
            source_selected, source_link_is_claim_bound, marked, focus_restored,
            guessed_images, mark_status, status_color, language, source_lists,
            snapped, hover_during_scroll, pinned_source, archive_round_trip,
            page.locator(".lp-rich-preview").count(), preview_has_background, comment_height >= 30, bookmarks_work, exports,
        )
        screenshots = os.environ.get("LP_SCREENSHOT_DIR")
        if screenshots:
            Path(screenshots).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(screenshots) / f"reader-workspace-{width}.png"))
    finally:
        context.close()
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()

    # Assert
    assert observed == (
        200, True, True, True, "true", True, True, True, "manuscript.pdf", True, "true", True, True, True, 0, "verified", True, "language-python", 0, True, False, True, True, 0, True, True, True,
        [("manuscript-highlighted.pdf", page_count, True), ("manuscript-with-evidence-graph.pdf", page_count + 1, True)],
    )
