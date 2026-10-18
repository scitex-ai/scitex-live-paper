"""MCP server for scitex-live-paper: projections of the function API.

Single FastMCP instance :data:`mcp`. Every tool projects one name from
the package's function API (``__all__`` non-class callables plus the
nested ``bundle_<verb>`` / ``dag_<verb>`` forms) so the §6 parity check
maps each tool back to a real Python API — no orphan tools, no
uncovered APIs. ``*_skills_list`` / ``*_skills_get`` are the required
§5 skills pair; the package ships no ``_skills/`` directory yet, so the
registry reports itself empty (honestly, not as a stub).

Importing this module requires the ``[mcp]`` extra (``fastmcp``). The
import is guarded: without the extra :data:`mcp` is ``None`` and the
plain tool functions still introspect (for ``mcp list-tools``'s
--json), while ``mcp start`` fails with an install hint. The CLI
imports this module lazily, so ``scitex-live-paper --help`` never pays
the FastMCP import cost and never fails without ``[mcp]``.
"""

from __future__ import annotations

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised without [mcp]
    FastMCP = None  # type: ignore[assignment,misc]

__all__ = ["mcp"]


def _load_bundle(bundle_path: str):
    """Load a bundle or raise a tool-friendly error."""
    from scitex_live_paper import bundle as bundle_module

    try:
        return bundle_module.load(bundle_path)
    except bundle_module.BundleError as exc:
        raise RuntimeError(f"cannot load bundle at {bundle_path!r}: {exc}") from exc


def live_paper_bundle_load(bundle_path: str) -> dict:
    """Load a bundle directory and return the full bundle model as JSON.

    Projects ``bundle_load`` (``scitex_live_paper.bundle.load``): the
    complete machine-readable model — root, manuscript, schema version,
    claims, paper-state lifecycle fields, DAG presence — the same data
    the viewer and API layers read.
    """
    loaded = _load_bundle(bundle_path)
    ps = loaded.paper_state
    return {
        "root": str(loaded.root),
        "manuscript": loaded.manuscript_path.name if loaded.manuscript_path else None,
        "schema_version": loaded.schema_version,
        "claims": [
            {
                "claim_id": c.claim_id,
                "status": c.status,
                "file_path": c.file_path,
                "source_hash": c.source_hash,
            }
            for c in loaded.claims
        ],
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
        "dag_present": bool(loaded.dag and loaded.dag.strip()),
    }


def live_paper_mount(bundle_path: str) -> dict:
    """Return the URL route table a bundle directory would serve.

    Projects :func:`scitex_live_paper.mount`: builds the Django URL
    patterns for a directory-backed resolver and reports the routes
    (viewer, API dispatcher, ports) WITHOUT starting a server.
    Requires the ``[django]`` extra.
    """
    try:
        from scitex_live_paper import BundleContext, BundleSource, mount
    except ImportError as exc:  # pragma: no cover - exercised without [django]
        raise RuntimeError(
            "the `mount` projection requires the [django] extra — "
            "install with: pip install 'scitex-live-paper[django]'"
        ) from exc

    def resolver(**_kw):
        return BundleContext(source=BundleSource.from_directory(bundle_path))

    patterns, namespace = mount(resolver)
    return {
        "namespace": namespace,
        "routes": [str(p.pattern) for p in patterns],
    }


def live_paper_derive_wrapper_manifest(
    label: str | None = None,
    subtitle: str | None = None,
    schema_version: str = "2.0.0",
) -> dict:
    """Return the scitex-hub workspace manifest for this package.

    Projects :func:`scitex_live_paper.derive_wrapper_manifest` — the
    same payload ``scitex-live-paper hub-manifest`` prints.
    """
    from scitex_live_paper import derive_wrapper_manifest

    return derive_wrapper_manifest(
        label=label, subtitle=subtitle, schema_version=schema_version
    )


def live_paper_dag_render_dag(bundle_path: str, out_dir: str) -> dict:
    """Render the DAG pane files for a bundle into ``out_dir``.

    Projects ``dag_render_dag`` (``scitex_live_paper.dag.render_dag``).
    Returns the emitted artifact paths.
    """
    from scitex_live_paper import dag as dag_module

    import dataclasses

    loaded = _load_bundle(bundle_path)
    artifacts = dag_module.render_dag(loaded, out_dir)
    return {
        "out_dir": str(out_dir),
        "artifacts": [str(getattr(artifacts, f.name)) for f in dataclasses.fields(artifacts)],
    }


def live_paper_dag_render_html(bundle_path: str, out_dir: str) -> dict:
    """Render the standalone DAG HTML for a bundle into ``out_dir``.

    Projects ``dag_render_html``
    (``scitex_live_paper.dag.render_html``). Returns the emitted
    artifact paths.
    """
    from scitex_live_paper import dag as dag_module

    import dataclasses

    loaded = _load_bundle(bundle_path)
    artifacts = dag_module.render_html(loaded, out_dir)
    return {
        "out_dir": str(out_dir),
        "artifacts": [str(getattr(artifacts, f.name)) for f in dataclasses.fields(artifacts)],
    }


def _skills_registry() -> dict:
    """Bundled agent-facing skills (markdown leaves under ``_skills/``).

    The package ships no ``_skills/`` directory yet, so the registry is
    empty — reported honestly, not stubbed. When skill leaves land,
    both tools serve them with no interface change.
    """
    from pathlib import Path

    skills_dir = Path(__file__).resolve().parent / "_skills"
    registry: dict[str, str] = {}
    if skills_dir.is_dir():
        for leaf in sorted(skills_dir.rglob("*.md")):
            registry[leaf.stem] = str(leaf)
    return registry


def live_paper_skills_list() -> dict:
    """List the agent-facing skills bundled with this package.

    Required §5 skills pair (with ``live_paper_skills_get``). Empty
    until the package ships ``_skills/`` leaves.
    """
    return {"skills": sorted(_skills_registry())}


def live_paper_skills_get(name: str) -> dict:
    """Return one bundled skill (markdown source) by name.

    Required §5 skills pair (with ``live_paper_skills_list``).
    """
    registry = _skills_registry()
    if name not in registry:
        raise RuntimeError(
            f"unknown skill {name!r} — this package bundles no _skills/ leaves yet"
        )
    from pathlib import Path

    return {"name": name, "markdown": Path(registry[name]).read_text(encoding="utf-8")}


_TOOL_FUNCS = (
    live_paper_bundle_load,
    live_paper_mount,
    live_paper_derive_wrapper_manifest,
    live_paper_dag_render_dag,
    live_paper_dag_render_html,
    live_paper_skills_list,
    live_paper_skills_get,
)

if FastMCP is not None:
    mcp = FastMCP("scitex-live-paper")
    _registered: list = []
    for _func in _TOOL_FUNCS:
        _registered.append(mcp.tool(name=_func.__name__)(_func))
    del _func
    del _registered
else:  # pragma: no cover - exercised without [mcp]
    mcp = None
