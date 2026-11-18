"""Re-verify endpoints — single (``api/claim/verify``) + bulk (``api/claims/verify``).

Both ask an **evidence provider** for the current evidence state of
registered claims, through the provider-neutral contract in
:mod:`scitex_live_paper.evidence` (``docs/evidence-provider-contract.md``).
live-paper imports no provider: the provider is found through the ports
seam (:func:`~scitex_live_paper.evidence.find_provider`) and its answer is
collected and validated by :func:`~scitex_live_paper.evidence.collect_report`.

Configuration (environment, read per request):

- ``SCITEX_LIVE_PAPER_EVIDENCE_PROVIDER`` — the provider's entry-point
  name. Unset → the single installed provider.
- ``SCITEX_LIVE_PAPER_EVIDENCE_ROOT`` — the project the claims belong to.
  Unset → the bundle root.

The provider assesses the CURRENT on-disk state of that project.
``pinned_commit`` is METADATA only here: it is validated and echoed back as
``verified_against``, never passed to the provider. To re-verify against a
specific commit the host/deployment checks that commit out before serving.
These handlers never mutate the working tree.

With no provider installed the response degrades gracefully (``ok: false``,
``status: "unassessed"``, ``fallback: true``) rather than a 500, so the SPA
badge stays meaningful on a base install. The bulk endpoint uses the same
per-result envelope and collects ONE report for all target claims, so the
SPA's "Re-verify all" button gets every per-claim state from a single
provider call.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any, Dict, List, Optional, Tuple

import scitex_logging as slogging

try:
    from django.http import HttpResponse, JsonResponse
except ImportError as exc:
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[all]'"
    ) from exc

from ...evidence import LABELS, ProviderNotFound, collect_report, find_provider
from ..services import get_request_bundle_state

log = slogging.getLogger(__name__)

__all__ = [
    "ENV_EVIDENCE_PROVIDER",
    "ENV_EVIDENCE_ROOT",
    "UNASSESSED",
    "handle_reverify",
    "handle_reverify_all",
]

#: Entry-point name of the evidence provider to ask (else the only one).
ENV_EVIDENCE_PROVIDER = "SCITEX_LIVE_PAPER_EVIDENCE_PROVIDER"
#: Project root handed to the provider (else the bundle root).
ENV_EVIDENCE_ROOT = "SCITEX_LIVE_PAPER_EVIDENCE_ROOT"
#: Status of a claim no provider could assess.
UNASSESSED = "unassessed"
_NO_PROVIDER_REASON = "no evidence provider is installed"


def handle_reverify(request) -> HttpResponse:
    """Re-verify a single claim through the evidence provider.

    Request
    -------
    ``POST /api/claim/verify``
    Body (JSON)::

        {
            "claim_id":      "claim_a1b2c3d4e5f6",        # required
            "pinned_commit": "deadbeefcafef00d12345678"   # optional; defaults
                                                           # to bundle.paper_state.pinned_commit
        }

    Response
    --------
    On success::

        {
            "ok": true,
            "claim_id": "...",
            "verified_against": "<commit>",     # metadata echo
            "status": "supported" | "not_supported" | "not_checkable"
                      | "no_evidence_graph",
            "state":  <same as status>,
            "label":  "Supported by evidence" | ...,
            "reason": "<provider's reason>",
            "verified_at": null,
            "details": {...}                    # the claim's report entry
        }

    Claim absent from the provider's report → ``ok: false``,
    ``status: "not_found"``.

    No provider installed (or the configured one is not installed)::

        {"ok": false, "claim_id": "...", "status": "unassessed",
         "reason": "no evidence provider is installed", "fallback": true}

    Error cases:

    - Non-POST → 405 with ``{"error": "method not allowed"}``
    - Missing / non-mapping body → 400
    - Missing ``claim_id`` → 400
    - No pinned_commit anywhere (body + bundle.paper_state both empty) → 400
    - Provider raised, or its report breaks the contract → 500
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "method not allowed; POST a JSON body"},
            status=405,
        )

    body = _parse_json_body(request)
    if not isinstance(body, dict):
        return JsonResponse(
            {"error": "request body must be a JSON object"},
            status=400,
        )

    claim_id = body.get("claim_id")
    if not isinstance(claim_id, str) or not claim_id.strip():
        return JsonResponse(
            {"error": "'claim_id' is required and must be a non-empty string"},
            status=400,
        )

    bundle = get_request_bundle_state(request).bundle
    pinned_commit = _resolve_pinned_commit(body, bundle)
    if not pinned_commit:
        return _no_pinned_commit()

    try:
        entries = _collect_entries(bundle, [claim_id])
    except ProviderNotFound as exc:
        log.info("[re-verify] %s — claim %s left unassessed", exc, claim_id)
        return JsonResponse(_fallback(claim_id, exc))
    except Exception as exc:
        log.exception("[re-verify] evidence provider failed for %s", claim_id)
        return JsonResponse(
            {"ok": False, "claim_id": claim_id, "error": str(exc)},
            status=500,
        )

    return JsonResponse(_envelope(claim_id, pinned_commit, entries.get(claim_id)))


def _parse_json_body(request) -> Any:
    """Lenient JSON body parser. Returns ``None`` on empty / malformed."""
    if not request.body:
        return None
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _resolve_pinned_commit(body: Mapping[str, Any], bundle) -> str | None:
    """Body wins, then ``bundle.paper_state.pinned_commit``."""
    pinned_commit = body.get("pinned_commit")
    if not isinstance(pinned_commit, str) or not pinned_commit.strip():
        pinned_commit = bundle.paper_state.pinned_commit
    return pinned_commit or None


def _no_pinned_commit() -> HttpResponse:
    return JsonResponse(
        {
            "error": (
                "no pinned_commit available — pass one in the body or "
                "set bundle.paper_state.pinned_commit via state.yaml"
            )
        },
        status=400,
    )


def _collect_entries(bundle, claim_ids: Sequence[str]) -> dict[str, Mapping[str, Any]]:
    """One validated report for *claim_ids*, keyed by claim_id.

    Raises :class:`ProviderNotFound` when no (or not the configured)
    provider is installed; any provider or contract failure propagates.
    """
    name = os.environ.get(ENV_EVIDENCE_PROVIDER) or None
    _, adapter = find_provider(name)
    project_root = os.environ.get(ENV_EVIDENCE_ROOT) or str(bundle.root)
    report = collect_report(adapter, project_root, claim_ids=list(claim_ids))
    return {entry["claim_id"]: entry for entry in report["claims"]}


def _fallback(claim_id: str, exc: ProviderNotFound) -> dict[str, Any]:
    reason = str(exc) or _NO_PROVIDER_REASON
    return {
        "ok": False,
        "claim_id": claim_id,
        "status": UNASSESSED,
        "reason": reason,
        "fallback": True,
    }


def _envelope(
    claim_id: str,
    pinned_commit: str,
    entry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Shape one report entry (or its absence) into the SPA's envelope."""
    if entry is None:
        return {
            "ok": False,
            "claim_id": claim_id,
            "verified_against": pinned_commit,
            "status": "not_found",
            "reason": "the evidence provider reported no such registered claim",
            "verified_at": None,
            "details": None,
        }
    state = entry["state"]
    return {
        "ok": True,
        "claim_id": claim_id,
        "verified_against": pinned_commit,
        "status": state,
        "state": state,
        "label": LABELS[state],
        "reason": entry["reason"],
        "verified_at": None,
        "details": dict(entry),
    }


# ──────────────────────────────────────────────────────────────────
# Bulk: ``api/claims/verify``
# ──────────────────────────────────────────────────────────────────


def handle_reverify_all(request) -> HttpResponse:
    """Re-verify every claim in the bundle (or a subset) in ONE provider call.

    Request
    -------
    ``POST /api/claims/verify``
    Body (JSON; all keys optional)::

        {
            "claim_ids":     ["claim_a", "claim_b", ...]   # filter; omit = all
            "pinned_commit": "<sha>"                       # override for all
        }

    Response
    --------
    ::

        {
            "ok": true | false,
            "verified_against": "<sha>",
            "count": <int>,                  # number of results below
            "results": [
                { ...same envelope as api/claim/verify... },
                ...
            ]
        }

    Top-level ``ok`` is True iff EVERY per-claim result succeeded. One
    fallback, not-found, or error result flips it to False so the SPA can
    flag the overall sweep as incomplete.

    Errors:

    - Non-POST → 405
    - Body present but not a JSON object → 400
    - ``claim_ids`` present but not a list of strings → 400
    - No pinned_commit anywhere → 400
    - No claims to verify (bundle has none and no filter given) → 400

    Provider failures (raise / contract violation) and unknown claim ids
    are folded into the per-result envelopes with ``ok=false`` — they do
    NOT 500 the bulk call.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "method not allowed; POST a JSON body"},
            status=405,
        )

    body = _parse_json_body(request)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return JsonResponse(
            {"error": "request body must be a JSON object"},
            status=400,
        )

    claim_ids_raw = body.get("claim_ids")
    claim_ids_filter: list[str] | None
    if claim_ids_raw is None:
        claim_ids_filter = None
    elif isinstance(claim_ids_raw, list) and all(
        isinstance(x, str) and x.strip() for x in claim_ids_raw
    ):
        claim_ids_filter = list(claim_ids_raw)
    else:
        return JsonResponse(
            {"error": "'claim_ids' must be a list of non-empty strings"},
            status=400,
        )

    bundle = get_request_bundle_state(request).bundle
    pinned_commit = _resolve_pinned_commit(body, bundle)
    if not pinned_commit:
        return _no_pinned_commit()

    target_ids, missing = _split_targets(
        [c.claim_id for c in bundle.claims], claim_ids_filter
    )
    if not target_ids and not claim_ids_filter:
        return JsonResponse(
            {"error": "bundle has no claims to verify"},
            status=400,
        )

    # Unknown ids are reported per-result rather than failing the call, so
    # the SPA can show them without losing the other results.
    results: list[Mapping[str, Any]] = [
        {
            "ok": False,
            "claim_id": missing_id,
            "status": "unknown",
            "reason": "claim_id not found in bundle",
        }
        for missing_id in missing
    ]
    if target_ids:
        results.extend(_bulk_results(bundle, target_ids, pinned_commit))

    return JsonResponse(
        {
            "ok": all(r.get("ok", False) for r in results),
            "verified_against": pinned_commit,
            "count": len(results),
            "results": results,
        }
    )


def _split_targets(
    bundle_ids: list[str], claim_ids_filter: list[str] | None
) -> tuple[list[str], list[str]]:
    """``(ids to verify, requested ids absent from the bundle)``."""
    if claim_ids_filter is None:
        return bundle_ids, []
    known = set(bundle_ids)
    return (
        [cid for cid in claim_ids_filter if cid in known],
        [cid for cid in claim_ids_filter if cid not in known],
    )


def _bulk_results(
    bundle, target_ids: list[str], pinned_commit: str
) -> list[Mapping[str, Any]]:
    """Per-claim envelopes from ONE report covering every target id."""
    try:
        entries = _collect_entries(bundle, target_ids)
    except ProviderNotFound as exc:
        log.info(
            "[re-verify-all] %s — %d claim(s) left unassessed", exc, len(target_ids)
        )
        return [_fallback(cid, exc) for cid in target_ids]
    except Exception as exc:
        log.exception("[re-verify-all] evidence provider failed")
        return [{"ok": False, "claim_id": cid, "error": str(exc)} for cid in target_ids]
    return [_envelope(cid, pinned_commit, entries.get(cid)) for cid in target_ids]
