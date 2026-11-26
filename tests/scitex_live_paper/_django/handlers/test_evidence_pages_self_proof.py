"""The mounted review packet and paper page carry the bundle's self-proof receipt.

Real Django requests against a real host mount (shared ``evidence_host``
fixture); the receipt is a real file inside the authorized resource root.
"""

from __future__ import annotations

import json
import os

import pytest

from .test_evidence_pages import evidence_host, get  # noqa: F401 - shared real host fixture

RECEIPT = {
    "schema": "paper-scitex-clew/self-proof/v1",
    "verdict": "PASS",
    "finished_at": "2026-11-26T03:04:05Z",
    "source": {"commit": "0123456789abcdef0123456789abcdef01234567", "ref": "develop"},
    "claims": {"ok": 1, "committed": 1, "verified": 1},
    "failures": [],
}


def _write(host, content) -> None:
    text = content if isinstance(content, str) else json.dumps(content)
    (host.roots["alice"] / "self-proof.json").write_text(text, encoding="utf-8")


def test_review_json_self_proof_is_null_without_a_receipt(evidence_host):
    # Arrange
    host = evidence_host
    # Act
    packet = get(host, "review.json").json()
    # Assert
    assert packet["self_proof"] is None


def test_review_json_carries_the_receipt_from_the_authorized_root(evidence_host):
    # Arrange
    _write(evidence_host, RECEIPT)
    # Act
    packet = get(evidence_host, "review.json").json()
    # Assert
    assert packet["self_proof"] == {**RECEIPT, "date": "2026-11-26"}


def test_receipt_of_another_project_is_not_served(evidence_host):
    # Arrange
    (evidence_host.roots["bob"] / "self-proof.json").write_text(json.dumps(RECEIPT))
    # Act
    packet = get(evidence_host, "review.json").json()
    # Assert
    assert packet["self_proof"] is None


@pytest.mark.parametrize(
    "content",
    ["{broken", json.dumps({**RECEIPT, "schema": "paper-scitex-clew/self-proof/v2"})],
    ids=["invalid-json", "wrong-schema"],
)
def test_malformed_receipt_is_ignored_and_the_paper_still_serves(
    evidence_host, content
):
    # Arrange
    _write(evidence_host, content)
    # Act
    responses = (get(evidence_host, "review.json"), get(evidence_host, "paper.html"))
    # Assert
    assert (
        responses[0].status_code,
        responses[0].json()["self_proof"],
        responses[1].status_code,
        "self-proof" in responses[1].content.decode(),
    ) == (200, None, 200, False)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs a FIFO")
def test_non_regular_receipt_is_ignored(evidence_host):
    # Arrange
    os.mkfifo(evidence_host.roots["alice"] / "self-proof.json")
    # Act
    packet = get(evidence_host, "review.json").json()
    # Assert
    assert packet["self_proof"] is None


def test_paper_page_shows_the_receipt_line_with_the_commit_as_title(evidence_host):
    # Arrange
    _write(evidence_host, RECEIPT)
    # Act
    html = get(evidence_host, "paper.html").content.decode()
    # Assert
    assert (
        '<p class="lp-self-proof" data-verdict="PASS" title="commit 0123456 (develop)">'
        "self-proof: 1/1 claims re-derived from a fresh checkout on 2026-11-26</p>"
    ) in html


def test_paper_page_shows_a_failed_receipt_as_a_warning(evidence_host):
    # Arrange
    _write(
        evidence_host,
        {**RECEIPT, "verdict": "FAIL", "failures": ["value: <21> differs"]},
    )
    # Act
    html = get(evidence_host, "paper.html").content.decode()
    # Assert
    assert (
        'data-verdict="FAIL"' in html,
        "self-proof FAILED on 2026-11-26: value: &lt;21&gt; differs" in html,
    ) == (True, True)
