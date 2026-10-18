"""No-mocks tests for the ``scitex-live-paper info`` subcommand.

Operator-facing pre-flight check: load a bundle and print a one-screen
summary (or a `--json` machine-parseable blob). The path uses the real
``bundle.load()`` against on-disk fixtures — no mocks, no patches.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from scitex_live_paper._cli import cli

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"


# ──────────────────────────────────────────────────────────────────
# `info` subcommand registration + --help
# ──────────────────────────────────────────────────────────────────


def test_info_subcommand_is_registered():
    # Arrange
    # Act
    # Assert
    assert "info" in cli.commands


def test_top_level_help_lists_info__assert_result_exit_code_0():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert result.exit_code == 0


def test_top_level_help_lists_info__assert_info_in_result_output():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert "info" in result.output




def test_info_help_documents_bundle_argument__assert_result_exit_code_0_2():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", "--help"])
    # Assert
    assert result.exit_code == 0


def test_info_help_documents_bundle_argument__assert_bundle_path_in_result_out():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", "--help"])
    # Assert
    assert "BUNDLE_PATH" in result.output


def test_info_help_documents_bundle_argument__assert_json_in_result_output():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", "--help"])
    # Assert
    assert "--json" in result.output




def test_info_rejects_missing_bundle_path():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", "/does-not-exist-anywhere-99"])
    # Assert
    assert result.exit_code != 0


def test_info_rejects_file_path_for_bundle(tmp_path):
    # Arrange
    f = tmp_path / "not-a-dir.txt"
    f.write_text("x", encoding="utf-8")
    # Act
    result = CliRunner().invoke(cli, ["info", str(f)])
    # Assert
    assert result.exit_code != 0


# ──────────────────────────────────────────────────────────────────
# Human-readable output (default)
# ──────────────────────────────────────────────────────────────────


def test_info_bundle_min_exits_zero():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert result.exit_code == 0, result.output


def test_info_bundle_min_prints_manuscript_filename():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "manuscript.pdf" in result.output


def test_info_bundle_min_prints_claim_count():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "claims    : 3" in result.output


def test_info_bundle_min_prints_status_palette():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    for label in ("registered", "suspect", "verified"):
        assert label in result.output


def test_info_bundle_min_prints_dag_embedded():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "dag       : embedded" in result.output


def test_info_bundle_min_prints_paper_state_section__assert_paper_state_in_result_out():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "paper_state" in result.output


def test_info_bundle_min_prints_paper_state_section__assert_stage_preprint_in_result():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "stage         : preprint" in result.output


def test_info_bundle_min_prints_paper_state_section__assert_header_label_preprint_in():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "header_label  : Preprint" in result.output




def test_info_bundle_min_omits_optional_fields_when_absent():
    # bundle-min has no state.yaml → no journal / DOI / pinned_commit
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    for absent_field in ("journal       :", "doi           :", "pinned_commit :"):
        assert absent_field not in result.output


def test_info_bundle_accepted_prints_journal_and_doi__assert_result_exit_code_0_result():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert result.exit_code == 0, result.output


def test_info_bundle_accepted_prints_journal_and_doi__assert_journal_elife_in_result_o():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert "journal       : eLife" in result.output


def test_info_bundle_accepted_prints_journal_and_doi__assert_10_7554_elife_99999_in_re():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert "10.7554/eLife.99999" in result.output




def test_info_bundle_accepted_prints_pinned_commit():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert "deadbeefcafef00d12345678" in result.output


def test_info_bundle_accepted_shows_badge_visible_true__assert_badge_visible_true_in_res():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert "badge visible : True" in result.output


def test_info_bundle_accepted_shows_badge_visible_true__assert_re_verify_true_in_result():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED)])
    # Assert
    assert "re-verify : True" in result.output




def test_info_bundle_min_shows_badge_hidden_false():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN)])
    # Assert
    assert "badge visible : False" in result.output


# ──────────────────────────────────────────────────────────────────
# --json output
# ──────────────────────────────────────────────────────────────────


def test_info_json_exits_zero():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"])
    # Assert
    assert result.exit_code == 0, result.output


def test_info_json_is_valid_parseable_json():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"])
    # Act
    payload = json.loads(result.output)
    # Assert
    assert isinstance(payload, dict)


def test_info_json_carries_required_keys():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"])
    payload = json.loads(result.output)
    required = {
        "bundle_path",
        "manuscript",
        "schema_version",
        "claim_count",
        "status_palette",
        "dag_present",
        "paper_state",
    }
    # Act
    missing = required - set(payload.keys())
    # Assert
    assert not missing, f"missing keys: {missing}"


def test_info_json_status_palette_counts():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"])
    # Act
    palette = json.loads(result.output)["status_palette"]
    # Assert
    assert palette == {"registered": 1, "suspect": 1, "verified": 1}


def test_info_json_paper_state_nested_block__assert_ps_stage_accepted():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["stage"] == "accepted"


def test_info_json_paper_state_nested_block__assert_ps_journal_elife():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["journal"] == "eLife"


def test_info_json_paper_state_nested_block__assert_ps_doi_10_7554_elife_9999():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["doi"] == "10.7554/eLife.99999"


def test_info_json_paper_state_nested_block__assert_ps_pinned_commit_deadbeef():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["pinned_commit"] == "deadbeefcafef00d12345678"


def test_info_json_paper_state_nested_block__assert_ps_show_verification_badg():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["show_verification_badge"] is True


def test_info_json_paper_state_nested_block__assert_ps_re_verify_enabled_is_t():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_ACCEPTED), "--json"])
    # Act
    ps = json.loads(result.output)["paper_state"]
    # Assert
    assert ps["re_verify_enabled"] is True




def test_info_json_dag_present_true():
    # Arrange
    result = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"])
    # Act
    payload = json.loads(result.output)
    # Assert
    assert payload["dag_present"] is True


def test_info_json_output_is_stable_across_runs():
    # Sort_keys=True + Counter ordering → stable output the operator
    # can diff between runs.
    # Arrange
    first = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"]).output
    # Act
    second = CliRunner().invoke(cli, ["info", str(BUNDLE_MIN), "--json"]).output
    # Assert
    assert first == second


# ──────────────────────────────────────────────────────────────────
# Error paths — BundleError surfaces as ClickException
# ──────────────────────────────────────────────────────────────────


def test_info_malformed_claims_json_exits_nonzero__assert_result_exit_code_0_3(tmp_path):
    # Arrange
    bad = tmp_path / "bad-bundle"
    bad.mkdir()
    (bad / "claims.json").write_text("not json {", encoding="utf-8")
    (bad / "manuscript.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (bad / "figz").mkdir()
    # Act
    result = CliRunner().invoke(cli, ["info", str(bad)])
    # Assert
    assert result.exit_code != 0


def test_info_malformed_claims_json_exits_nonzero__assert_traceback_not_in_result_o(tmp_path):
    # Arrange
    bad = tmp_path / "bad-bundle"
    bad.mkdir()
    (bad / "claims.json").write_text("not json {", encoding="utf-8")
    (bad / "manuscript.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (bad / "figz").mkdir()
    # Act
    result = CliRunner().invoke(cli, ["info", str(bad)])
    # Assert
    assert "Traceback" not in result.output




def test_info_missing_manuscript_exits_nonzero(tmp_path):
    # Arrange
    bad = tmp_path / "no-manuscript"
    bad.mkdir()
    (bad / "claims.json").write_text(
        '{"schema":"scitex-clew.claims/v1","claims":[]}',
        encoding="utf-8",
    )
    (bad / "figz").mkdir()
    # Act
    result = CliRunner().invoke(cli, ["info", str(bad)])
    # Assert
    assert result.exit_code != 0
