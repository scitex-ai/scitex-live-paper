"""Evidence pages of the static site, all rendered from ONE review packet.

Emits, beside the existing pages:

- ``paper.html`` — the manuscript with each registered claim marked by state;
- ``claim-graph-*.html`` — one minimal-evidence-graph page per claim;
- ``review.json`` / ``review.txt`` — the same packet for an AI reviewer.

The claims page and the landing page receive the same packet object, so
every human surface and the machine adapter agree by construction.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scitex_live_paper.bundle import Bundle
from scitex_live_paper.evidence import (
    EvidenceError,
    build_review_packet,
    collect_report,
    find_provider,
    iter_entries,
    load_report,
    review_text,
)

from .dag import claim_graph_filename, render_claim_graph
from .paper import render_paper

__all__ = [
    "EvidenceError",
    "EvidencePages",
    "render_evidence_pages",
    "resolve_evidence_report",
    "write_review",
]



@dataclass(frozen=True)
class EvidencePages:
    packet: Mapping[str, Any]
    paper_html: Path | None
    paper_url: str | None
    review_json: Path
    review_txt: Path
    graph_pages: tuple[Path, ...]


def resolve_evidence_report(
    bundle: Bundle,
    *,
    report_path: str | Path | None = None,
    provider: str | None = None,
    project_root: str | Path | None = None,
) -> Mapping[str, Any] | None:
    """The evidence report for *bundle*, or ``None`` when none was asked for.

    A report file wins; otherwise the named (or single installed) provider
    assesses *project_root* (default: the bundle directory), restricted to
    the bundle's claims.
    """
    if report_path is not None:
        return load_report(report_path)
    if provider is None and project_root is None:
        return None
    _name, adapter = find_provider(provider)
    root = str(Path(project_root or bundle.root).expanduser().resolve())
    claim_ids = [c.claim_id for c in bundle.claims] or None
    return collect_report(adapter, root, claim_ids=claim_ids)


def write_review(packet: Mapping[str, Any], out_dir: Path) -> tuple[Path, Path]:
    """Write ``review.json`` + ``review.txt`` (the machine-readable adapter)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    as_json = out_dir / "review.json"
    as_text = out_dir / "review.txt"
    as_json.write_text(
        json.dumps(packet, indent=2, default=str) + "\n", encoding="utf-8"
    )
    as_text.write_text(review_text(packet) + "\n", encoding="utf-8")
    return as_json, as_text


def render_evidence_pages(
    report: Mapping[str, Any],
    out_dir: str | Path,
    *,
    bundle: Bundle | None = None,
    project_label: str | None = None,
) -> EvidencePages:
    """Build the review packet from *report* and render every evidence page."""
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    urls = {
        c["claim_id"]: claim_graph_filename(c["claim_id"]) for c in report["claims"]
    }
    packet = build_review_packet(report, urls)

    text_root = packet.get("project_root") or (str(bundle.root) if bundle else None)
    paper = render_paper(packet, out, text_root=text_root, project_label=project_label)
    paper_url = "paper.html" if paper is not None else None

    pages = tuple(
        render_claim_graph(e, out, paper_url=paper_url, project_label=project_label)
        for e in iter_entries(packet)
    )
    review_json, review_txt = write_review(packet, out)
    return EvidencePages(
        packet=packet,
        paper_html=paper.paper_html if paper else None,
        paper_url=paper_url,
        review_json=review_json,
        review_txt=review_txt,
        graph_pages=pages,
    )
