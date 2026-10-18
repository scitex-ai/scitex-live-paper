"""Serve command: run the standalone Django dev server pinned to a bundle."""

from __future__ import annotations

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from .spec import spec_command_kwargs

__all__ = ["serve_cmd", "register"]


@click.command(
    "serve",
    **spec_command_kwargs(
        summary="Run the standalone Django dev server pinned to a bundle.",
        description=(
            "Requires the [django] extra. The viewer mounts at / and the "
            "catch-all API dispatcher mounts at /<endpoint> (e.g. "
            "/api/ping, /api/bundle-info).",
        ),
        examples=(
            ("{prog} serve bundle/", "Serve on 127.0.0.1:8765."),
            (
                "{prog} serve bundle/ --host 0.0.0.0 --port 8000",
                "Serve on all interfaces, port 8000.",
            ),
        ),
    ),
)
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Interface to bind the dev server to.",
)
@click.option(
    "--port",
    default=8765,
    show_default=True,
    type=int,
    help="Port to bind the dev server to.",
)
def serve_cmd(bundle_path: str, host: str, port: int) -> None:
    """Run the standalone Django dev server pinned to BUNDLE_PATH.

    Requires the ``[django]`` extra. The viewer mounts at ``/`` and the
    catch-all API dispatcher mounts at ``/<endpoint>`` (e.g. ``/api/ping``,
    ``/api/bundle-info``).
    """
    try:
        from scitex_live_paper._django._server import serve as _serve  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without [django]
        raise click.ClickException(
            "the `serve` command requires the [django] extra — "
            "install with: pip install 'scitex-live-paper[django]'"
        ) from exc
    # pragma: no cover reason — `_serve(...)` is `_server.serve()`
    # with no injected runner, which calls Django's `runserver` and
    # binds a TCP port. No-mocks doctrine prohibits patching
    # call_command for a coverage hit; this line only fires from the
    # live `scitex-live-paper serve` CLI.
    _serve(bundle_path, host=host, port=port)  # pragma: no cover


def register(group) -> None:
    """Attach the ``serve`` command to ``group``."""
    group.add_command(serve_cmd)
