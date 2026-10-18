"""Command-line entry point for `scitex-live-paper` (issue #7).

Exposes ``scitex-live-paper render <bundle> --out <site>`` — the M1
end-to-end loop that takes an accepted manuscript bundle and emits a
self-contained static site directory (viewer + claims + DAG + landing
page + vendored assets). The generated site opens straight from
``file://`` — no server required.

The CLI is the thin glue layer: it loads the bundle and calls each
sibling renderer in turn. All claim / DAG semantics live upstream in
``scitex-clew``; this module never invents or validates fields.
"""

from __future__ import annotations

import sys

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from scitex_live_paper import __version__
from .help_tree import emit_help_recursive
from .spec import spec_group_kwargs

__all__ = ["RenderResult", "render_site", "cli", "main"]


# Every visible top-level command MUST be assigned — the auto `Other`
# catch-all is an audit finding and never renders at audit-clean.
_COMMAND_CATEGORIES = (
    ("Core", ("render", "hub-manifest")),
    ("Service", ("serve", "mcp")),
    ("Diagnostics", ("info", "validate")),
    ("Introspection", ("list-python-apis",)),
    ("Shell", ("install-shell-completion", "print-shell-completion")),
)


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    **spec_group_kwargs(
        summary="Emit a static live-paper site from an accepted bundle.",
        description=(
            "The M1 end-to-end loop: load an accepted manuscript bundle "
            "and emit a self-contained static site (viewer + claims + "
            "DAG + landing page + vendored assets) that opens straight "
            "from file:// — no server required. All claim / DAG semantics "
            "live upstream in scitex-clew; this CLI never invents or "
            "validates fields.",
        ),
        config_resolution=(
            "--config PATH (explicit flag wins when the command accepts one)",
            "$SCITEX_LIVE_PAPER_CONFIG (environment override)",
            "<project>/.scitex/live-paper/config.yaml (project scope)",
            "~/.scitex/live-paper/config.yaml (user scope)",
        ),
        version_of="scitex-live-paper",
        command_categories=_COMMAND_CATEGORIES,
    ),
)
@click.option(
    "--help-recursive",
    "help_recursive",
    is_flag=True,
    help="Show help for every subcommand, flattened.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit machine-readable JSON (the command tree for the top level).",
)
@click.version_option(__version__, "-V", "--version", prog_name="scitex-live-paper")
@click.pass_context
def cli(ctx: click.Context, help_recursive: bool, as_json: bool) -> None:
    """Top-level ``scitex-live-paper`` group."""
    if help_recursive or as_json:
        emit_help_recursive(ctx, as_json=as_json)
        ctx.exit(0)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


# Re-exported for back-compat (`from scitex_live_paper._cli import ...`).
from .hub_manifest import hub_manifest_cmd
from .info import _bundle_info_summary, _print_human_summary, info_cmd
from .render import RenderResult, render_cmd, render_site
from .serve import serve_cmd
from .validate import (
    _KNOWN_CLAIM_STATUSES,
    _looks_hex,
    _validate_bundle,
    validate_cmd,
)


# ---------------------------------------------------------------------------
# Command registration — every leaf lives in its own module; this package
# only owns the group, the universal flags, and the registration calls.
# ---------------------------------------------------------------------------
from .completion import register_completion_commands
from .hub_manifest import register as register_hub_manifest
from .info import register as register_info
from .introspect import register as register_introspect
from .mcp import register_mcp_group
from .render import register as register_render
from .serve import register as register_serve
from .validate import register as register_validate

register_render(cli)
register_serve(cli)
register_info(cli)
register_validate(cli)
register_hub_manifest(cli)
register_introspect(cli)
register_mcp_group(cli)
register_completion_commands(cli, prog_name="scitex-live-paper")


def main(argv: list[str] | None = None) -> int:
    """Entrypoint used by the ``[project.scripts]`` declaration.

    Returns the exit code so callers can ``sys.exit(main())`` cleanly.
    """
    try:
        cli.main(args=argv, standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except SystemExit as exc:  # pragma: no cover
        # Defensive — click(standalone_mode=False) is supposed to
        # surface UsageError + ClickException without `sys.exit()`,
        # but plugins / hooks can raise SystemExit unrelated to click.
        # When that happens (rare), preserve the exit code so the
        # console-script returns the same value to the shell.
        return int(exc.code) if exc.code is not None else 0  # pragma: no cover
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via console_scripts
    sys.exit(main())
