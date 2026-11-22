"""Actual Django HTTP pages, authenticated assets and claim graphs in Chromium."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import struct
import threading
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
        inspector = page.get_by_role("complementary", name="Claim evidence")
        row = inspector.locator(".scitex-rich-pdf-feed button").first
        row.wait_for()
        pdf = document.bounding_box()
        evidence = inspector.bounding_box()
        if embed:
            arrangement_ok = evidence["y"] > pdf["y"]
            page.get_by_role("link", name="Claim evidence", exact=True).click()
            navigation_ok = page.evaluate("location.hash") == "#live-paper-claims"
        else:
            arrangement_ok = (
                abs(evidence["y"] - pdf["y"]) < 2
                and evidence["x"] >= pdf["x"] + pdf["width"]
            )
            navigation_ok = pdf["width"] > 600
        overlay = document.locator('[data-overlay-id="value"]')
        overlay.wait_for()
        assert overlay.get_attribute("data-status") == "verified"
        assert overlay.evaluate("""element => {
            const style = getComputedStyle(element);
            const verified = style.getPropertyValue("--lp-status-verified").trim();
            return verified && style.getPropertyValue("--lp-rich-mark").trim() === verified;
        }""")
        overlay.hover()
        preview = page.locator(".lp-rich-preview")
        preview.get_by_role("heading", name="Evidence graph (recorded-test-evidence)").wait_for()
        graph = preview.locator(".lp-claim-dag svg")
        graph.wait_for()
        reference = preview.get_by_role("button", name="Run analysis.py", exact=True)
        reference.hover()
        preview.get_by_text("print('computed value')", exact=True).wait_for()
        graph.locator("g.lp-source-highlight").wait_for()
        source_link_is_claim_bound = "claim_id=value" in preview.get_by_role(
            "link", name="Open full evidence graph"
        ).get_attribute("href")
        trace_summary = page.get_by_role("link", name="Calculation traces", exact=False)
        trace_summary.wait_for()
        marked = overlay.get_attribute("data-appearance") == "highlight"
        source_selected = reference.get_attribute("aria-pressed")
        overlay.click()
        preview.get_by_role("button", name="Input samples.gz", exact=True).hover()
        preview.get_by_text("Gzip-compressed file.", exact=False).wait_for()
        guessed_images = preview.locator(".lp-source-preview canvas, .lp-source-preview img").count()
        page.keyboard.press("Escape")
        preview.wait_for(state="hidden")
        overlay.focus()
        overlay.press("Enter")
        preview.wait_for()
        page.keyboard.press("Escape")
        preview.wait_for(state="hidden")
        focus_restored = overlay.evaluate("button => button === document.activeElement")
        row.click()
        overlay_selected = overlay.get_attribute("aria-current") == "true"
        with page.expect_download() as pending:
            page.get_by_role("link", name="Download PDF", exact=True).click()
        download = pending.value
        observed = (
            response.status, arrangement_ok, navigation_ok,
            row.get_attribute("aria-current"),
            inspector.get_by_role("dialog", name="Claim detail").is_visible(),
            page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
            overlay_selected,
            download.suggested_filename,
            download.path().read_bytes() == fixture.read_bytes(),
            source_selected, source_link_is_claim_bound, marked, focus_restored,
            guessed_images,
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
        200, True, True, "true", True, True, True, "manuscript.pdf", True, "true", True, True, True, 0
    )
