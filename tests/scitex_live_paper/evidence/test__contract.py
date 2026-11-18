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
from _reference_provider import EXPECTED_STATES, ref_project, ref_report  # noqa: E402,F401

_MUTATIONS = {
    "foreign_state": lambda r: r["claims"][0].__setitem__("state", "verified"),
    "no_reason": lambda r: r["claims"][0].pop("reason"),
    "major_2": lambda r: r.__setitem__("schema_version", "2.0.0"),
    "no_provider_name": lambda r: r["provider"].pop("name"),
    "foreign_node_kind": lambda r: r["claims"][0]["graph"]["nodes"][0].__setitem__(
        "kind", "run"
    ),
}


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
    assert _schema()["$id"].endswith("/evidence-report/1.0.0")


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
