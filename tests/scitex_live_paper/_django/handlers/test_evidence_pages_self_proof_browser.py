"""The PDF reader shows the bundle's self-proof receipt under the claim summary (Chromium)."""

from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from wsgiref.simple_server import make_server

import pytest
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.handlers.wsgi import WSGIHandler

from .test_evidence_pages import evidence_host  # noqa: F401 - shared real host fixture
from .test_evidence_pages_browser import QuietHandler, mounted_browser  # noqa: F401

RECEIPT = {
    "schema": "paper-scitex-clew/self-proof/v1",
    "verdict": "PASS",
    "finished_at": "2026-11-26T03:04:05Z",
    "source": {"commit": "0123456789abcdef0123456789abcdef01234567", "ref": "develop"},
    "claims": {"ok": 1, "committed": 1, "verified": 1},
    "failures": [],
}

FAILED = {**RECEIPT, "verdict": "FAIL", "failures": ["value: 20 differs from 21"]}


def _reader_line(evidence_host, browser, receipt):
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "rich-provider.pdf"
    root = evidence_host.roots["alice"]
    shutil.copyfile(fixture, root / "manuscript.pdf")
    if receipt is not None:
        (root / "self-proof.json").write_text(json.dumps(receipt))
    server = make_server(
        "127.0.0.1", 0, StaticFilesHandler(WSGIHandler()), handler_class=QuietHandler
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    context = browser.new_context(
        viewport={"width": 1440, "height": 850},
        extra_http_headers={"Authorization": "Bearer alice"},
    )
    try:
        page = context.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/mounted/paper/?project=alice")
        page.get_by_role("link", name="Calculation traces", exact=False).wait_for()
        line = page.locator("#live-paper-trace-status .lp-trace-self-proof")
        observed = (
            None
            if line.count() == 0
            else (
                line.text_content(),
                line.get_attribute("title"),
                line.get_attribute("data-verdict"),
                line.evaluate("node => getComputedStyle(node).fontWeight"),
            )
        )
        screenshots = os.environ.get("LP_SCREENSHOT_DIR")
        if screenshots:
            Path(screenshots).mkdir(parents=True, exist_ok=True)
            verdict = receipt["verdict"] if receipt else "absent"
            page.locator("#live-paper-trace-status").screenshot(
                path=str(Path(screenshots) / f"reader-self-proof-{verdict}.png")
            )
        return observed
    finally:
        context.close()
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def test_reader_shows_a_passing_receipt_with_the_commit_tooltip(
    evidence_host, mounted_browser
):
    # Arrange
    receipt = RECEIPT
    # Act
    observed = _reader_line(evidence_host, mounted_browser, receipt)
    # Assert
    assert observed == (
        "self-proof: 1/1 claims re-derived from a fresh checkout on 2026-11-26",
        "commit 0123456 (develop)",
        "PASS",
        "400",
    )


def test_reader_shows_a_failed_receipt_as_a_warning(evidence_host, mounted_browser):
    # Arrange
    receipt = FAILED
    # Act
    observed = _reader_line(evidence_host, mounted_browser, receipt)
    # Assert
    assert observed == (
        "self-proof FAILED on 2026-11-26: value: 20 differs from 21",
        "commit 0123456 (develop)",
        "FAIL",
        "600",
    )


def test_reader_shows_nothing_without_a_receipt(evidence_host, mounted_browser):
    # Arrange
    receipt = None
    # Act
    observed = _reader_line(evidence_host, mounted_browser, receipt)
    # Assert
    assert observed is None


