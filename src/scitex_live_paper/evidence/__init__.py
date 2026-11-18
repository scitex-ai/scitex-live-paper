"""Evidence states of registered claims — the provider-neutral contract.

live-paper shows which REGISTERED claims are supported by evidence and which
need inspection, with each claim's minimal evidence graph. It computes none
of this: an evidence provider does, through the contract documented in
``docs/evidence-provider-contract.md`` (report schema
``scitex-live-paper.evidence-report`` v1, shipped as
``evidence-report.schema.json``). live-paper imports no provider; with no
provider, claims render without a state.

Text that is not a registered claim is never assessed or marked.
"""

from __future__ import annotations

from ._contract import (
    GRAPH_NODE_KINDS,
    REPORT_SCHEMA,
    REPORT_SCHEMA_VERSION,
    ContractError,
    EvidenceError,
    load_report,
    schema_path,
    validate_report,
)
from ._packet import (
    PACKET_SCHEMA,
    PACKET_SCHEMA_VERSION,
    SCOPE,
    build_review_packet,
    find_claim,
    iter_entries,
    review_text,
)
from ._provider import (
    ProviderNotFound,
    available_providers,
    collect_report,
    find_provider,
)
from ._states import (
    INSPECTION_ORDER,
    LABELS,
    NO_EVIDENCE_GRAPH,
    NOT_CHECKABLE,
    NOT_SUPPORTED,
    STATES,
    SUPPORTED,
    SYMBOLS,
)

__all__ = [
    "GRAPH_NODE_KINDS",
    "INSPECTION_ORDER",
    "LABELS",
    "NOT_CHECKABLE",
    "NOT_SUPPORTED",
    "NO_EVIDENCE_GRAPH",
    "PACKET_SCHEMA",
    "PACKET_SCHEMA_VERSION",
    "REPORT_SCHEMA",
    "REPORT_SCHEMA_VERSION",
    "SCOPE",
    "STATES",
    "SUPPORTED",
    "SYMBOLS",
    "ContractError",
    "EvidenceError",
    "ProviderNotFound",
    "available_providers",
    "build_review_packet",
    "collect_report",
    "find_claim",
    "find_provider",
    "iter_entries",
    "load_report",
    "review_text",
    "schema_path",
    "validate_report",
]
