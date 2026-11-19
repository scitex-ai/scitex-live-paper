"""Review packet: reviewer ordering, reasons, versioning (no mocks)."""

from __future__ import annotations

import sys
from pathlib import Path

from scitex_live_paper.evidence import (
    build_review_packet,
    find_claim,
    iter_entries,
    review_text,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import EXPECTED_FAILURES, ref_project, ref_report  # noqa: F401


def test_packet_lists_needs_inspection_in_review_order(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    order = [e["state"] for e in packet["needs_inspection"]]
    # Assert
    assert order == [
        "not_supported",
        "not_supported",
        "not_checkable",
        "no_evidence_graph",
    ]


def test_packet_lists_supported_claims_after(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    supported = [e["claim_id"] for e in packet["supported"]]
    # Assert
    assert supported == ["auc"]


def test_packet_carries_the_providers_specific_reason(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    entry = find_claim(packet, "n_rows")
    # Assert
    assert entry["reason"] == "value in source differs: 2 in source vs 3 stated"


def test_packet_is_versioned(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    version = (packet["schema"], packet["schema_version"])
    # Assert
    assert version == ("scitex-live-paper.review-packet", "1.2.0")


def test_find_claim_returns_none_for_unregistered_text(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    entry = find_claim(packet, "room-temperature")
    # Assert
    assert entry is None


def test_review_text_lists_every_claim_with_label_and_reason(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    text = review_text(packet)
    # Act
    missing = [
        e["claim_id"]
        for e in iter_entries(packet)
        if f"{e['label']}: {e['claim_id']}" not in text or e["reason"] not in text
    ]
    # Assert
    assert missing == []


def test_packet_lists_the_failing_nodes_of_each_claim(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    failing = {
        e["claim_id"]: {f["label"]: f["failure"] for f in e["failing_nodes"]}
        for e in iter_entries(packet)
        if e["graph"] is not None
    }
    # Assert
    assert failing == EXPECTED_FAILURES


def test_failing_node_entries_carry_label_and_detail(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    (node,) = find_claim(packet, "n_rows")["failing_nodes"]
    # Assert
    assert (node["failure_label"], node["detail"]) == (
        "Mismatched",
        "2 in source vs 3 stated",
    )


def test_review_text_says_where_the_evidence_broke(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    text = review_text(packet)
    # Assert
    assert (
        "evidence broke at: \u26a0 CHANGED input:data/input2.csv -- "
        "hash differs from the recorded run" in text
        and "input:data/input2.csv [\u26a0 CHANGED] -> process:scripts/compute.py"
        in text
    )


def test_claims_without_failing_nodes_have_an_empty_list(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    entry = find_claim(packet, "auc")
    # Assert
    assert entry["failing_nodes"] == []
