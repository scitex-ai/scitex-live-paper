"""Find an evidence provider and collect a validated report from it.

Providers arrive through the ports seam: an entry point in the
``scitex.livepaper.renderers`` group whose object has ``port = "evidence"``
(see :mod:`scitex_live_paper.ports`). live-paper imports no provider.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from ..ports import discover
from ..ports.protocols import EVIDENCE_PORT
from ._contract import ContractError, EvidenceError, validate_report

__all__ = ["ProviderNotFound", "available_providers", "collect_report", "find_provider"]


class ProviderNotFound(EvidenceError, LookupError):
    """No installed evidence provider matches the request."""


def available_providers() -> dict[str, Any]:
    """``{name: adapter}`` of every installed evidence provider."""
    return {
        name: adapter for port, name, adapter in discover() if port == EVIDENCE_PORT
    }


def find_provider(name: str | None = None) -> tuple[str, Any]:
    """The installed provider called *name*, or the only one when *name* is None."""
    found = available_providers()
    if name is not None:
        if name not in found:
            raise ProviderNotFound(
                f"no evidence provider named {name!r}; installed: {sorted(found) or 'none'}"
            )
        return name, found[name]
    if len(found) == 1:
        return next(iter(found.items()))
    if not found:
        raise ProviderNotFound("no evidence provider is installed")
    raise ProviderNotFound(
        f"several evidence providers are installed ({sorted(found)}); name one"
    )


def collect_report(
    adapter: Any,
    project_root: str,
    *,
    claim_ids: Sequence[str] | None = None,
    options: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Ask *adapter* for a report and fill omitted graphs on demand.

    A claim whose entry omits the ``graph`` key gets it from the provider's
    optional ``evidence_graph``; a provider without that method leaves it
    ``null`` with a ``graph_error`` saying so. The result is validated.
    """
    opts = dict(options or {})
    report = adapter.evidence_report(
        project_root, list(claim_ids) if claim_ids else None, opts
    )
    report = copy.deepcopy(dict(validate_report(report)))
    graph_fn = getattr(adapter, "evidence_graph", None)
    for claim in report["claims"]:
        if "graph" in claim:
            continue
        if callable(graph_fn):
            try:
                claim["graph"] = graph_fn(project_root, claim["claim_id"], opts)
            except Exception as exc:  # noqa: BLE001 — surfaced per claim, not swallowed
                claim["graph"] = None
                claim["graph_error"] = f"provider could not build the graph: {exc}"
        else:
            claim["graph"] = None
            claim["graph_error"] = "the provider supplies no graph for this claim"
    try:
        return validate_report(report)
    except ContractError as exc:
        raise ContractError(f"provider graph output: {exc}") from exc
