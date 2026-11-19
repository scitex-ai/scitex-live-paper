"""The evidence-report contract: ids, versions, and a stdlib validator.

The authoritative shape is ``evidence-report.schema.json`` (shipped beside
this module); :func:`validate_report` enforces the same rules without a
JSON-Schema dependency, and the test suite checks the two agree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._states import STATES

__all__ = [
    "FAILURE_KIND_PATTERN",
    "GRAPH_NODE_KINDS",
    "REPORT_SCHEMA",
    "REPORT_SCHEMA_VERSION",
    "ContractError",
    "EvidenceError",
    "load_report",
    "schema_path",
    "validate_report",
]

REPORT_SCHEMA = "scitex-live-paper.evidence-report"
#: The contract version this release implements. Any ``1.x.y`` report is
#: accepted (minor bumps only add optional fields).
REPORT_SCHEMA_VERSION = "1.2.0"
GRAPH_NODE_KINDS = frozenset({"claim", "process", "input", "output", "other"})
#: A node's ``failure.kind`` (1.1.0) is a short lowercase token. Any token is
#: accepted so a later 1.x can name new kinds; unknown ones render verbatim.
FAILURE_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class EvidenceError(Exception):
    """Base of every evidence-contract failure (bad report, missing provider)."""


class ContractError(EvidenceError, ValueError):
    """An evidence report does not conform to the contract."""


def schema_path() -> Path:
    """Path of the shipped JSON Schema for the evidence report."""
    return Path(__file__).resolve().parent / "evidence-report.schema.json"


def _fail(where: str, msg: str) -> None:
    raise ContractError(f"evidence report {where}: {msg}")


def _check_failure(failure: Any, where: str, node_id: Any) -> None:
    if failure is None:
        return
    if not isinstance(failure, Mapping):
        _fail(where, f"node {node_id!r}: failure must be an object or null")
    kind = failure.get("kind")
    if not isinstance(kind, str) or not FAILURE_KIND_PATTERN.match(kind):
        _fail(
            where,
            f"node {node_id!r}: failure.kind must be a short lowercase token, "
            f"got {kind!r}",
        )
    detail = failure.get("detail")
    if detail is not None and not isinstance(detail, str):
        _fail(where, f"node {node_id!r}: failure.detail must be a string or null")


def _check_graph(graph: Any, where: str) -> None:
    if not isinstance(graph, Mapping):
        _fail(where, "graph must be an object or null")
    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        _fail(where, "graph needs 'nodes' and 'edges' lists")
    ids = set()
    for n in nodes:
        if not isinstance(n, Mapping) or not all(
            k in n for k in ("id", "kind", "label")
        ):
            _fail(where, "each graph node needs id, kind, label")
        if n["kind"] not in GRAPH_NODE_KINDS:
            _fail(where, f"unknown node kind {n['kind']!r}")
        _check_failure(n.get("failure"), where, n["id"])
        ids.add(n["id"])
    for e in edges:
        if not isinstance(e, Mapping) or "source" not in e or "target" not in e:
            _fail(where, "each graph edge needs source and target")
        if e["source"] not in ids or e["target"] not in ids:
            _fail(
                where, f"edge {e['source']!r} -> {e['target']!r} names an unknown node"
            )


def validate_report(report: Any) -> Mapping[str, Any]:
    """Return *report* if it conforms to contract v1; raise :class:`ContractError`."""
    if not isinstance(report, Mapping):
        _fail("", "must be a JSON object")
    if report.get("schema") != REPORT_SCHEMA:
        _fail("", f"schema must be {REPORT_SCHEMA!r}, got {report.get('schema')!r}")
    version = str(report.get("schema_version", ""))
    if version.split(".")[0] != REPORT_SCHEMA_VERSION.split(".")[0]:
        _fail("", f"schema_version {version!r} is not a 1.x contract")
    provider = report.get("provider")
    if not isinstance(provider, Mapping) or not provider.get("name"):
        _fail("", "provider.name is required")
    claims = report.get("claims")
    if not isinstance(claims, list):
        _fail("", "claims must be a list")
    seen = set()
    for i, c in enumerate(claims):
        where = f"claims[{i}]"
        if not isinstance(c, Mapping):
            _fail(where, "must be an object")
        for key in ("claim_id", "location", "state", "reason"):
            if key not in c:
                _fail(where, f"missing required {key!r}")
        if c["claim_id"] in seen:
            _fail(where, f"duplicate claim_id {c['claim_id']!r}")
        seen.add(c["claim_id"])
        if c["state"] not in STATES:
            _fail(
                where,
                f"unknown state {c['state']!r} (expected one of {sorted(STATES)})",
            )
        if not isinstance(c["reason"], str) or not c["reason"]:
            _fail(where, "reason must be a non-empty string")
        if not isinstance(c["location"], Mapping):
            _fail(where, "location must be an object")
        line = c["location"].get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            _fail(where, "location.line must be a positive integer or null")
        if c.get("graph") is not None:
            _check_graph(c["graph"], where)
    return report


def load_report(path: str | Path) -> Mapping[str, Any]:
    """Read and validate an evidence-report JSON file a provider produced."""
    p = Path(path).expanduser()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read evidence report {p}: {exc}") from exc
    return validate_report(data)
