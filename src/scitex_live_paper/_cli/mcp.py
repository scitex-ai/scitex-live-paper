"""``scitex-live-paper mcp`` group — MCP server verbs.

``list-tools`` enumerates the tools registered on
:mod:`scitex_live_paper._mcp_server` with the ``-v``/``-vv``/``-vvv``
ladder (names / +signatures / +summaries / +sources+schemas) and a
``--json`` machine-readable form. ``start`` launches the server over
stdio. Both require the ``[mcp]`` extra; without it they fail with an
install hint instead of a traceback.
"""

from __future__ import annotations

import inspect
import json

import click

from .spec import spec_command_kwargs, spec_group_kwargs

__all__ = ["register_mcp_group"]


def _load_server():
    """Import the FastMCP server module (works with or without [mcp]).

    The module's ``fastmcp`` import is guarded, so the plain tool
    functions introspect even when the extra is absent — only
    ``mcp start`` needs a live server object.
    """
    try:
        from scitex_live_paper import _mcp_server as server
    except ImportError as exc:
        raise _install_hint() from exc
    return server


def _require_live_server():
    """Return the server module, or fail cleanly when [mcp] is absent."""
    server = _load_server()
    if server.mcp is None:  # pragma: no cover - exercised without [mcp]
        raise _install_hint()
    return server


def _install_hint() -> click.ClickException:
    """The [mcp]-missing error both entry points raise."""
    return click.ClickException(
        "scitex-live-paper MCP tools require the [mcp] extra:\n"
        "  pip install 'scitex-live-paper[mcp]'"
    )


def _tool_records() -> list[dict]:
    """Introspect the registered tool functions into plain records."""
    server = _load_server()
    records: list[dict] = []
    for name in sorted(dir(server)):
        if not name.startswith("live_paper_"):
            continue
        func = getattr(server, name)
        if not inspect.isfunction(func):
            continue
        try:
            signature = str(inspect.signature(func))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            signature = "(...)"
        doc = inspect.getdoc(func) or ""
        try:
            source = inspect.getsourcefile(func) or ""
        except TypeError:  # pragma: no cover - defensive
            source = ""
        schema: dict[str, str] = {}
        try:
            for pname, param in inspect.signature(func).parameters.items():
                ann = param.annotation
                schema[pname] = getattr(ann, "__name__", str(ann))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            pass
        records.append(
            {
                "name": name,
                "signature": signature,
                "summary": doc.splitlines()[0] if doc else "",
                "doc": doc,
                "source": source,
                "schema": schema,
            }
        )
    return records


def register_mcp_group(cli: click.Group) -> None:
    """Attach the ``mcp`` group (``list-tools`` + ``start``) to ``cli``."""

    @cli.group(
        "mcp",
        **spec_group_kwargs(
            summary="Model Context Protocol server verbs.",
            description=(
                "Serve the bundle-inspection tools to MCP clients "
                "(``start``) or enumerate them (``list-tools``). "
                "Requires the [mcp] extra.",
            ),
        ),
    )
    def mcp() -> None:
        """Serve bundle-inspection tools over MCP."""

    @mcp.command(
        "list-tools",
        **spec_command_kwargs(
            summary="List the MCP tools registered by this package.",
            description=(
                "Verbosity is additive: -v adds signatures, -vv adds "
                "docstring summaries, -vvv adds source paths + arg schemas.",
            ),
            examples=(
                ("{prog} mcp list-tools -v", "List with signatures."),
                ("{prog} mcp list-tools --json", "Full records as JSON."),
            ),
        ),
    )
    @click.option(
        "-v",
        "--verbose",
        count=True,
        help="Add detail (repeatable): -v signatures, -vv summaries, -vvv sources+schemas.",
    )
    @click.option(
        "--json",
        "as_json",
        is_flag=True,
        help="Emit the tool list as JSON (rich records, independent of -v).",
    )
    def list_tools_cmd(verbose: int, as_json: bool) -> None:
        """List the MCP tools this package serves."""
        records = _tool_records()
        if as_json:
            click.echo(json.dumps(records))
            return
        for entry in records:
            if verbose == 0:
                click.echo(entry["name"])
                continue
            click.echo(f"{entry['name']}{entry['signature']}")
            if verbose >= 2 and entry["summary"]:
                click.echo(f"    {entry['summary']}")
            if verbose >= 3:
                if entry["source"]:
                    click.echo(f"    [{entry['source']}]")
                for arg, atype in entry["schema"].items():
                    click.echo(f"    {arg}: {atype}")

    @mcp.command(
        "start",
        **spec_command_kwargs(
            summary="Launch the MCP server over stdio.",
            description=(
                "Serves the bundle-inspection tools to MCP clients. "
                "Requires the [mcp] extra.",
            ),
            examples=(
                ("{prog} mcp start", "Serve tools over stdio."),
                (
                    "{prog} mcp start --dry-run",
                    "Print the launch plan without serving.",
                ),
            ),
        ),
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Print what would happen (transport) and exit 0 without launching.",
    )
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="Proceed without confirmation (this command never prompts anyway).",
    )
    def start_cmd(dry_run: bool, yes: bool) -> None:
        """Launch the MCP server (stdio transport)."""
        _ = yes  # accepted for §2 compliance; start never prompts.
        if dry_run:
            click.echo("# dry-run: would launch MCP server transport=stdio")
            return
        server = _require_live_server()
        server.mcp.run()

    # EOF
