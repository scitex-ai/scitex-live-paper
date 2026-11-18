"""The provider-neutral evidence-state vocabulary (contract v1)."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "INSPECTION_ORDER",
    "LABELS",
    "NOT_CHECKABLE",
    "NOT_SUPPORTED",
    "NO_EVIDENCE_GRAPH",
    "STATES",
    "SUPPORTED",
    "SYMBOLS",
]

#: Only the first state counts as "supported by evidence".
SUPPORTED = "supported"
NOT_SUPPORTED = "not_supported"
NOT_CHECKABLE = "not_checkable"
NO_EVIDENCE_GRAPH = "no_evidence_graph"

#: The order a reviewer should look in: problems first, supported last.
INSPECTION_ORDER = (NOT_SUPPORTED, NOT_CHECKABLE, NO_EVIDENCE_GRAPH, SUPPORTED)
STATES = frozenset(INSPECTION_ORDER)

#: Plain-language label per state.
LABELS: Mapping[str, str] = {
    SUPPORTED: "Supported by evidence",
    NOT_SUPPORTED: "Not supported",
    NOT_CHECKABLE: "Registered, not checkable",
    NO_EVIDENCE_GRAPH: "No evidence graph",
}

#: One symbol per state, so the state reads without colour.
SYMBOLS: Mapping[str, str] = {
    SUPPORTED: "✓",
    NOT_SUPPORTED: "✗",
    NOT_CHECKABLE: "?",
    NO_EVIDENCE_GRAPH: "∅",
}
