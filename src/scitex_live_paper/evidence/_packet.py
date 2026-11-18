"""The review packet: the ONE payload every view is rendered from.

Built from a validated evidence report. The human view (needs-inspection
list, highlighted paper, per-claim graph pages) and the machine adapter
(``export-review`` CLI, MCP tools) all read this dict, so they cannot
disagree. Only registered claims appear; nothing is said about other text.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ._contract import validate_report
from ._states import INSPECTION_ORDER, LABELS, SUPPORTED, SYMBOLS

__all__ = [
    "PACKET_SCHEMA",
    "PACKET_SCHEMA_VERSION",
    "SCOPE",
    "build_review_packet",
    "find_claim",
    "iter_entries",
    "review_text",
]

PACKET_SCHEMA = "scitex-live-paper.review-packet"
PACKET_SCHEMA_VERSION = "1.0.0"

SCOPE = (
    "Registered claims only. Text that is not a registered claim is not "
    "assessed: it may or may not be supported; no graph connects it."
)


def _position(entry: Mapping[str, Any]) -> tuple:
    loc = entry.get("location") or {}
    return (str(loc.get("file") or ""), loc.get("line") or 0, entry["claim_id"])


def _entry(claim: Mapping[str, Any], graph_urls: Mapping[str, str]) -> dict[str, Any]:
    state = claim["state"]
    loc = claim.get("location") or {}
    src = claim.get("source") or {}
    return {
        "claim_id": claim["claim_id"],
        "location": {
            "file": loc.get("file"),
            "line": loc.get("line"),
            "label": loc.get("label"),
        },
        "claim_type": claim.get("claim_type"),
        "stated_text": claim.get("stated_text"),
        "stated_value": claim.get("stated_value"),
        "state": state,
        "label": LABELS[state],
        "symbol": SYMBOLS[state],
        "reason": claim["reason"],
        "needs_inspection": state != SUPPORTED,
        "source": {"file": src.get("file"), "locator": src.get("locator")},
        "details": list(claim.get("details") or []),
        "provider_status": claim.get("provider_status"),
        "graph": claim.get("graph"),
        "graph_error": claim.get("graph_error"),
        "graph_url": graph_urls.get(claim["claim_id"]),
    }


def build_review_packet(
    report: Mapping[str, Any], graph_urls: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Order *report*'s claims for review: needs inspection first, then supported."""
    validate_report(report)
    urls = graph_urls or {}
    rank = {s: i for i, s in enumerate(INSPECTION_ORDER)}
    entries = [_entry(c, urls) for c in report["claims"]]
    needs = sorted(
        (e for e in entries if e["needs_inspection"]),
        key=lambda e: (rank[e["state"]], *_position(e)),
    )
    supported = sorted((e for e in entries if not e["needs_inspection"]), key=_position)
    counts = {s: 0 for s in INSPECTION_ORDER}
    for e in entries:
        counts[e["state"]] += 1
    return {
        "schema": PACKET_SCHEMA,
        "schema_version": PACKET_SCHEMA_VERSION,
        "scope": SCOPE,
        "provider": dict(report["provider"]),
        "evidence_report_version": report["schema_version"],
        "project_root": report.get("project_root"),
        "states": {s: LABELS[s] for s in INSPECTION_ORDER},
        "symbols": {s: SYMBOLS[s] for s in INSPECTION_ORDER},
        "counts": counts,
        "needs_inspection": needs,
        "supported": supported,
    }


def iter_entries(packet: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Every claim entry of a packet, needs-inspection first."""
    yield from packet["needs_inspection"]
    yield from packet["supported"]


def find_claim(packet: Mapping[str, Any], claim_id: str) -> Mapping[str, Any] | None:
    """One claim's packet entry (state, reason, source, graph), or ``None``."""
    return next((e for e in iter_entries(packet) if e["claim_id"] == claim_id), None)


def review_text(packet: Mapping[str, Any]) -> str:
    """Plain-text rendering of a review packet (graphs as edge lists)."""
    counts = ", ".join(
        f"{packet['states'][k]}: {v}" for k, v in packet["counts"].items()
    )
    prov = packet["provider"]
    out = [
        f"Registered-claim evidence review — provider {prov.get('name')} {prov.get('version') or ''}".rstrip(),
        f"schema {packet['schema']} v{packet['schema_version']}",
        packet["scope"],
        f"Counts: {counts}",
        "",
    ]
    for title, key in (
        ("NEEDS INSPECTION", "needs_inspection"),
        ("SUPPORTED", "supported"),
    ):
        out.append(f"== {title} ({len(packet[key])}) ==")
        for e in packet[key]:
            loc = e["location"]
            status = e["provider_status"] or {}
            raw = f" [provider: {status.get('name')}]" if status.get("name") else ""
            out.append(
                f"- {e['symbol']} {e['label']}: {e['claim_id']} @ {loc['file']}:{loc['line']} "
                f'"{e["stated_text"]}" -- {e["reason"]}{raw}'
            )
            src = e["source"]
            out.append(f"    source: {src['file']} locator: {src['locator']}")
            graph = e["graph"]
            if graph is None:
                out.append(
                    f"    minimal graph: none ({e['graph_error'] or 'not supplied'})"
                )
                continue
            names = {n["id"]: f"{n['kind']}:{n['label']}" for n in graph["nodes"]}
            for edge in graph["edges"]:
                out.append(f"    {names[edge['source']]} -> {names[edge['target']]}")
        out.append("")
    return "\n".join(out)
