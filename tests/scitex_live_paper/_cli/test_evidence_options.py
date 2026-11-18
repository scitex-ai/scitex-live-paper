"""``export-review`` and the render evidence options (real CLI, no mocks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner
from scitex_live_paper._cli import cli

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidence"))
from _reference_provider import (  # noqa: F401
    ref_bundle,
    ref_project,
    ref_report,
    ref_report_file,
)


def test_export_review_writes_the_packet(tmp_path, ref_report_file):
    # Arrange
    out = tmp_path / "review.json"
    args = [
        "export-review",
        "--evidence-report",
        str(ref_report_file),
        "--out",
        str(out),
    ]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert (res.exit_code, json.loads(out.read_text())["counts"]) == (
        0,
        {
            "not_supported": 2,
            "not_checkable": 1,
            "no_evidence_graph": 1,
            "supported": 1,
        },
    )


def test_export_review_text_lists_needs_inspection(ref_report_file):
    # Arrange
    args = [
        "export-review",
        "--evidence-report",
        str(ref_report_file),
        "--format",
        "text",
    ]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert "== NEEDS INSPECTION (4) ==" in res.output


def test_export_review_dry_run_writes_nothing(tmp_path, ref_report_file):
    # Arrange
    out = tmp_path / "review.json"
    args = [
        "export-review",
        "--evidence-report",
        str(ref_report_file),
        "--out",
        str(out),
        "--dry-run",
    ]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert (res.exit_code, out.exists(), "DRY RUN" in res.output) == (0, False, True)


def test_invalid_report_is_a_clean_render_error(tmp_path, ref_bundle, ref_report):
    # Arrange
    ref_report["claims"][0]["state"] = "verified"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(ref_report))
    args = [
        "render",
        str(ref_bundle),
        "--out",
        str(tmp_path / "s"),
        "--evidence-report",
        str(bad),
    ]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert (res.exit_code != 0, "unknown state 'verified'" in res.output) == (
        True,
        True,
    )
