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
        zoom = page.get_by_role("group", name="Evidence graph controls")
        zoom.get_by_role("button", name="Zoom in on evidence graph").click()
        assert zoom.get_by_text("125%", exact=True).is_visible()
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
    from scitex_live_paper.evidence.citations import CITATION_REPORT, citation_verification
    citation = {"status": "verified", "claim_id": "value", "resolver_source": "fixture provider",
                "reason": "Fixture verification", "link": "https://example.org/article"}
    (root / CITATION_REPORT).write_text(json.dumps(citation_verification(fixture, {"fixture": citation})))
    registry = root / "claims.json"
    claims = json.loads(registry.read_text())
    claims["claims"] = [dict(claims["claims"][0], claim_id="value", claim_type="value")]
    claims["claims"].extend([
        {"claim_id": "classifier-sentence", "claim_type": "text",
         "file_path": "manuscript.pdf", "claim_value": "The held-out classifier score improved.",
         "source_file": "results/summary.json"},
        {"claim_id": "test-statistic", "claim_type": "statistic", "file_path": "manuscript.pdf"},
        {"claim_id": "test-table", "claim_type": "table", "file_path": "manuscript.pdf"},
        {"claim_id": "test-figure", "claim_type": "figure", "file_path": "manuscript.pdf"},
    ])
    registry.write_text(json.dumps(claims))
    claim_id = "value"
    (root / "pdf-anchors.json").write_text(json.dumps({
        "pdf_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "anchors": {
            claim_id: {"page": 1, "bbox": [50, 200, 100, 220]},
            "classifier-sentence": {"page": 2, "bbox": [50, 160, 240, 176]},
        },
    }))
    evidence_host.navigation["alice"] = lambda path: {
        "file": "/alice/demo/blob/" + path.as_posix(),
        "folder": "/alice/demo/",
    }
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
        "hash": hashlib.sha256(grids).hexdigest(), "author_registered": True,
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
        graph_requests = []
        page.on("request", lambda request: graph_requests.append(request.url)
                if "/api/dag?" in request.url else None)
        base = f"http://127.0.0.1:{server.server_port}/mounted/paper/"
        response = page.goto(base + f"?project=alice&embed={int(embed)}")
        document = page.get_by_role("region", name="Manuscript", exact=True)
        document.locator("canvas").first.wait_for()
        page.get_by_role("link", name="Download PDF", exact=True).wait_for()
        navigation = page.get_by_role("navigation", name="PDF navigation")
        navigation_toggle = navigation.locator(".rpdf-nav-toggle")
        assert navigation_toggle.get_attribute("aria-expanded") == "true"
        assert navigation.is_visible()
        assert navigation.bounding_box()["x"] < document.bounding_box()["x"]
        assert not page.get_by_text("Bundle diagnostics", exact=True).count()
        assert not page.get_by_text("Archive event log", exact=True).count()
        assert page.get_by_role("combobox", name="PDF theme").is_visible()
        root = page.locator("#live-paper-root")
        root.evaluate("node => node.dataset.paperStage = 'preprint'")
        assert document.locator(".stx-pdf-page").first.evaluate(
            "node => getComputedStyle(node, '::after').content"
        ) == '"Preprint"'
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
                abs(evidence["y"] - page.locator(".lp-manuscript-pane").bounding_box()["y"]) < 2
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
        first_layout = graph.get_attribute("id")
        processor = graph.locator("g.node.run").first
        assert "analysis.py" in processor.text_content()
        assert hashlib.sha256(script).hexdigest()[:6] in processor.text_content()
        assert hashlib.sha256(script).hexdigest() not in processor.text_content()
        marked_source = graph.locator("g.node.author_source")
        assert "✒ Author-registered source" in marked_source.text_content()
        assert marked_source.locator(":scope > polygon").evaluate(
            "node => getComputedStyle(node).stroke"
        ) == "rgb(37, 135, 115)"
        viewport = preview.get_by_role("region", name="Evidence graph viewport")
        zoom_controls = preview.get_by_role("group", name="Evidence graph controls")
        before_zoom = graph.bounding_box()["width"]
        pdf_before_zoom = document.evaluate(
            "pane => [pane.scrollTop, pane.querySelector('canvas').getBoundingClientRect().width]"
        )
        zoom_in = zoom_controls.get_by_role("button", name="Zoom in on evidence graph")
        for _ in range(3):
            zoom_in.click()
        assert zoom_controls.get_by_text("175%", exact=True).is_visible()
        assert graph.bounding_box()["width"] > before_zoom
        assert viewport.get_attribute("data-can-pan") is not None
        viewport.scroll_into_view_if_needed()
        viewport.evaluate("node => node.scrollLeft = 0")
        box = viewport.bounding_box()
        x, y = box["x"] + box["width"] * 0.8, box["y"] + 3
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 40, y, steps=4)
        page.mouse.up()
        assert viewport.evaluate("node => node.scrollLeft") > 0
        assert document.evaluate(
            "pane => [pane.scrollTop, pane.querySelector('canvas').getBoundingClientRect().width]"
        ) == pdf_before_zoom
        viewport.hover()
        page.keyboard.press("Control+-")
        assert zoom_controls.get_by_text("150%", exact=True).is_visible()
        page.keyboard.press("Control+0")
        assert zoom_controls.get_by_text("100%", exact=True).is_visible()
        assert document.evaluate(
            "pane => [pane.scrollTop, pane.querySelector('canvas').getBoundingClientRect().width]"
        ) == pdf_before_zoom
        download_graph = zoom_controls.get_by_text("Download graph", exact=True)
        for format, signature in (("SVG", b"<svg"), ("PNG", bytes.fromhex("89504e470d0a1a0a"))):
            download_graph.click()
            with page.expect_download() as pending_graph:
                zoom_controls.get_by_role("button", name=format, exact=True).click()
            image = pending_graph.value
            assert image.suggested_filename == "evidence-graph." + format.lower()
            assert image.path().read_bytes().startswith(signature)

        reference = preview.get_by_role("button", name="Run analysis.py", exact=True)
        reference.hover()
        preview.get_by_text("print('computed value')", exact=True).wait_for()
        graph.locator("g.lp-source-highlight").wait_for()
        language = preview.locator("pre code").get_attribute("class")
        file_action = preview.get_by_role("link", name="Open file", exact=True)
        folder_action = preview.get_by_role("link", name="Open containing folder", exact=True)
        source_action_urls = (
            file_action.get_attribute("href"), folder_action.get_attribute("href"),
            file_action.get_attribute("target"),
        )
        code = preview.locator(".lp-source-preview pre")
        pdf_theme = page.get_by_role("combobox", name="PDF theme")
        assert pdf_theme.input_value() == "auto"
        raster = document.locator(".stx-pdf-page > canvas:first-child").first
        graph_card = preview.locator(".lp-claim-dag")
        graph_shape = graph.locator("g.node.failing > :is(rect, polygon, path)").first
        graph_themes = []
        code_colors = []
        for theme in ("light", "dark"):
            page.evaluate("""theme => {
              document.documentElement.dataset.theme = theme;
              document.querySelectorAll("[data-theme]").forEach(node => node.dataset.theme = theme);
            }""", theme)
            code_colors.append(code.evaluate("node => getComputedStyle(node).color"))
            graph_themes.append((
                graph_card.evaluate("node => getComputedStyle(node).backgroundColor"),
                graph_shape.evaluate("node => getComputedStyle(node).fill"),
                graph_shape.evaluate("node => getComputedStyle(node).stroke"),
            ))
            pdf_filter = raster.evaluate("node => getComputedStyle(node).filter")
            assert (pdf_filter != "none") == (theme == "dark")
        assert graph.get_attribute("id") == first_layout
        assert graph_themes[0][:2] != graph_themes[1][:2]
        assert graph_themes[0][2] == graph_themes[1][2] == "rgb(248, 81, 73)"
        assert overlay.evaluate("node => getComputedStyle(node).filter") == "none"
        pdf_theme.select_option("light")
        assert raster.evaluate("node => getComputedStyle(node).filter") == "none"
        pdf_theme.select_option("dark")
        assert "invert" in raster.evaluate("node => getComputedStyle(node).filter")
        assert page.evaluate("localStorage.getItem('live-paper.pdf-theme')") == "dark"
        pdf_theme.select_option("auto")
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
        before_reopen = len(graph_requests)
        overlay.press("Enter")
        preview.wait_for()
        graph.wait_for()
        fresh_graph = (len(graph_requests) > before_reopen and graph.get_attribute("id") == first_layout)
        page.keyboard.press("Escape")
        preview.wait_for(state="hidden")
        focus_restored = overlay.evaluate("button => button === document.activeElement")
        if embed:
            toggle.click()
        row.click()
        overlay_selected = overlay.get_attribute("aria-current") == "true"
        all_claims_tab = inspector.get_by_role("tab", name="All claims", exact=False)
        all_claims_tab.click()
        preview.wait_for(state="hidden")
        type_tabs = inspector.get_by_role("tablist", name="Claim type")
        feed = inspector.locator(".scitex-rich-pdf-feed")
        search = inspector.get_by_role("searchbox", name="Search claims")
        assert feed.get_by_role("button").count() == 5
        type_tabs.get_by_role("tab", name="All", exact=True).press("ArrowRight")
        sentences = type_tabs.get_by_role("tab", name="Sentences", exact=True)
        assert sentences.get_attribute("aria-selected") == "true"
        assert all_claims_tab.get_attribute("aria-selected") == "true"
        assert feed.get_by_role("button").all_text_contents() == ["classifier-sentence"]
        search.fill("SCORE summary.json")
        assert feed.get_by_role("button").all_text_contents() == ["classifier-sentence"]
        type_tabs.get_by_role("tab", name="Values", exact=True).click()
        inspector.get_by_text("No claims match these filters.", exact=True).wait_for()
        search.fill("")
        assert feed.get_by_role("button").all_text_contents() == ["value"]
        for label, claim in (("Statistics", "test-statistic"), ("Tables", "test-table"), ("Figures", "test-figure")):
            type_tabs.get_by_role("tab", name=label, exact=True).click()
            assert feed.get_by_role("button").all_text_contents() == [claim]
        type_tabs.get_by_role("tab", name="All", exact=True).click()
        assert row.get_attribute("aria-current") == "true"
        all_claims_tab.press("ArrowLeft")
        preview.wait_for()
        with page.expect_download() as pending:
            page.get_by_role("link", name="Download PDF", exact=True).click()
        download = pending.value
        exports = []
        page_count = document.locator(".stx-pdf-page").count()
        for title in ("With highlights", "With highlights and selected graph"):
            page.locator("[aria-label='PDF download options']").click()
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
        assert inspector.get_by_role("tab", name="Selected claim").is_visible()
        sentence_overlay = document.locator('[data-overlay-id="classifier-sentence"]')

        def expect_pdf_jump():
            page.wait_for_function("""() => {
              const pane = document.querySelector('.lp-reader-document');
              const anchor = pane.querySelector('[data-overlay-id="classifier-sentence"]');
              if (!anchor) return false;
              const rect = anchor.getBoundingClientRect();
              const view = pane.getBoundingClientRect();
              return rect.top >= view.top && rect.bottom <= view.bottom;
            }""")
            assert page.evaluate("window.scrollY") == scroller["host"]
            assert sentence_overlay.get_attribute("aria-current") == "true"

        all_claims_tab.click()
        feed.get_by_role("button", name="test-statistic", exact=True).click()
        assert preview.get_by_role("button", name="Show in PDF").count() == 0
        all_claims_tab.click()
        document.evaluate("node => node.scrollTop = 0")
        feed.get_by_role("button", name="classifier-sentence", exact=True).press("Enter")
        expect_pdf_jump()
        document.evaluate("node => node.scrollTop = 0")
        preview.get_by_role("button", name="Show in PDF", exact=True).click()
        expect_pdf_jump()
        if embed:
            assert not inspector.is_visible()
            toggle.click()

        navigation.get_by_role("button", name="Page 1", exact=True).wait_for()
        thumbnail = navigation.locator("canvas").first
        thumbnail.wait_for()
        if not embed:
            pdf_page = document.locator(".stx-pdf-page").first
            thumbnail_width = thumbnail.bounding_box()["width"]
            pdf_width = pdf_page.bounding_box()["width"]

            thumbnail.hover()
            page.keyboard.press("Control+=")
            assert thumbnail.bounding_box()["width"] > thumbnail_width
            assert pdf_page.bounding_box()["width"] == pdf_width
            page.keyboard.press("Control+0")
            assert thumbnail.bounding_box()["width"] == thumbnail_width

            document.hover()
            page.keyboard.press("Control+=")
            page.wait_for_function(
                "width => parseFloat(document.querySelector('.stx-pdf-page')?.style.width) > width",
                arg=pdf_width,
            )
            assert thumbnail.bounding_box()["width"] == thumbnail_width
            page.keyboard.press("Control+0")
            page.wait_for_function(
                """width => {
                    const page = document.querySelector('.stx-pdf-page');
                    return page && Math.abs(page.getBoundingClientRect().width - width) < 1;
                }""",
                arg=pdf_width,
            )

        navigation.get_by_role("button", name="Page 2", exact=True).click()
        page.wait_for_function("document.querySelector('.lp-reader-document').scrollTop > 0")
        navigation.get_by_role("button", name="Bookmarks", exact=True).click()
        navigation.get_by_role("button", name="References", exact=True).click()
        reference = document.locator(".lp-bibliography-highlight", has_text="Second page destination")
        reference.wait_for(state="visible")
        assert reference.get_attribute("data-status") == "verified"
        assert "rgb(46, 160, 67)" in reference.evaluate("node => getComputedStyle(node).boxShadow")
        navigation_toggle.click()
        reference.evaluate("node => node.click()")
        citation_pane = inspector.get_by_role("region", name="Citation evidence")
        citation_pane.get_by_text("Scholar provider · fixture provider").wait_for()
        citation_pane.locator(".lp-claim-dag-svg").wait_for()
        citation_pane.get_by_role("button", name="Close", exact=True).click()
        if embed:
            page.get_by_role("button", name="Claim evidence", exact=True).click()
        navigation_toggle.click()
        docked_width = document.bounding_box()["width"]
        navigation_toggle.click()
        bookmarks_work = navigation.is_visible() and navigation_toggle.get_attribute("aria-expanded") == "false"
        if not embed:
            assert document.bounding_box()["width"] > docked_width
        navigation_toggle.click()
        assert navigation.get_by_role("button", name="References", exact=True).is_visible()
        navigation.get_by_role("button", name="References", exact=True).press("Escape")
        assert navigation.is_visible() and navigation_toggle.get_attribute("aria-expanded") == "false"
        assert navigation_toggle.evaluate("node => node === document.activeElement")
        share = page.get_by_role("button", name="Share", exact=True)
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: undefined})")
        if embed:
            page.get_by_role("button", name="Claim evidence", exact=True).click()
        inspector.get_by_role("tab", name="All claims", exact=False).click()
        share.click()
        paper_link = page.get_by_role("textbox", name="Share link").input_value()
        assert paper_link == base + "?project=alice&shared=1"
        row.click()
        share.click()
        claim_link = page.get_by_role("textbox", name="Share link").input_value()
        assert claim_link == paper_link + "&claim=value"
        linked = context.new_page()
        linked.goto(claim_link + f"&embed={int(embed)}")
        linked.get_by_role("region", name="Claim detail").wait_for()
        assert linked.locator(".lp-claim-detail").get_attribute("data-claim-id") == claim_id
        assert linked.locator('[data-overlay-id="value"]').get_attribute("aria-current") == "true"
        linked.close()
        format_tabs = page.get_by_role("tablist", name="Manuscript format")
        pdf_tab = format_tabs.get_by_role("tab", name="PDF", exact=True)
        html_tab = format_tabs.get_by_role("tab", name="HTML", exact=True)
        assert pdf_tab.get_attribute("aria-selected") == "true"
        original_url = page.url
        original_scroll = document.evaluate("node => node.scrollTop")
        html_tab.click()
        frame = page.frame_locator('iframe[title="Manuscript in HTML"]')
        frame.locator("html[data-lp-paper-ready]").wait_for(state="attached")
        frame.locator("mark#claim-value a").click()
        assert page.url == original_url and document.is_hidden()
        assert frame.locator("[data-stx-app-header]").count() == 0
        preview.get_by_role("button", name="Show in PDF", exact=True).wait_for()
        pdf_tab.click()
        assert page.url == original_url and document.is_visible()
        assert document.evaluate("node => node.scrollTop") == original_scroll
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
            page.locator(".lp-rich-preview").count(), source_action_urls, code_colors, bookmarks_work, fresh_graph, exports,
        )
        comments_tab = inspector.get_by_role("tab", name="Comments", exact=True)
        assert preview.get_by_role("textbox", name="Comment", exact=True).count() == 0
        comments_tab.click()
        discussion = inspector.get_by_role("region", name="Comments", exact=True)
        attach_to = discussion.get_by_role("combobox", name="Attach to")
        assert attach_to.input_value() == "page"
        post = discussion.get_by_role("button", name="Post comment", exact=True)
        assert post.evaluate("node => node.getBoundingClientRect().height") >= 30
        box = discussion.get_by_role("textbox", name="Comment", exact=True)
        box.fill("Check the units on this page.")
        with page.expect_response(lambda r: "/api/comments" in r.url and r.request.method == "POST") as posted:
            post.click()
        assert posted.value.ok, posted.value.text()
        discussion.get_by_text("Check the units on this page.", exact=True).wait_for()
        attach_to.select_option("claim")
        box.fill("Where did this value come from?")
        post.click()
        discussion.get_by_text("Where did this value come from?", exact=True).wait_for()
        inspector.get_by_role("tab", name="Selected claim", exact=True).click()
        comments_tab.click()
        discussion.get_by_text("Check the units on this page.", exact=True).wait_for()
        assert discussion.get_by_role("listitem").get_by_text("Claim · value", exact=False).count() == 1
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
        200, True, True, True, "true", True, True, True, "manuscript.pdf", True, "true", True, True, True, 0, "verified", True, "language-python", 0, True, False, True, True, 0,
        ("/alice/demo/blob/analysis.py", "/alice/demo/", "_blank"),
        ["rgb(36, 41, 47)", "rgb(230, 237, 243)"], True, True,
        [("manuscript-highlighted.pdf", page_count, True), ("manuscript-with-evidence-graph.pdf", page_count + 1, True)],
    )
