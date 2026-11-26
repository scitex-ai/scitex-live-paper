"""Highlighted-paper page: the manuscript text with registered claims marked.

Each registered claim's span (its stated text on its registered line; the
whole line when the text is not found verbatim there) is wrapped in a
``<mark class="lp-claim-span" data-support=...>`` linking to its minimal
evidence graph. Every other character of the manuscript is emitted as plain
escaped text: text that is not a registered claim is not assessed, so it is
never marked — not as supported, not as unsupported. Reader presentation
hides TeX setup; the source toggle reveals every original escaped line.

Rendered from the review packet only (``scitex_live_paper.evidence``), so
the highlights agree with the claims page and the machine adapter.

Navigation (``assets/paper.js``, a classic script so it also runs from
``file://``): selecting a mark (click, tap, Enter) opens an in-page evidence
panel with the claim's state, reason, stated vs source value, source and
locator, and its minimal evidence graph drawn inline (the same mermaid source
as the claim's graph page, failing nodes marked the same way). A claims
navigator lists the claims needing inspection first; ``#claim-<id>`` deep
links open the panel and the browser's back/forward buttons step through the
claims opened. Without JavaScript every mark still links to its graph page
and every navigator entry to its mark.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from scitex_live_paper.evidence import SYMBOLS, iter_entries

from ._sdk_header import copy_sdk_header_assets, header_context
from ._latex_inline import collect_labels
from ._paper_presentation import presentation_lines
from ._values import display_value, value_presentation
from .dag import MERMAID_VERSION, graph_to_mermaid

__all__ = ["PaperArtifacts", "claims_data", "highlight_lines", "render_paper"]

_RENDERER_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _RENDERER_DIR / "assets"
_TEMPLATES_DIR = _RENDERER_DIR / "templates"
_MERMAID_MAIN = "mermaid/mermaid.min.js"
_LATEX_SUFFIXES = {".tex", ".ltx"}
#: Assets the paper page loads, copied verbatim into ``<out>/assets/``.
_PAPER_ASSETS = (
    "claims.css",
    "support.css",
    "paper.css",
    "paper-panel.js",
    "paper.js",
    _MERMAID_MAIN,
)


@dataclass(frozen=True)
class PaperArtifacts:
    paper_html: Path
    files: tuple[str, ...]


def _mark(entry: Mapping[str, Any], inner: str) -> str:
    title = f"{entry['label']}: {entry['reason']}"
    href = entry.get("graph_url") or "#"
    return (
        f'<mark class="lp-claim-span" id="claim-{escape(entry["claim_id"])}" '
        f'data-claim-id="{escape(entry["claim_id"])}" data-support="{escape(entry["state"])}" '
        f'title="{escape(title)}"><a href="{escape(href)}" aria-haspopup="dialog" '
        f'aria-controls="lp-claim-panel">{inner}'
        f'<sup aria-label="{escape(entry["label"])}">{escape(entry["symbol"])}</sup></a></mark>'
    )


def highlight_lines(text: str, entries: list[Mapping[str, Any]]) -> list[Markup]:
    """Escape *text* line by line, marking each registered claim's span.

    Registered ``\\vclaim{id}`` macros display their stated value. This
    never substitutes a source value or changes the provider's verdict.
    Untagged text is returned escaped and unmarked.
    """
    by_line: dict[int, list[Mapping[str, Any]]] = {}
    for e in entries:
        line = e["location"].get("line")
        if isinstance(line, int):
            by_line.setdefault(line, []).append(e)

    out: list[Markup] = []
    for n, raw in enumerate(text.splitlines(), start=1):
        claims = by_line.get(n, [])
        if not claims:
            out.append(Markup(escape(raw)))
            continue
        pieces: list[tuple[int, int, Mapping[str, Any], str]] = []
        whole: list[Mapping[str, Any]] = []
        for e in claims:
            stated = e.get("stated_text") or ""
            at = raw.find(stated) if stated else -1
            end, display = at + len(stated), stated
            macro = re.search(
                r"\\vclaim\s*\{\s*" + re.escape(e["claim_id"]) + r"\s*\}", raw
            )
            value = display_value(e.get("stated_value"), e.get("stated_text"))
            if macro is not None and value is not None:
                at, end = macro.span()
                display = value
            taken = any(a < end and at < b for a, b, _, _ in pieces)
            if at >= 0 and not taken:
                pieces.append((at, end, e, display))
            else:
                whole.append(e)
        pieces.sort(key=lambda p: p[0])
        html, pos = [], 0
        for a, b, e, display in pieces:
            html.append(str(escape(raw[pos:a])))
            html.append(_mark(e, str(escape(display))))
            pos = b
        html.append(str(escape(raw[pos:])))
        line_html = "".join(html)
        for e in whole:
            line_html = _mark(e, line_html)
        out.append(Markup(line_html))
    return out


#: Packet-entry keys the in-page panel reads (everything it shows).
_CLIENT_KEYS = (
    "claim_id",
    "location",
    "claim_type",
    "stated_text",
    "stated_value",
    "state",
    "label",
    "symbol",
    "reason",
    "needs_inspection",
    "source",
    "details",
    "provider_status",
    "graph",
    "failing_nodes",
    "graph_error",
    "graph_url",
)


def claims_data(review: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The packet's entries as the paper page embeds them, needs-inspection first.

    Each entry is the packet entry (same keys, same values) plus ``mermaid``:
    the exact mermaid source the claim's graph page draws, so the inline graph
    and the graph page cannot differ (``None`` when the claim has no graph);
    ``stated_display``: the stated value as the manuscript states it; and
    ``value_check``: how the source value relates to it (``None`` when the
    provider reported no source value).
    """
    out = []
    for e in iter_entries(review):
        item = {k: e.get(k) for k in _CLIENT_KEYS}
        item.update(value_presentation(e))
        graph = e.get("graph")
        item["mermaid"] = (
            graph_to_mermaid(graph, state=e["state"])[0] if graph else None
        )
        out.append(item)
    return out


def manuscript_text_entries(review: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    """Group claims by text source, excluding PDF regions."""
    by_file: dict[str, list[Mapping[str, Any]]] = {}
    for entry in iter_entries(review):
        source = entry["location"].get("file")
        if source and Path(source).suffix.lower() != ".pdf":
            by_file.setdefault(source, []).append(entry)
    return by_file


def render_paper(
    review: Mapping[str, Any],
    out_dir: str | Path,
    *,
    text_root: str | Path | None = None,
    claims_url: str = "claims.html",
    title: str | None = None,
    project_label: str | None = None,
    read_text: Callable[[str], str | None] | None = None,
    asset_url: Callable[[str], str] | None = None,
) -> PaperArtifacts | None:
    """Render ``paper.html`` from *review*; ``None`` when no source text is readable.

    Manuscript files named by the claims' ``location.file`` are read relative
    to *text_root* (default: the packet's ``project_root``).
    A host may supply ``read_text`` to resolve every source through its own
    authorized storage capability, and ``asset_url`` to bind resource URLs.
    """
    base = text_root or review.get("project_root")
    if base is None and read_text is None:
        return None
    root = Path(base) if base is not None else None
    by_file = manuscript_text_entries(review)

    texts = {}
    for rel in sorted(by_file):
        if read_text is not None:
            text = read_text(rel)
            if text is None:
                continue
        else:
            path = Path(rel) if Path(rel).is_absolute() else root / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        texts[rel] = text
    # \ref links resolve across every rendered file, not only the current one.
    labels = collect_labels(
        t for rel, t in texts.items() if Path(rel).suffix.lower() in _LATEX_SUFFIXES
    )
    sections = []
    for rel, text in texts.items():
        lines = highlight_lines(text, by_file[rel])
        is_latex = Path(rel).suffix.lower() in _LATEX_SUFFIXES
        sections.append({
            "file": rel,
            "lines": lines,
            "is_latex": is_latex,
            "reader_lines": presentation_lines(
                text, lines, is_latex=is_latex, labels=labels
            ),
        })
    if not sections:
        return None

    out_dir = Path(out_dir).expanduser().resolve()
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    for name in _PAPER_ASSETS:
        (out_dir / "assets" / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ASSETS_DIR / name, out_dir / "assets" / name)
    copy_sdk_header_assets(out_dir)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
        keep_trailing_newline=True,
    )
    entries = list(iter_entries(review))
    asset = asset_url if asset_url is not None else str
    html = env.get_template("paper.html.j2").render(
        title=title or "Live Paper — Paper",
        review=review,
        symbols=SYMBOLS,
        sections=sections,
        claims_url=claims_url,
        nav_groups=[
            ("Needs inspection", [e for e in entries if e["needs_inspection"]]),
            ("Supported", [e for e in entries if not e["needs_inspection"]]),
        ],
        claims_data=claims_data(review),
        css_url=asset("assets/claims.css"),
        support_css_url=asset("assets/support.css"),
        paper_css_url=asset("assets/paper.css"),
        paper_panel_js_url=asset("assets/paper-panel.js"),
        paper_js_url=asset("assets/paper.js"),
        mermaid_url=asset(f"assets/{_MERMAID_MAIN}"),
        mermaid_version=MERMAID_VERSION,
        **header_context(project_label=project_label, asset_url=asset_url),
    )
    dest = out_dir / "paper.html"
    dest.write_text(html, encoding="utf-8")
    return PaperArtifacts(paper_html=dest, files=tuple(s["file"] for s in sections))
