"""No-mocks tests for the ``scitex-live-paper hub-manifest`` subcommand.

Pins:
1. Subcommand registration + ``--help`` documents the flags
2. Default JSON output is indented + sorted (stable VCS diffs)
3. ``--compact`` switches to single-line JSON
4. ``--label`` / ``--subtitle`` / ``--schema-version`` overrides win
5. Output, with no overrides, matches :func:`derive_wrapper_manifest`
6. Output is ready to redirect into ``manifest.json`` — no chrome,
   no leading log lines, just JSON.

Real CliRunner + real derive_wrapper_manifest — no mocks.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from scitex_live_paper._cli import cli


# ──────────────────────────────────────────────────────────────────
# Subcommand registration + help
# ──────────────────────────────────────────────────────────────────


def test_hub_manifest_subcommand_is_registered():
    # Arrange
    # Act
    # Assert
    assert "hub-manifest" in cli.commands


def test_top_level_help_lists_hub_manifest__assert_result_exit_code_0():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert result.exit_code == 0


def test_top_level_help_lists_hub_manifest__assert_hub_manifest_in_result_ou():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert "hub-manifest" in result.output




def test_hub_manifest_help_documents_flags():
    result = CliRunner().invoke(cli, ["hub-manifest", "--help"])
    assert result.exit_code == 0
    for flag in ("--label", "--subtitle", "--schema-version", "--compact"):
        assert flag in result.output, f"--help missing flag: {flag}"


def test_hub_manifest_help_mentions_redirect_example():
    # The whole point of the subcommand: redirect into manifest.json.
    # The help text should make that idiom discoverable.
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["hub-manifest", "--help"])
    # Assert
    assert "manifest.json" in result.output


# ──────────────────────────────────────────────────────────────────
# Default output — indented, sorted, JSON, exit 0
# ──────────────────────────────────────────────────────────────────


def test_hub_manifest_exits_zero():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Assert
    assert result.exit_code == 0


def test_hub_manifest_default_output_is_valid_json():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert isinstance(parsed, dict)


def test_hub_manifest_default_output_is_indented():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Act
    line_count = sum(1 for ln in result.output.splitlines() if ln.strip())
    # Assert
    assert line_count > 5, "default output should be indented (multi-line)"


def test_hub_manifest_default_output_is_sorted():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest"])
    parsed = json.loads(result.output)
    # Act
    top_keys = list(parsed.keys())
    # Assert
    assert top_keys == sorted(top_keys)


def test_hub_manifest_default_output_matches_derive():
    # Arrange
    from scitex_live_paper import derive_wrapper_manifest
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert parsed == derive_wrapper_manifest()


# ──────────────────────────────────────────────────────────────────
# --compact — single-line JSON for inline embedding
# ──────────────────────────────────────────────────────────────────


def test_hub_manifest_compact_is_single_line__assert_result_exit_code_0_2():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["hub-manifest", "--compact"])
    # Assert
    assert result.exit_code == 0


def test_hub_manifest_compact_is_single_line__assert_n_not_in_payload():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest", "--compact"])
    # Act
    payload = result.output.rstrip("\n")
    # Assert
    assert "\n" not in payload




def test_hub_manifest_compact_is_still_valid_json():
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["hub-manifest", "--compact"])
    # Assert
    assert json.loads(result.output) == json.loads(
        CliRunner().invoke(cli, ["hub-manifest"]).output
    )


# ──────────────────────────────────────────────────────────────────
# Per-wrapper overrides win
# ──────────────────────────────────────────────────────────────────


def test_hub_manifest_label_override_wins():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest", "--label", "Live Paper"])
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert parsed["label"] == "Live Paper"


def test_hub_manifest_subtitle_override_wins():
    # Arrange
    result = CliRunner().invoke(
        cli,
        ["hub-manifest", "--subtitle", "Mounted under apps/live-paper/"],
    )
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert parsed["subtitle"] == "Mounted under apps/live-paper/"


def test_hub_manifest_schema_version_override_wins():
    # Arrange
    result = CliRunner().invoke(
        cli,
        ["hub-manifest", "--schema-version", "2.1.0"],
    )
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert parsed["schema_version"] == "2.1.0"


def test_hub_manifest_default_schema_version_is_2_0_0():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Act
    parsed = json.loads(result.output)
    # Assert
    assert parsed["schema_version"] == "2.0.0"


# ──────────────────────────────────────────────────────────────────
# Output is redirect-ready — no log chrome, no banner
# ──────────────────────────────────────────────────────────────────


def test_hub_manifest_output_starts_with_brace():
    # If we printed a banner / progress line above the JSON, redirect
    # into manifest.json would produce an invalid file. Pin: stdout
    # starts with `{` — nothing before it.
    # Arrange
    # Act
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Assert
    assert result.output.lstrip().startswith("{")


def test_hub_manifest_output_ends_after_closing_brace():
    # Arrange
    result = CliRunner().invoke(cli, ["hub-manifest"])
    # Act
    lines = [ln for ln in result.output.splitlines() if ln.strip()]
    # Assert
    assert lines[-1].rstrip() == "}"
