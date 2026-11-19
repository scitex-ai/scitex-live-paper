"""Review packet: reviewer ordering, reasons, versioning (no mocks)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import jsonschema
import pytest
from scitex_live_paper.evidence import (
    PACKET_SCHEMA_VERSION,
    build_review_packet,
    find_claim,
    iter_entries,
    review_text,
    schema_path,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import (  # noqa: F401
    EXPECTED_FAILURES,
    ReferenceProvider,
    ref_bundle,
    ref_project,
    ref_report,
    ref_report_file,
    ref_site,
)


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
        "hash differs from the recorded run"
        in text
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


# ---------------------------------------------------------------------------
# The shipped JSON Schema of the packet (review-packet.schema.json)
# ---------------------------------------------------------------------------


def _packet_schema() -> dict:
    path = schema_path().parent / "review-packet.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(packet: dict) -> list:
    return list(jsonschema.Draft202012Validator(_packet_schema()).iter_errors(packet))


def _refs(node) -> list[str]:
    if isinstance(node, dict):
        own = [node["$ref"]] if isinstance(node.get("$ref"), str) else []
        return own + [r for v in node.values() for r in _refs(v)]
    if isinstance(node, list):
        return [r for v in node for r in _refs(v)]
    return []


def test_packet_schema_is_a_valid_2020_12_schema():
    # Arrange
    schema = _packet_schema()
    # Act
    jsonschema.Draft202012Validator.check_schema(schema)
    # Assert
    assert schema["$id"] == (
        "https://scitex.ai/schemas/scitex-live-paper/review-packet/"
        f"{PACKET_SCHEMA_VERSION}"
    )


def test_packet_schema_is_standalone():
    # Arrange
    schema = _packet_schema()
    # Act
    external = [r for r in _refs(schema) if not r.startswith("#/$defs/")]
    # Assert
    assert external == []


def test_built_packet_conforms_to_the_packet_schema(ref_report):
    # Arrange
    packet = build_review_packet(ref_report)
    # Act
    errors = _schema_errors(json.loads(json.dumps(packet)))
    # Assert
    assert errors == []


def test_rendered_review_json_conforms_to_the_packet_schema(ref_site):
    # Arrange
    _site, _result, packet = ref_site
    # Act
    errors = _schema_errors(packet)
    # Assert
    assert (errors, all(e["graph_url"] for e in iter_entries(packet))) == ([], True)


def test_packet_without_embedded_graphs_conforms_to_the_packet_schema(ref_project):
    # Arrange
    report = ReferenceProvider(embed_graphs=False).evidence_report(
        str(ref_project), None, {}
    )
    # Act
    errors = _schema_errors(build_review_packet(report))
    # Assert
    assert errors == []


def _supported_in_needs_inspection(p: dict) -> None:
    p["needs_inspection"].append(p["supported"].pop())


def _drop_failing_nodes(p: dict) -> None:
    del p["needs_inspection"][0]["failing_nodes"]


def _drop_value_reported(p: dict) -> None:
    del p["supported"][0]["source"]["value_reported"]


def _unknown_state_count(p: dict) -> None:
    p["counts"]["unknown"] = 0


def _major_2(p: dict) -> None:
    p["schema_version"] = "2.0.0"


_PACKET_MUTATIONS = {
    "supported_in_needs_inspection": _supported_in_needs_inspection,
    "drop_failing_nodes": _drop_failing_nodes,
    "drop_value_reported": _drop_value_reported,
    "unknown_state_count": _unknown_state_count,
    "major_2": _major_2,
}


@pytest.mark.parametrize("mutation", sorted(_PACKET_MUTATIONS))
def test_packet_schema_rejects_a_bad_packet(ref_report, mutation):
    # Arrange
    bad = copy.deepcopy(build_review_packet(ref_report))
    _PACKET_MUTATIONS[mutation](bad)
    # Act
    errors = _schema_errors(bad)
    # Assert
    assert errors != []
