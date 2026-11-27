"""Evidence report 1.3.0: no build-host path reaches a reader (no mocks).

A 1.3.0 provider omits the deprecated ``project_root`` and names the project
by ``project_name``; live-paper must work without the root and still accept
a 1.2.x report that carries one.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import jsonschema
from scitex_live_paper._renderer.evidence_site import render_evidence_pages
from scitex_live_paper.bundle import load as load_bundle
from scitex_live_paper.evidence import (
    build_review_packet,
    find_claim,
    schema_path,
    validate_report,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import (  # noqa: F401
    ref_bundle,
    ref_project,
    ref_report,
    ref_report_file,
    ref_site,
)


def _report_schema_errors(report: dict) -> list:
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    return list(jsonschema.Draft202012Validator(schema).iter_errors(report))


def _as_1_2(report: dict, root: Path) -> dict:
    """The same report as a 1.2.0 provider wrote it (with project_root)."""
    old = copy.deepcopy(report)
    old["schema_version"] = "1.2.0"
    old.pop("project_name", None)
    old["project_root"] = str(root)
    return old


def test_reference_report_omits_project_root(ref_report):
    # Arrange
    report = ref_report
    # Act
    present = "project_root" in report
    # Assert
    assert present is False


def test_report_without_project_root_passes_the_validator(ref_report):
    # Arrange
    report = copy.deepcopy(ref_report)
    # Act
    validated = validate_report(report)
    # Assert
    assert validated is report


def test_report_without_project_root_passes_the_json_schema(ref_report):
    # Arrange
    report = copy.deepcopy(ref_report)
    # Act
    errors = _report_schema_errors(report)
    # Assert
    assert errors == []


def test_report_with_external_flags_passes_the_json_schema(ref_report):
    # Arrange
    report = copy.deepcopy(ref_report)
    report["claims"][0]["location"]["external"] = False
    report["claims"][0]["source"] = {"file": "/shared/data.json", "external": True}
    # Act
    errors = _report_schema_errors(report)
    # Assert
    assert errors == []


def test_a_1_2_report_with_project_root_is_still_accepted(ref_report, ref_project):
    # Arrange
    old = _as_1_2(ref_report, ref_project)
    # Act
    accepted = (validate_report(old) is old, _report_schema_errors(old))
    # Assert
    assert accepted == (True, [])


def test_packet_carries_the_project_name(ref_report, ref_project):
    # Arrange
    report = ref_report
    # Act
    packet = build_review_packet(report)
    # Assert
    assert packet["project_name"] == ref_project.name


def test_packet_project_root_is_null_when_the_report_omits_it(ref_report):
    # Arrange
    report = ref_report
    # Act
    packet = build_review_packet(report)
    # Assert
    assert packet["project_root"] is None


def test_packet_copies_the_external_flags(ref_report):
    # Arrange
    report = copy.deepcopy(ref_report)
    claim_id = report["claims"][0]["claim_id"]
    report["claims"][0]["location"]["external"] = False
    report["claims"][0]["source"] = {"file": "/shared/data.json", "external": True}
    # Act
    entry = find_claim(build_review_packet(report), claim_id)
    # Assert
    assert (entry["location"]["external"], entry["source"]["external"]) == (
        False,
        True,
    )


def test_packet_external_is_null_when_not_reported(ref_report):
    # Arrange
    report = ref_report
    # Act
    entry = find_claim(build_review_packet(report), report["claims"][0]["claim_id"])
    # Assert
    assert (entry["location"]["external"], entry["source"]["external"]) == (
        None,
        None,
    )


def test_site_reads_manuscript_from_the_evidence_root_without_project_root(ref_site):
    # Arrange
    _site, result, _packet = ref_site
    # Act
    paper = result.paper_html
    # Assert
    assert paper is not None and paper.is_file()


def test_rendered_review_json_names_no_project_root_path(ref_site, ref_project):
    # Arrange
    _site, result, _packet = ref_site
    # Act
    text = result.review_json.read_text(encoding="utf-8")
    # Assert
    assert str(ref_project) not in text


def test_a_1_2_report_still_reads_manuscript_from_its_project_root(
    tmp_path, ref_bundle, ref_report, ref_project
):
    # Arrange
    old = _as_1_2(ref_report, ref_project)
    # Act
    pages = render_evidence_pages(
        old, tmp_path / "site", bundle=load_bundle(ref_bundle)
    )
    # Assert
    assert pages.paper_html is not None
