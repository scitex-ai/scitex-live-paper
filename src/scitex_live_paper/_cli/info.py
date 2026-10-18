"""Info command: one-screen sanity summary of a bundle."""

from __future__ import annotations

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from scitex_live_paper import bundle as bundle_module
from .spec import spec_command_kwargs

__all__ = ["info_cmd", "_bundle_info_summary", "_print_human_summary", "register"]


@click.command(
    "info",
    **spec_command_kwargs(
        summary="Print a one-screen sanity summary of a bundle.",
        description=(
            "Operator-facing pre-flight check: load the bundle (without "
            "rendering anything) and report claim count + status palette, "
            "paper_state stage + journal + DOI + pinned_commit, manuscript "
            "filename, whether the DAG is embedded, and the claims.json "
            "schema version. Pass --json for a stable machine-parseable "
            "summary.",
        ),
        examples=(
            ("{prog} info bundle/", "Human-readable sanity summary."),
            (
                "{prog} info bundle/ --json | jq .paper_state.stage",
                "Machine-readable summary, staged field extraction.",
            ),
        ),
    ),
)
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit a JSON object instead of the human-readable summary.",
)
def info_cmd(bundle_path: str, as_json: bool) -> None:
    """Print a one-screen sanity summary of BUNDLE_PATH.

    Operator-facing pre-flight check: load the bundle (without rendering
    anything) and report claim count + status palette, paper_state stage
    + journal + DOI + pinned_commit, manuscript filename, whether the
    DAG is embedded, and the claims.json schema version. ``BundleError``
    surfaces as a clean CLI exit (no traceback).

    Pass ``--json`` to emit a stable machine-parseable summary
    (suitable for ``scitex-live-paper info bundle | jq``).
    """
    try:
        bundle = bundle_module.load(bundle_path)
    except bundle_module.BundleError as exc:
        raise click.ClickException(str(exc)) from exc

    payload = _bundle_info_summary(bundle)

    if as_json:
        import json as _json

        click.echo(_json.dumps(payload, indent=2, sort_keys=True))
        return

    _print_human_summary(payload)
def _bundle_info_summary(bundle: "bundle_module.Bundle") -> dict:
    """Build the payload both the human + JSON branches render."""
    from collections import Counter

    palette = Counter(c.status for c in bundle.claims)
    ps = bundle.paper_state
    return {
        "bundle_path": str(bundle.root),
        "manuscript": bundle.manuscript_path.name if bundle.manuscript_path else None,
        "schema_version": bundle.schema_version,
        "claim_count": len(bundle.claims),
        "status_palette": dict(palette),
        "dag_present": bool(bundle.dag and bundle.dag.strip()),
        "paper_state": {
            "stage": ps.stage,
            "header_label": ps.header_label(),
            "journal": ps.journal,
            "doi": ps.doi,
            "accepted_at": ps.accepted_at,
            "pinned_commit": ps.pinned_commit,
            "show_verification_badge": ps.show_verification_badge,
            "re_verify_enabled": ps.re_verify_enabled,
        },
    }


def _print_human_summary(payload: dict) -> None:
    """Render the one-screen operator summary."""
    click.echo(f"bundle    : {payload['bundle_path']}")
    click.echo(f"manuscript: {payload['manuscript'] or '(missing)'}")
    if payload["schema_version"]:
        click.echo(f"schema    : {payload['schema_version']}")
    click.echo(f"claims    : {payload['claim_count']}")
    if payload["status_palette"]:
        # Sort so output is stable across runs.
        items = sorted(payload["status_palette"].items())
        chips = " · ".join(f"{count} {status}" for status, count in items)
        click.echo(f"            {chips}")
    click.echo(f"dag       : {'embedded' if payload['dag_present'] else 'absent'}")
    ps = payload["paper_state"]
    click.echo("paper_state")
    click.echo(f"  stage         : {ps['stage']}")
    click.echo(f"  header_label  : {ps['header_label']}")
    if ps["journal"]:
        click.echo(f"  journal       : {ps['journal']}")
    if ps["doi"]:
        click.echo(f"  doi           : {ps['doi']}")
    if ps["accepted_at"]:
        click.echo(f"  accepted_at   : {ps['accepted_at']}")
    if ps["pinned_commit"]:
        click.echo(f"  pinned_commit : {ps['pinned_commit']}")
    click.echo(
        f"  badge visible : {ps['show_verification_badge']} · "
        f"re-verify : {ps['re_verify_enabled']}"
    )


def register(group) -> None:
    """Attach the ``info`` command to ``group``."""
    group.add_command(info_cmd)
