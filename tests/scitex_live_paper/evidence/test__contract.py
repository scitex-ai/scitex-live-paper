"""Evidence-report contract: validator vs shipped JSON Schema (no mocks).

The report comes from a REAL provider written for the suite
(``_reference_provider``) assessing a real on-disk project.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from scitex_live_paper.evidence import ContractError, schema_path, validate_report

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import (  # noqa: E402,F401
    EXPECTED_FAILURES,
    EXPECTED_STATES,
    ref_project,
    ref_report,
)

_MUTATIONS = {
    "foreign_state": lambda r: r["claims"][0].__setitem__("state", "verified"),
    "no_reason": lambda r: r["claims"][0].pop("reason"),
    "major_2": lambda r: r.__setitem__("schema_version", "2.0.0"),
    "no_provider_name": lambda r: r["provider"].pop("name"),
    "foreign_node_kind": lambda r: r["claims"][0]["graph"]["nodes"][0].__setitem__(
        "kind", "run"
    ),
    "failure_not_object": lambda r: r["claims"][0]["graph"]["nodes"][0].__setitem__(
        "failure", "changed"
    ),
    "failure_without_kind": lambda r: r["claims"][0]["graph"]["nodes"][0].__setitem__(
        "failure", {"detail": "x"}
    ),
    "failure_kind_not_a_token": lambda r: r["claims"][0]["graph"]["nodes"][
        0
    ].__setitem__("failure", {"kind": "Hash Changed!"}),
    "failure_detail_not_text": lambda r: r["claims"][0]["graph"]["nodes"][
        0
    ].__setitem__("failure", {"kind": "changed", "detail": 3}),
}


def _strip_failures(report: dict) -> dict:
    """The same report as a 1.0.0 provider would write it (no node failure)."""
    old = copy.deepcopy(report)
    old["schema_version"] = "1.0.0"
    for c in old["claims"]:
        for n in (c.get("graph") or {}).get("nodes", []):
            n.pop("failure", None)
    return old


def test_reference_provider_marks_exactly_the_nodes_where_evidence_broke(ref_report):
    # Arrange
    graphs = {c["claim_id"]: c.get("graph") for c in ref_report["claims"]}
    # Act
    marked = {
        cid: {n["label"]: n["failure"]["kind"] for n in g["nodes"] if n.get("failure")}
        for cid, g in graphs.items()
        if g is not None
    }
    # Assert
    assert marked == EXPECTED_FAILURES


def test_a_1_0_0_report_without_node_failures_still_validates(ref_report):
    # Arrange
    old = _strip_failures(ref_report)
    # Act
    validated = validate_report(old)
    # Assert
    assert validated["schema_version"] == "1.0.0"


def test_a_1_0_0_report_also_conforms_to_the_1_1_json_schema(ref_report):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    old = _strip_failures(ref_report)
    # Act
    errors = list(jsonschema.Draft202012Validator(_schema()).iter_errors(old))
    # Assert
    assert errors == []


def test_an_unknown_failure_kind_token_is_accepted_for_forward_compat(ref_report):
    # Arrange
    report = copy.deepcopy(ref_report)
    report["claims"][0]["graph"]["nodes"][0]["failure"] = {"kind": "stale_run"}
    # Act
    validated = validate_report(report)
    # Assert
    assert validated["claims"][0]["graph"]["nodes"][0]["failure"]["kind"] == "stale_run"


def _schema() -> dict:
    return json.loads(schema_path().read_text())


def test_reference_provider_reports_the_expected_states(ref_report):
    # Arrange
    validate_report(ref_report)
    # Act
    states = {c["claim_id"]: c["state"] for c in ref_report["claims"]}
    # Assert
    assert states == EXPECTED_STATES


def test_shipped_json_schema_is_a_valid_schema():
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    # Act
    jsonschema.Draft202012Validator.check_schema(_schema())
    # Assert
    assert _schema()["$id"].endswith("/evidence-report/1.2.0")


def test_shipped_json_schema_accepts_a_conforming_report(ref_report):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    # Act
    errors = list(jsonschema.Draft202012Validator(_schema()).iter_errors(ref_report))
    # Assert
    assert errors == []


@pytest.mark.parametrize("mutation", sorted(_MUTATIONS))
def test_validator_and_json_schema_reject_the_same_bad_report(ref_report, mutation):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    bad = copy.deepcopy(ref_report)
    _MUTATIONS[mutation](bad)
    # Act
    schema_rejects = bool(
        list(jsonschema.Draft202012Validator(_schema()).iter_errors(bad))
    )
    try:
        validate_report(bad)
        validator_rejects = False
    except ContractError:
        validator_rejects = True
    # Assert
    assert (schema_rejects, validator_rejects) == (True, True)


def test_edge_to_unknown_node_is_rejected(ref_report):
    # Arrange
    bad = copy.deepcopy(ref_report)
    bad["claims"][0]["graph"]["edges"].append({"source": "nope", "target": "c"})
    # Act
    # Assert
    with pytest.raises(ContractError):
        validate_report(bad)
