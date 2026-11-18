"""The provider-neutral evidence-state vocabulary (contract v1)."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "FAILURE_LABELS",
    "FAILURE_SYMBOL",
    "INSPECTION_ORDER",
    "LABELS",
    "NOT_CHECKABLE",
    "NOT_SUPPORTED",
    "NO_EVIDENCE_GRAPH",
    "STATES",
    "SUPPORTED",
    "SYMBOLS",
    "failure_label",
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


#: Graph nodes where the evidence broke (contract 1.1.0 ``node.failure``).
#: The recommended kinds get a fixed label; any other token shows verbatim.
FAILURE_LABELS: Mapping[str, str] = {
    "changed": "Changed",
    "missing": "Missing",
    "mismatched": "Mismatched",
}
#: Leads every failure label, so a failing node reads without colour.
FAILURE_SYMBOL = "⚠"


def failure_label(kind: str) -> str:
    """Plain-language label of a node failure kind (verbatim if unknown)."""
    return FAILURE_LABELS.get(kind, kind.replace("_", " ").capitalize())
