"""STX-TQ tests for ``scitex_live_paper._cli.render`` (M1 site emit).

Replaces the importorskip scaffolding stub from PR #13 (issue #10) now
that the CLI lands in this PR. Exercises the public contract:

  - module exposes a ``main`` callable that the pyproject's
    ``[project.scripts]`` entry actually targets,
  - ``scitex-live-paper render <bundle> --out <site>`` produces the
    site layout pinned in issue #7 (index / viewer / claims / dag +
    vendored assets + manuscript.pdf + claims.json),
  - the generated site is self-contained: no CDN URLs, every asset
    referenced from a page lives in the same directory tree,
  - errors from the bundle loader surface as clean CLI exits (no
    traceback) and a useful message.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from scitex_live_paper import _cli as cli_module
from scitex_live_paper._cli import RenderResult, cli, main, render_site
from scitex_live_paper._renderer import index as index_module

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
FIXTURE_BUNDLE = BUNDLE_MIN


def _run_cli(*args: str, cwd=None):
    """Run `python -m scitex_live_paper._cli` with the given args."""
    return subprocess.run(
        [sys.executable, "-m", "scitex_live_paper._cli", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Module surface — pyproject contract
# ---------------------------------------------------------------------------


def test_cli_module_exposes_main_callable():
    # Arrange
    target = cli_module
    # Act
    # Assert
    assert callable(getattr(target, "main", None))


def test_cli_module_exposes_render_site_callable():
    # Arrange
    # Act
    # Assert
    assert callable(getattr(cli_module, "render_site", None))


def test_cli_module_exposes_click_group():
    # Arrange
    import click
    # Act
    # Assert
    assert isinstance(cli, click.Group)


def test_render_site_returns_render_result_dataclass__assert_isinstance_result_renderr(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = render_site(BUNDLE_MIN, out)
    # Assert
    assert isinstance(result, RenderResult)


def test_render_site_returns_render_result_dataclass__assert_result_out_dir_out_resolv(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = render_site(BUNDLE_MIN, out)
    # Assert
    assert result.out_dir == out.resolve()




# ---------------------------------------------------------------------------
# Site layout — issue #7's pinned contract
# ---------------------------------------------------------------------------


def _run_render(tmp_path: Path, *extra: str) -> Path:
    runner = CliRunner()
    out_dir = tmp_path / "site"
    result = runner.invoke(
        cli,
        ["render", str(BUNDLE_MIN), "--out", str(out_dir), *extra],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return out_dir


def test_render_emits_index_html(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "index.html").is_file()


def test_render_emits_viewer_html(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "viewer.html").is_file()


def test_render_emits_claims_html(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "claims.html").is_file()


def test_render_emits_dag_html(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "dag.html").is_file()


def test_render_copies_manuscript_pdf(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "manuscript.pdf").is_file()


def test_render_copies_claims_json__assert_out_claims_json_is_file(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "claims.json").is_file()


def test_render_copies_claims_json__assert_parsed_get_schema_scitex(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    parsed = json.loads((out / "claims.json").read_text(encoding="utf-8"))
    # Assert
    assert parsed.get("schema") == "scitex-clew.claims/v1"




def test_render_vendors_pdfjs_under_assets__assert_out_assets_pdfjs_pdf_min(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "pdfjs" / "pdf.min.mjs").is_file()


def test_render_vendors_pdfjs_under_assets__assert_out_assets_pdfjs_pdf_work(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "pdfjs" / "pdf.worker.min.mjs").is_file()




def test_render_vendors_mermaid_under_assets(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "mermaid" / "mermaid.min.js").is_file()


def test_render_vendors_per_page_css_under_assets__assert_out_assets_viewer_css_is(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "viewer.css").is_file()


def test_render_vendors_per_page_css_under_assets__assert_out_assets_claims_css_is(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "claims.css").is_file()


def test_render_vendors_per_page_css_under_assets__assert_out_assets_dag_css_is_fil(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "dag.css").is_file()


def test_render_vendors_per_page_css_under_assets__assert_out_assets_index_css_is_f(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "index.css").is_file()




def test_render_vendors_per_page_js_under_assets__assert_out_assets_viewer_js_is_f(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "viewer.js").is_file()


def test_render_vendors_per_page_js_under_assets__assert_out_assets_claims_js_is_f(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "claims.js").is_file()


def test_render_vendors_per_page_js_under_assets__assert_out_assets_dag_js_is_file(tmp_path: Path):
    # Arrange
    # Act
    out = _run_render(tmp_path)
    # Assert
    assert (out / "assets" / "dag.js").is_file()




# ---------------------------------------------------------------------------
# Self-contained: no CDN strings anywhere in any rendered HTML
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "page", ["index.html", "viewer.html", "claims.html", "dag.html"]
)
def test_rendered_page_has_no_cdn_reference(tmp_path: Path, page: str):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / page).read_text(encoding="utf-8")
    # Assert
    for cdn in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com"):
        assert cdn not in html, f"{page} pulls from {cdn}"


# ---------------------------------------------------------------------------
# Landing page contract
# ---------------------------------------------------------------------------


def test_index_html_links_to_sibling_pages__assert_href_viewer_html_in_html(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert 'href="viewer.html"' in html


def test_index_html_links_to_sibling_pages__assert_href_claims_html_in_html(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert 'href="claims.html"' in html


def test_index_html_links_to_sibling_pages__assert_href_dag_html_in_html(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert 'href="dag.html"' in html




def test_index_html_lists_claim_count_from_bundle(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert "3" in html


def test_index_html_names_the_manuscript_file(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert "manuscript.pdf" in html


def test_index_html_shows_claims_schema_version(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path)
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert "scitex-clew.claims/v1" in html


def test_index_html_honours_custom_title_via_cli(tmp_path: Path):
    # Arrange
    out = _run_render(tmp_path, "--title", "Custom Paper")
    # Act
    html = (out / "index.html").read_text(encoding="utf-8")
    # Assert
    assert "<title>Custom Paper</title>" in html


# ---------------------------------------------------------------------------
# render_site (library mode) and RenderResult shape
# ---------------------------------------------------------------------------


def test_render_site_paths_point_at_emitted_pages(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = render_site(BUNDLE_MIN, out)
    # Assert
    assert result.index_html == (out / "index.html").resolve()
    assert result.viewer_html == (out / "viewer.html").resolve()
    assert result.claims_html == (out / "claims.html").resolve()
    assert result.dag_html == (out / "dag.html").resolve()
    for path in (
        result.index_html,
        result.viewer_html,
        result.claims_html,
        result.dag_html,
    ):
        assert path.is_file()


def test_render_site_is_idempotent(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    render_site(BUNDLE_MIN, out)
    # Act: second render must not raise and must update content
    result = render_site(BUNDLE_MIN, out, title="Second")
    # Assert
    html = result.index_html.read_text(encoding="utf-8")
    assert "<title>Second</title>" in html


# ---------------------------------------------------------------------------
# Errors → clean CLI exit
# ---------------------------------------------------------------------------


def test_render_cli_reports_missing_bundle_path__assert_result_exit_code_0(tmp_path: Path):
    # Arrange
    runner = CliRunner()
    missing = tmp_path / "does-not-exist"
    out = tmp_path / "site"
    # Act
    result = runner.invoke(
        cli, ["render", str(missing), "--out", str(out)]
    )
    # Assert
    assert result.exit_code != 0


def test_render_cli_reports_missing_bundle_path__assert_does_not_exist_in_result(tmp_path: Path):
    # Arrange
    runner = CliRunner()
    missing = tmp_path / "does-not-exist"
    out = tmp_path / "site"
    # Act
    result = runner.invoke(
        cli, ["render", str(missing), "--out", str(out)]
    )
    # Assert
    assert "does-not-exist" in result.output or "Invalid value" in result.output




def test_render_cli_reports_malformed_bundle__assert_result_exit_code_0_2(tmp_path: Path):
    # Arrange
    bad = tmp_path / "bad"
    bad.mkdir()
    runner = CliRunner()
    # Act
    result = runner.invoke(
        cli, ["render", str(bad), "--out", str(tmp_path / "site")]
    )
    # Assert
    assert result.exit_code != 0


def test_render_cli_reports_malformed_bundle__assert_manuscript_in_result_outp(tmp_path: Path):
    # Arrange
    bad = tmp_path / "bad"
    bad.mkdir()
    runner = CliRunner()
    # Act
    result = runner.invoke(
        cli, ["render", str(bad), "--out", str(tmp_path / "site")]
    )
    # Assert
    assert "manuscript" in result.output.lower()




def test_main_returns_zero_on_successful_render__assert_rc_0(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    # Act
    rc = main(["render", str(BUNDLE_MIN), "--out", str(out)])
    # Assert
    assert rc == 0


def test_main_returns_zero_on_successful_render__assert_out_index_html_is_file(tmp_path: Path):
    # Arrange
    out = tmp_path / "site"
    # Act
    rc = main(["render", str(BUNDLE_MIN), "--out", str(out)])
    # Assert
    assert (out / "index.html").is_file()




def test_main_returns_nonzero_on_bundle_error(tmp_path: Path):
    # Arrange
    bad = tmp_path / "bad"
    bad.mkdir()
    # Act
    rc = main(["render", str(bad), "--out", str(tmp_path / "site")])
    # Assert
    assert rc != 0


# ---------------------------------------------------------------------------
# CLI top-level group surface
# ---------------------------------------------------------------------------


def test_cli_top_level_help_lists_render_command__assert_result_exit_code_0_3():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["--help"])
    # Assert
    assert result.exit_code == 0


def test_cli_top_level_help_lists_render_command__assert_render_in_result_output():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["--help"])
    # Assert
    assert "render" in result.output




def test_cli_version_option_emits_a_version_string__assert_result_exit_code_0_4():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["--version"])
    # Assert
    assert result.exit_code == 0


def test_cli_version_option_emits_a_version_string__assert_scitex_live_paper_in_resu():
    # Arrange
    runner = CliRunner()
    # Act
    result = runner.invoke(cli, ["--version"])
    # Assert
    assert "scitex-live-paper" in result.output




# ---------------------------------------------------------------------------
# Renderer wiring
# ---------------------------------------------------------------------------


def test_renderer_subpackage_reexports_render_index__assert_callable_getattr_renderer():
    # Arrange
    # Act
    from scitex_live_paper import _renderer as renderer_pkg
    # Assert
    assert callable(getattr(renderer_pkg, "render_index", None))


def test_renderer_subpackage_reexports_render_index__assert_renderer_pkg_render_index():
    # Arrange
    # Act
    from scitex_live_paper import _renderer as renderer_pkg
    # Assert
    assert renderer_pkg.render_index is index_module.render_index


# ──────────────────────────────────────────────────────────────────
# End-to-end via a real subprocess (console-script / entry-point regressions)
# ──────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────
# `python -m scitex_live_paper._cli` — module-runnable entry point
# (covers the `if __name__ == "__main__": sys.exit(main())` branch).
# ──────────────────────────────────────────────────────────────────


def test_module_runnable_help_exits_zero__assert_result_returncode_0_resul():
    # Arrange
    # Act
    result = _run_cli("--help")
    # Assert
    assert result.returncode == 0, result.stderr


def test_module_runnable_help_exits_zero__assert_scitex_live_paper_in_resu():
    # Arrange
    # Act
    result = _run_cli("--help")
    # Assert
    assert "scitex-live-paper" in result.stdout.lower()




def test_module_runnable_render_help_exits_zero__assert_result_returncode_0_resul_2():
    # Arrange
    # Act
    result = _run_cli("render", "--help")
    # Assert
    assert result.returncode == 0, result.stderr


def test_module_runnable_render_help_exits_zero__assert_bundle_path_in_result_std():
    # Arrange
    # Act
    result = _run_cli("render", "--help")
    # Assert
    assert "BUNDLE_PATH" in result.stdout


def test_module_runnable_render_help_exits_zero__assert_out_in_result_stdout():
    # Arrange
    # Act
    result = _run_cli("render", "--help")
    # Assert
    assert "--out" in result.stdout




# ──────────────────────────────────────────────────────────────────
# `render <fixture-bundle> --out <tmp>` — real end-to-end
# ──────────────────────────────────────────────────────────────────


def test_render_subprocess_exits_zero_against_fixture_bundle(tmp_path):
    # arrange
    out = tmp_path / "site"

    # act
    result = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))

    # assert
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


def test_render_subprocess_emits_index_html(tmp_path):
    # arrange
    out = tmp_path / "site"

    # act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))

    # assert — landing page lands at the documented location
    assert (out / "index.html").is_file()


def test_render_subprocess_emits_all_four_pages(tmp_path):
    # arrange
    out = tmp_path / "site"

    # act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))

    # assert — the four pages pinned by issue #7
    for page in ("index.html", "viewer.html", "claims.html", "dag.html"):
        assert (out / page).is_file(), f"missing: {page}"


def test_render_subprocess_copies_claims_json_unchanged(tmp_path):
    # arrange
    out = tmp_path / "site"
    original = json.loads((FIXTURE_BUNDLE / "claims.json").read_text(encoding="utf-8"))

    # act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))

    # assert — read-only copy, byte-for-byte JSON equivalence
    copied = json.loads((out / "claims.json").read_text(encoding="utf-8"))
    assert copied == original


def test_render_subprocess_copies_manuscript_pdf__assert_out_manuscript_pdf_is_fil(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert (out / "manuscript.pdf").is_file()


def test_render_subprocess_copies_manuscript_pdf__assert_out_manuscript_pdf_stat_s(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert (out / "manuscript.pdf").stat().st_size > 0




def test_render_subprocess_vendors_pdfjs_assets__assert_pdfjs_is_dir(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    pdfjs = out / "assets" / "pdfjs"
    # Assert
    assert pdfjs.is_dir()


def test_render_subprocess_vendors_pdfjs_assets__assert_any_pdfjs_iterdir(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    pdfjs = out / "assets" / "pdfjs"
    # Assert
    assert any(pdfjs.iterdir())




def test_render_subprocess_vendors_mermaid_assets__assert_mermaid_is_dir(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    mermaid = out / "assets" / "mermaid"
    # Assert
    assert mermaid.is_dir()


def test_render_subprocess_vendors_mermaid_assets__assert_any_mermaid_iterdir(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    mermaid = out / "assets" / "mermaid"
    # Assert
    assert any(mermaid.iterdir())




def test_render_subprocess_pages_contain_no_cdn_references(tmp_path):
    # arrange
    out = tmp_path / "site"
    forbidden = ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com")

    # act
    _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))

    # assert — every emitted HTML page must be CDN-free per #7
    for page in ("index.html", "viewer.html", "claims.html", "dag.html"):
        text = (out / page).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"{page} references {marker}"


def test_render_subprocess_idempotent_on_second_run__assert_first_returncode_0(tmp_path):
    # Arrange
    out = tmp_path / "site"
    first = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Act
    second = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert first.returncode == 0


def test_render_subprocess_idempotent_on_second_run__assert_second_returncode_0(tmp_path):
    # Arrange
    out = tmp_path / "site"
    first = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Act
    second = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert second.returncode == 0


def test_render_subprocess_idempotent_on_second_run__assert_out_index_html_is_file(tmp_path):
    # Arrange
    out = tmp_path / "site"
    first = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Act
    second = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert (out / "index.html").is_file()




def test_render_subprocess_reports_output_paths_on_stdout__assert_index_html_in_result_stdo(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert "index.html" in result.stdout


def test_render_subprocess_reports_output_paths_on_stdout__assert_viewer_html_in_result_std(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert "viewer.html" in result.stdout


def test_render_subprocess_reports_output_paths_on_stdout__assert_claims_html_in_result_std(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert "claims.html" in result.stdout


def test_render_subprocess_reports_output_paths_on_stdout__assert_dag_html_in_result_stdout(tmp_path):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = _run_cli("render", str(FIXTURE_BUNDLE), "--out", str(out))
    # Assert
    assert "dag.html" in result.stdout




# ──────────────────────────────────────────────────────────────────
# Error paths — real exit codes, real stderr
# ──────────────────────────────────────────────────────────────────


def test_render_subprocess_nonzero_exit_for_missing_bundle(tmp_path):
    # arrange
    out = tmp_path / "site"
    # act
    result = _run_cli("render", str(tmp_path / "no-such-bundle"), "--out", str(out))
    # assert
    assert result.returncode != 0


def test_render_subprocess_nonzero_exit_for_malformed_bundle(tmp_path):
    # arrange — bundle dir exists but claims.json is unparseable
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "claims.json").write_text("not json {", encoding="utf-8")
    out = tmp_path / "site"

    # act
    result = _run_cli("render", str(bad), "--out", str(out))

    # assert — loader raises BundleError → CLI ClickException → non-zero exit
    assert result.returncode != 0


def test_render_subprocess_unknown_subcommand_exits_nonzero():
    # Arrange
    # Act
    result = _run_cli("not-a-subcommand")
    # Assert
    assert result.returncode != 0
