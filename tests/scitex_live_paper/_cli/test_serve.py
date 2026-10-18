"""CLI ``serve`` subcommand — registration + click validation + no-[django] branch.

All collaborators are real:

- ``sys.modules`` manipulation in a yield-fixture (real module state,
  reversed on teardown) drives the ``ImportError`` branch — the same
  one a user hits when they pip-install scitex-live-paper without the
  ``[django]`` extra.
- Click validation paths use ``CliRunner`` against the real ``cli``
  group; no patches.

The *delegation* CLI → ``_server.serve`` path is intentionally not
asserted here — its no-mocks-clean coverage lives in
``tests/django/test_server.py`` via the ``runner`` injection seam on
``_server.serve``.
"""

from __future__ import annotations

import sys
from typing import Iterator

import pytest
from click.testing import CliRunner

from scitex_live_paper._cli import cli, main


# ──────────────────────────────────────────────────────────────────
# Fixture: drop _server from sys.modules so the lazy import raises
# ──────────────────────────────────────────────────────────────────


@pytest.fixture
def server_module_uncached() -> Iterator[None]:
    """Force ``import scitex_live_paper._django._server`` to raise ImportError.

    Real module-state manipulation (the same lever ``importlib`` uses
    when a module fails to import). Restored on teardown.
    """
    key = "scitex_live_paper._django._server"
    sentinel = object()
    original = sys.modules.get(key, sentinel)
    sys.modules[key] = None  # type: ignore[assignment] — forces ImportError
    try:
        yield
    finally:
        if original is sentinel:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original  # type: ignore[assignment]


# ──────────────────────────────────────────────────────────────────
# `serve` registration + help
# ──────────────────────────────────────────────────────────────────


def test_serve_subcommand_is_registered():
    # Arrange
    # Act
    # Assert
    assert "serve" in cli.commands


def test_serve_help_documents_bundle_argument__assert_result_exit_code_0():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert result.exit_code == 0


def test_serve_help_documents_bundle_argument__assert_bundle_path_in_result_out():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert "BUNDLE_PATH" in result.output




def test_serve_help_lists_host_and_port_options__assert_host_in_result_output():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert "--host" in result.output


def test_serve_help_lists_host_and_port_options__assert_port_in_result_output():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert "--port" in result.output


def test_serve_help_lists_host_and_port_options__assert_127_0_0_1_in_result_outpu():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert "127.0.0.1" in result.output


def test_serve_help_lists_host_and_port_options__assert_8765_in_result_output():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", "--help"])
    # Assert
    assert "8765" in result.output




# ──────────────────────────────────────────────────────────────────
# ImportError branch (no [django] extra)
# ──────────────────────────────────────────────────────────────────


def test_serve_without_django_raises_click_exception__assert_result_exit_code_0_2(server_module_uncached, tmp_path):
    # Arrange
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", str(bundle)])
    # Assert
    assert result.exit_code != 0


def test_serve_without_django_raises_click_exception__assert_django_in_result_output(server_module_uncached, tmp_path):
    # Arrange
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["serve", str(bundle)])
    # Assert
    assert "[django]" in result.output




def test_serve_without_django_names_install_command__assert_extra_in_out(server_module_uncached, tmp_path):
    # Arrange
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["serve", str(bundle)])
    # Act
    out = result.output.lower()
    # Assert
    assert "extra" in out


def test_serve_without_django_names_install_command__assert_scitex_live_paper_in_resu(server_module_uncached, tmp_path):
    # Arrange
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["serve", str(bundle)])
    # Act
    out = result.output.lower()
    # Assert
    assert "scitex-live-paper" in result.output




# ──────────────────────────────────────────────────────────────────
# click argument validation (no [_server] import needed)
# ──────────────────────────────────────────────────────────────────


def test_serve_rejects_missing_bundle_path():
    # arrange
    runner = CliRunner()
    # act
    result = runner.invoke(cli, ["serve", "/does-not-exist-anywhere-12345"])
    # assert — click's ``exists=True`` fails before lazy import
    assert result.exit_code != 0


def test_serve_rejects_file_path_for_bundle(tmp_path):
    # arrange
    runner = CliRunner()
    f = tmp_path / "not-a-dir.txt"
    f.write_text("hi", encoding="utf-8")
    # act
    result = runner.invoke(cli, ["serve", str(f)])
    # assert — ``file_okay=False`` blocks regular files
    assert result.exit_code != 0


# ──────────────────────────────────────────────────────────────────
# main() exit-code contract
# ──────────────────────────────────────────────────────────────────


def test_main_returns_zero_on_top_level_help():
    # Arrange
    # Act
    code = main(argv=["--help"])
    # Assert
    assert code == 0


def test_main_returns_zero_on_subcommand_help():
    # Arrange
    # Act
    code = main(argv=["render", "--help"])
    # Assert
    assert code == 0


def test_main_returns_nonzero_on_bundle_error(tmp_path):
    # arrange — malformed claims.json triggers BundleError → ClickException
    bad = tmp_path / "bad-bundle"
    bad.mkdir()
    (bad / "claims.json").write_text("not json", encoding="utf-8")
    out = tmp_path / "site"
    # act
    code = main(argv=["render", str(bad), "--out", str(out)])
    # assert
    assert code != 0
