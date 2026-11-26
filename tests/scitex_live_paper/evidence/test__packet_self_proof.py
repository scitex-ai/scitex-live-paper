"""Review packet: the bundle's optional self-proof receipt (no mocks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
from scitex_live_paper import bundle as bundle_module
from scitex_live_paper._renderer.evidence_site import render_evidence_pages
from scitex_live_paper.evidence import (
    build_review_packet,
    review_text,
    schema_path,
    self_proof_line,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import (  # noqa: F401
    ref_bundle,
    ref_project,
    ref_report,
)

RECEIPT = {
    "schema": "paper-scitex-clew/self-proof/v1",
    "verdict": "PASS",
    "finished_at": "2026-11-26T03:04:05Z",
    "source": {"commit": "0123456789abcdef0123456789abcdef01234567", "ref": "develop"},
    "claims": {"ok": 11, "committed": 12, "verified": 12},
    "failures": [],
}


def _with_receipt(bundle_dir: Path, **overrides) -> bundle_module.Bundle:
    (bundle_dir / "self-proof.json").write_text(json.dumps({**RECEIPT, **overrides}))
    return bundle_module.load(bundle_dir)


def _schema_errors(packet: dict) -> list:
    schema = json.loads(
        (schema_path().parent / "review-packet.schema.json").read_text(encoding="utf-8")
    )
    return list(jsonschema.Draft202012Validator(schema).iter_errors(packet))


def test_packet_self_proof_is_null_without_a_receipt(ref_report):
    # Arrange
    report = ref_report
    # Act
    packet = build_review_packet(report)
    # Assert
    assert (packet["self_proof"], _schema_errors(packet)) == (None, [])


def test_packet_carries_the_bundle_receipt(ref_report, ref_bundle):
    # Arrange
    loaded = _with_receipt(ref_bundle)
    # Act
    packet = build_review_packet(ref_report, self_proof=loaded.self_proof)
    # Assert
    assert packet["self_proof"] == {
        **RECEIPT,
        "date": "2026-11-26",
    }


def test_packet_with_a_receipt_matches_the_shipped_schema(ref_report, ref_bundle):
    # Arrange
    loaded = _with_receipt(ref_bundle, verdict="FAIL", failures=["fig2-auc: differs"])
    # Act
    packet = build_review_packet(ref_report, self_proof=loaded.self_proof)
    # Assert
    assert _schema_errors(packet) == []


def test_reader_line_for_a_passing_receipt(ref_report, ref_bundle):
    # Arrange
    packet = build_review_packet(
        ref_report, self_proof=_with_receipt(ref_bundle).self_proof
    )
    # Act
    line = self_proof_line(packet["self_proof"])
    # Assert
    assert line == (
        "self-proof: 11/12 claims re-derived from a fresh checkout on 2026-11-26"
    )


def test_reader_line_for_a_failed_receipt_names_the_first_failure(
    ref_report, ref_bundle
):
    # Arrange
    loaded = _with_receipt(
        ref_bundle,
        verdict="FAIL",
        failures=["fig2-auc: 0.91 != 0.93", "n-rows: missing"],
    )
    packet = build_review_packet(ref_report, self_proof=loaded.self_proof)
    # Act
    line = self_proof_line(packet["self_proof"])
    # Assert
    assert line == "self-proof FAILED on 2026-11-26: fig2-auc: 0.91 != 0.93"


def test_review_text_includes_the_receipt_line_only_when_present(
    ref_report, ref_bundle
):
    # Arrange
    with_receipt = build_review_packet(
        ref_report, self_proof=_with_receipt(ref_bundle).self_proof
    )
    without = build_review_packet(ref_report)
    # Act
    texts = (review_text(with_receipt), review_text(without))
    # Assert
    assert ("self-proof: 11/12" in texts[0], "self-proof" in texts[1]) == (True, False)


def test_static_evidence_site_passes_the_bundle_receipt(
    ref_report, ref_bundle, tmp_path
):
    # Arrange
    loaded = _with_receipt(ref_bundle)
    # Act
    pages = render_evidence_pages(ref_report, tmp_path / "site", bundle=loaded)
    written = json.loads(pages.review_json.read_text(encoding="utf-8"))
    # Assert
    assert written["self_proof"]["claims"] == {
        "ok": 11,
        "committed": 12,
        "verified": 12,
    }
