"""Hub-manifest command: print the scitex-hub workspace manifest."""

from __future__ import annotations

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from .spec import spec_command_kwargs

__all__ = ["hub_manifest_cmd", "register"]


@click.command(
    "hub-manifest",
    **spec_command_kwargs(
        summary="Print the scitex-hub workspace manifest as JSON.",
        description=(
            "Hub-side wrapper apps (e.g. "
            "apps/workspace/live_paper_app/manifest.json) can regenerate "
            "the file via redirect. The output is the v2.0.0 hub "
            "workspace UI shape — derived from "
            "scitex_live_paper.HUB_APP_MANIFEST. Default formatting is "
            "indented + sort_keys=True so successive runs produce "
            "stable, review-friendly diffs.",
        ),
        examples=(
            ("{prog} hub-manifest > manifest.json", "Regenerate the wrapper manifest."),
            (
                "{prog} hub-manifest --compact | head -c 200",
                "Single-line JSON for piping.",
            ),
        ),
    ),
)
@click.option(
    "--label",
    default=None,
    help="Override workspace tile title (default: HUB_APP_MANIFEST display_name).",
)
@click.option(
    "--subtitle",
    default=None,
    help="Override short tagline (default: first sentence of description).",
)
@click.option(
    "--schema-version",
    default="2.0.0",
    show_default=True,
    help="Hub manifest schema_version to declare.",
)
@click.option(
    "--compact",
    is_flag=True,
    default=False,
    help="Emit single-line JSON (default: indented + sorted for stable VCS diffs).",
)
def hub_manifest_cmd(
    label: str | None,
    subtitle: str | None,
    schema_version: str,
    compact: bool,
) -> None:
    """Print the scitex-hub workspace manifest as JSON.

    Hub-side wrapper apps (e.g. ``apps/workspace/live_paper_app/manifest.json``)
    can regenerate the file via:

    \b
        scitex-live-paper hub-manifest > manifest.json

    The output is the v2.0.0 hub workspace UI shape — derived from
    :data:`scitex_live_paper.HUB_APP_MANIFEST` via
    :func:`scitex_live_paper.derive_wrapper_manifest`. Default formatting
    is indented + ``sort_keys=True`` so successive runs produce stable,
    review-friendly diffs.

    Useful per-wrapper overrides:

    \b
        --label "Live Paper"
        --subtitle "Mounted under apps/live-paper/<paper_id>/"
    """
    import json as _json

    from scitex_live_paper import derive_wrapper_manifest

    manifest = derive_wrapper_manifest(
        label=label,
        subtitle=subtitle,
        schema_version=schema_version,
    )

    if compact:
        click.echo(_json.dumps(manifest, sort_keys=True))
    else:
        click.echo(_json.dumps(manifest, sort_keys=True, indent=2))


def register(group) -> None:
    """Attach the ``hub-manifest`` command to ``group``."""
    group.add_command(hub_manifest_cmd)
