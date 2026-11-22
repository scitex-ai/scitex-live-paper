"""DAG navigator HTML renderer (issue #6).

Emits a standalone ``dag.html`` site page that renders the bundle's
``dag.mmd`` mermaid string with vendored mermaid, then wires click
handlers so Claim nodes open the matching claim panel via the same
``live-paper:claim`` event channel used by the PDF viewer (#4) and the
claims sidebar (#5).

Boundary
--------
The DAG structure and the node-class taxonomy are **owned upstream by
whoever produced** ``dag.mmd``. This renderer just paints what the
bundle's ``dag.mmd`` already encodes — it does not add, rewrite, or
normalise nodes. Per-claim minimal evidence graphs
(:func:`render_claim_graph`) likewise draw exactly the nodes and edges the
evidence provider supplied.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper dag renderer requires Jinja2 — "
        "install the package (or `pip install jinja2`)"
    ) from exc

from scitex_live_paper.bundle import Bundle
from scitex_live_paper.evidence import FAILURE_SYMBOL, failure_label

from ._sdk_header import copy_sdk_header_assets, header_context

__all__ = [
    "MERMAID_VERSION",
    "DagArtifacts",
    "claim_graph_filename",
    "graph_to_mermaid",
    "render_claim_graph",
    "render_dag",
    "render_html",
]

# Vendored mermaid UMD bundle version (see assets/mermaid/README.md).
MERMAID_VERSION = "10.9.4"

_RENDERER_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _RENDERER_DIR / "assets"
_TEMPLATES_DIR = _RENDERER_DIR / "templates"
_MERMAID_DIR = _ASSETS_DIR / "mermaid"
_MERMAID_MAIN = "mermaid.min.js"
_DAG_CSS = _ASSETS_DIR / "dag.css"
_DAG_JS = _ASSETS_DIR / "dag.js"


@dataclass(frozen=True)
class DagArtifacts:
    """Paths of every artefact the DAG renderer wrote."""

    dag_html: Path
    css: Path
    js: Path
    mermaid_main: Path


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
        keep_trailing_newline=True,
    )


def _copy_into(out_dir: Path, rel_dest: str, source: Path) -> Path:
    dest = out_dir / rel_dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return dest


def render_dag(
    bundle: Bundle,
    out_dir: str | Path,
    *,
    title: str | None = None,
    viewer_url: str = "viewer.html",
    claims_url: str = "claims.html",
    project_label: str | None = None,
) -> DagArtifacts:
    """Render the M1 DAG navigator page for *bundle* into *out_dir*.

    Parameters
    ----------
    bundle
        Loaded :class:`scitex_live_paper.bundle.Bundle`. Reads
        ``bundle.dag`` for the mermaid source and the provenance map
        for ``source_hash`` lookup on Source / Processing nodes.
    out_dir
        Output directory. Created if absent. Existing files are
        overwritten — the renderer is idempotent.
    title
        Optional page title; defaults to ``"Live Paper — DAG"``.
    viewer_url
        Used when click-through links jump to the PDF viewer.
    claims_url
        Used when click-through links jump to the claims sidebar.

    Returns
    -------
    DagArtifacts
        Resolved paths so the CLI (#7) can wire ``index.html``.
    """
    out_dir = Path(out_dir).expanduser().resolve()
    css_dest, js_dest, mermaid_dest = _copy_dag_assets(out_dir)

    # Provenance hash lookup: source_file -> source_hash. This lets the
    # DAG overlay show "script + hash" for Source / Processing nodes
    # without re-walking the provenance graph in JavaScript.
    provenance_map = _collect_source_hashes(bundle)

    env = _jinja_env()
    template = env.get_template("dag.html.j2")
    html = template.render(
        title=title or "Live Paper — DAG",
        subtitle=None,
        claim=None,
        # mermaid expects the raw graph source; pass it through verbatim.
        # NB: the template wraps it in a <pre class="mermaid"> block which
        # mermaid.init() picks up on DOMContentLoaded.
        dag_source=bundle.dag or 'graph LR\n  empty["no dag.mmd in bundle"]',
        has_dag=bool(bundle.dag and bundle.dag.strip()),
        css_url="assets/dag.css",
        js_url="assets/dag.js",
        mermaid_url=f"assets/mermaid/{_MERMAID_MAIN}",
        mermaid_version=MERMAID_VERSION,
        viewer_url=viewer_url,
        claims_url=claims_url,
        provenance_map=provenance_map,
        **header_context(project_label=project_label),
    )
    dag_html = out_dir / "dag.html"
    dag_html.write_text(html, encoding="utf-8")

    return DagArtifacts(
        dag_html=dag_html,
        css=css_dest,
        js=js_dest,
        mermaid_main=mermaid_dest,
    )


def _copy_dag_assets(out_dir: Path) -> tuple[Path, Path, Path]:
    """Copy the DAG page's CSS / JS / vendored mermaid into *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assets" / "mermaid").mkdir(parents=True, exist_ok=True)
    css_dest = _copy_into(out_dir, "assets/dag.css", _DAG_CSS)
    js_dest = _copy_into(out_dir, "assets/dag.js", _DAG_JS)
    # Canonical SDK AppHeader (header-parity): its CSS/JS travel with the
    # site so the component mounts over http(s). file:// keeps the static
    # fallback title line (module scripts don't run there — documented in
    # docs/dev-quickstart.md).
    copy_sdk_header_assets(out_dir)
    mermaid_dest = _copy_into(
        out_dir, f"assets/mermaid/{_MERMAID_MAIN}", _MERMAID_DIR / _MERMAID_MAIN
    )
    return css_dest, js_dest, mermaid_dest


# ---------------------------------------------------------------------------
# Per-claim minimal evidence graph (from the evidence provider)
# ---------------------------------------------------------------------------

_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def claim_graph_filename(claim_id: str) -> str:
    """Site-relative file name of a claim's minimal-graph page.

    Claim ids are author-chosen strings; the name keeps a readable slug and
    adds a short digest so two ids that slug alike never collide.
    """
    slug = _SAFE_ID.sub("-", claim_id).strip("-")[:48] or "claim"
    digest = hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:8]
    return f"claim-graph-{slug}-{digest}.html"


def _mermaid_escape(text: str) -> str:
    return str(text).replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;")


def _mermaid_label(kind: str, text: str, failure: str | None = None) -> str:
    # mermaid entity escapes; the kind prefix is what dag.js keys node
    # decoration on (the node taxonomy: Claim / Processing / Input /
    # Output). A failing node gets a LAST line led by FAILURE_SYMBOL, which
    # dag.js strips from the click payload.
    tail = f"<br/>{FAILURE_SYMBOL} {_mermaid_escape(failure)}" if failure else ""
    return f'"{kind}<br/>{_mermaid_escape(text)}{tail}"'


_KIND_LABEL = {
    "process": ("Processing", "run"),
    "input": ("Input", "file"),
    "output": ("Output", "file"),
    "claim": ("Claim", None),
}


def graph_to_mermaid(
    graph: Mapping[str, Any], *, state: str | None = None
) -> tuple[str, dict[str, str]]:
    """Mermaid source + ``{node label: hash}`` map for a claim's minimal graph.

    *graph* is a review-packet entry's ``graph`` (contract nodes/edges,
    supplied by the evidence provider): this draws exactly
    its nodes and edges, nothing more, so the page and the packet agree.
    """
    ids = {n["id"]: f"n{i}" for i, n in enumerate(graph["nodes"])}
    lines = ["graph LR"]
    provenance: dict[str, str] = {}
    interpretations = {
        edge["target"] for edge in graph["edges"]
        if edge.get("relation") == "author_interpretation"
    }
    for n in graph["nodes"]:
        kind, cls = _KIND_LABEL.get(n["kind"], (n["kind"].title(), "file"))
        if n["kind"] == "claim":
            cls = state or "registered"
            if n["id"] in interpretations:
                kind += " · ✒ Author interpretation"
        elif n["kind"] in {"input", "output"} and n.get("author_registered") is True:
            kind += " · ✒ Author-registered source"
            cls = "author_source"
        failure = n.get("failure")
        marker = None
        if failure:
            # Where the evidence broke: own class (thick dash-dot outline,
            # hatched-look fill) AND a text label, never colour alone.
            cls = "failing"
            marker = failure_label(failure["kind"]).upper()
        lines.append(
            f"  {ids[n['id']]}[{_mermaid_label(kind, n['label'], marker)}]:::{cls}"
        )
        if n.get("hash"):
            provenance[str(n["label"])] = str(n["hash"])
    claim_nodes = {node["id"] for node in graph["nodes"] if node["kind"] == "claim"}
    for edge in graph["edges"]:
        source, target = edge["source"], edge["target"]
        interpretation = edge.get("relation") == "author_interpretation" and target in claim_nodes
        label = "|Author interpretation|" if interpretation else ""
        lines.append(f"  {ids[source]} -->{label} {ids[target]}")
    lines += [
        "  classDef run fill:#e3f1fa,stroke:#005a8c",
        "  classDef file fill:#f6f8fa,stroke:#57606a",
        "  classDef author_source fill:#e0f2ee,stroke:#258773",
        "  classDef supported fill:#e6f4ea,stroke:#2ea043,stroke-width:3px",
        "  classDef not_supported fill:#fde6d8,stroke:#b34700,stroke-width:3px,stroke-dasharray:6 3",
        "  classDef not_checkable fill:#fdf0c8,stroke:#7a5400,stroke-width:3px,stroke-dasharray:2 2",
        "  classDef no_evidence_graph fill:#ececec,stroke:#4d4d4d,stroke-width:2px",
        "  classDef registered fill:#ececec,stroke:#4d4d4d",
        # Okabe-Ito vermillion + black text; a dash-dot outline no other
        # class uses, so the node also differs in pattern, not only hue.
        "  classDef failing fill:#ffd9c2,stroke:#9e3a00,stroke-width:5px,"
        "stroke-dasharray:12 4 3 4,color:#000000,font-weight:bold",
    ]
    return "\n".join(lines) + "\n", provenance


def render_claim_graph(
    entry: Mapping[str, Any],
    out_dir: str | Path,
    *,
    viewer_url: str = "viewer.html",
    claims_url: str = "claims.html",
    paper_url: str | None = None,
    project_label: str | None = None,
    asset_url: Callable[[str], str] | None = None,
) -> Path:
    """Render one claim's minimal evidence graph page (``claim-graph-*.html``).

    *entry* is the claim's review-packet entry
    (:func:`scitex_live_paper.evidence.build_review_packet`). Same page,
    assets and click wiring as :func:`render_dag`; the graph is the claim's
    minimal evidence graph instead of the bundle's whole ``dag.mmd``.
    """
    out_dir = Path(out_dir).expanduser().resolve()
    _copy_dag_assets(out_dir)
    _copy_into(out_dir, "assets/support.css", _ASSETS_DIR / "support.css")
    claim_id = entry["claim_id"]
    graph = entry.get("graph")
    if graph is not None:
        source, provenance = graph_to_mermaid(graph, state=entry["state"])
        summary = graph.get("summary")
    else:
        source, provenance, summary = "", {}, None

    template = _jinja_env().get_template("dag.html.j2")
    asset = asset_url if asset_url is not None else str
    html = template.render(
        title=f"Live Paper — evidence graph for {claim_id}",
        subtitle=(
            f"Minimal evidence graph of claim {claim_id}"
            + (f" · {summary}" if summary else "")
        ),
        claim=entry,
        support_css_url=asset("assets/support.css"),
        paper_url=paper_url,
        dag_source=source,
        has_dag=bool(source),
        css_url=asset("assets/dag.css"),
        js_url=asset("assets/dag.js"),
        mermaid_url=asset(f"assets/mermaid/{_MERMAID_MAIN}"),
        mermaid_version=MERMAID_VERSION,
        viewer_url=viewer_url,
        claims_url=claims_url,
        provenance_map=provenance,
        **header_context(project_label=project_label, asset_url=asset_url),
    )
    dest = out_dir / claim_graph_filename(claim_id)
    dest.write_text(html, encoding="utf-8")
    return dest


def _collect_source_hashes(bundle: Bundle) -> dict[str, str]:
    """Build a ``{source_file: source_hash}`` map from the bundle.

    Sources of truth, in order:
      1. The claims list — each claim already carries ``source_file`` +
         ``source_hash`` from the claim registry.
      2. The provenance graph — ``sessions[<sess>].files[<path>].hash``
         shape, if present. Lenient: missing branches are skipped.
    """
    out: dict[str, str] = {}
    for c in bundle.claims:
        if c.source_file and c.source_hash:
            out.setdefault(c.source_file, c.source_hash)

    sessions = bundle.provenance.get("sessions") if bundle.provenance else None
    if isinstance(sessions, dict):
        for _sid, sess in sessions.items():
            if not isinstance(sess, dict):
                continue
            files = sess.get("files")
            if not isinstance(files, dict):
                continue
            for path, meta in files.items():
                if not isinstance(meta, dict):
                    continue
                hsh = meta.get("hash")
                if isinstance(hsh, str) and path not in out:
                    out[path] = hsh
    return out


# ---------------------------------------------------------------------------
# Compat alias
# ---------------------------------------------------------------------------


def render_html(bundle: Bundle, out_dir: str | Path, **kwargs) -> DagArtifacts:
    """Alias of :func:`render_dag`.

    The PR #13 test scaffolding (issue #10) pinned ``render_html`` as
    the expected public callable for this module; keep it as a thin
    alias so the scaffolded contract continues to hold.
    """
    return render_dag(bundle, out_dir, **kwargs)
