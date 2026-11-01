"""Render command: emit a self-contained static site from a bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from scitex_live_paper import bundle as bundle_module
from .spec import spec_command_kwargs
from scitex_live_paper._renderer.claims import render_claims_sidebar
from scitex_live_paper._renderer.dag import render_dag
from scitex_live_paper._renderer.index import render_index
from scitex_live_paper._renderer.viewer import render_viewer

__all__ = ["RenderResult", "render_site", "render_cmd", "register"]


@dataclass(frozen=True)
class RenderResult:
    """Resolved paths of the four pages the site emits.

    The vendored asset paths are intentionally NOT part of the contract
    — callers should look up ``out_dir / "assets" / ...`` if needed.
    """

    out_dir: Path
    index_html: Path
    viewer_html: Path
    claims_html: Path
    dag_html: Path


def render_site(
    bundle_path: str | Path,
    out_dir: str | Path,
    *,
    title: str | None = None,
    project_label: str | None = None,
) -> RenderResult:
    """Render a bundle directory into a self-contained static site.

    Parameters
    ----------
    bundle_path
        Path to the accepted manuscript bundle directory (see
        :mod:`scitex_live_paper.bundle` for the expected layout).
    out_dir
        Output directory. Created if absent. Existing pages are
        overwritten — the render is idempotent.
    title
        Optional shared page title; defaults to ``"Live Paper"`` for the
        landing page and ``"Live Paper — <surface>"`` for the others.
    project_label
        Optional project name shown as static text in the SDK header's
        project slot (static export has no project provider).

    Returns
    -------
    RenderResult
        Resolved paths of the four emitted pages.
    """
    loaded = bundle_module.load(bundle_path)
    out_dir = Path(out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    viewer = render_viewer(
        loaded,
        out_dir,
        title=title or "Live Paper — Viewer",
        project_label=project_label,
    )
    claims = render_claims_sidebar(
        loaded,
        out_dir,
        title=title or "Live Paper — Claims",
        project_label=project_label,
    )
    dag = render_dag(
        loaded,
        out_dir,
        title=title or "Live Paper — DAG",
        project_label=project_label,
    )
    index = render_index(
        loaded,
        out_dir,
        title=title,
        project_label=project_label,
    )

    return RenderResult(
        out_dir=out_dir,
        index_html=index.index_html,
        viewer_html=viewer.viewer_html,
        claims_html=claims.claims_html,
        dag_html=dag.dag_html,
    )
@click.command(
    "render",
    **spec_command_kwargs(
        summary="Render a bundle into a self-contained static site.",
        description=(
            "Loads the accepted manuscript bundle and emits viewer + "
            "claims + DAG + landing page plus vendored assets under "
            "--out. Existing pages are overwritten — the render is "
            "idempotent.",
        ),
        examples=(
            ("{prog} render bundle/ --out site/", "Render into site/."),
            (
                "{prog} render bundle/ --out site/ --title 'My Paper'",
                "Render with a shared page title.",
            ),
        ),
    ),
)
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
@click.option(
    "--out",
    "out_dir",
    required=True,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    help="Output directory for the generated static site.",
)
@click.option(
    "--title",
    default=None,
    help="Optional shared page title (defaults to 'Live Paper').",
)
@click.option(
    "--project-label",
    "project_label",
    default=None,
    help="Optional project name shown as static text in the SDK header "
    "project slot (static export has no project provider).",
)
def render_cmd(bundle_path: str, out_dir: str, title: str | None, project_label: str | None) -> None:
    """Render BUNDLE_PATH into a self-contained static site under --out."""
    try:
        result = render_site(bundle_path, out_dir, title=title, project_label=project_label)
    except bundle_module.BundleError as exc:
        # Surface bundle-layout errors with a clean exit code (no traceback).
        raise click.ClickException(str(exc)) from exc

    click.echo(f"rendered → {result.out_dir}")
    click.echo(f"  index    : {result.index_html.relative_to(result.out_dir)}")
    click.echo(f"  viewer   : {result.viewer_html.relative_to(result.out_dir)}")
    click.echo(f"  claims   : {result.claims_html.relative_to(result.out_dir)}")
    click.echo(f"  dag      : {result.dag_html.relative_to(result.out_dir)}")


def register(group) -> None:
    """Attach the ``render`` command to ``group``."""
    group.add_command(render_cmd)
