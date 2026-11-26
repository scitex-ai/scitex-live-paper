"""Optional reproduction receipt of a bundle: ``self-proof.json``.

A paper project's ``make self-proof`` re-derives every claim from a fresh
clone with a throwaway store and writes this receipt. live-paper reads it
through a small versioned contract and never imports the producer:

.. code-block:: json

   {"schema": "<producer>/self-proof/v1",
    "verdict": "PASS",
    "finished_at": "2026-11-26T03:04:05Z",
    "source": {"commit": "<sha>", "ref": "develop"},
    "claims": {"ok": 12, "committed": 12, "verified": 12},
    "failures": []}

Only these keys are read; anything else is ignored. The receipt is optional
decoration, so a missing file and a malformed one both yield ``None`` (the
malformed one with a logged warning); loading never raises.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import scitex_logging as slogging

__all__ = [
    "SELF_PROOF_FILENAME",
    "SELF_PROOF_SCHEMA_SUFFIX",
    "SelfProof",
    "load_self_proof",
    "parse_self_proof",
]

log = slogging.getLogger(__name__)

#: File name of the receipt inside a bundle directory.
SELF_PROOF_FILENAME = "self-proof.json"
#: Accepted ``schema`` suffix: any producer namespace, contract version v1.
SELF_PROOF_SCHEMA_SUFFIX = "/self-proof/v1"


def _parse_iso(value: str) -> _dt.datetime:
    # ``fromisoformat`` accepts a trailing "Z" only from Python 3.11.
    text = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = _dt.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.UTC)


@dataclass(frozen=True)
class SelfProof:
    """The contract keys of a ``self-proof.json`` receipt."""

    schema: str
    verdict: str  # "PASS" | "FAIL"
    finished_at: str  # ISO-8601, UTC
    commit: str
    ref: str | None
    ok: int
    committed: int
    verified: int
    failures: tuple[str, ...] = ()

    @property
    def date(self) -> str:
        """``YYYY-MM-DD`` (UTC) of :attr:`finished_at`."""
        moment = _parse_iso(self.finished_at).astimezone(_dt.UTC)
        return moment.date().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """The receipt as the review packet carries it (``packet["self_proof"]``)."""
        return {
            "schema": self.schema,
            "verdict": self.verdict,
            "finished_at": self.finished_at,
            "date": self.date,
            "source": {"commit": self.commit, "ref": self.ref},
            "claims": {
                "ok": self.ok,
                "committed": self.committed,
                "verified": self.verified,
            },
            "failures": list(self.failures),
        }


def _from_mapping(raw: Any) -> SelfProof:
    """Validate the contract keys of a parsed receipt; ``ValueError`` if wrong."""
    if not isinstance(raw, dict):
        raise ValueError("top level must be an object")
    schema = raw.get("schema")
    if not isinstance(schema, str) or not schema.endswith(SELF_PROOF_SCHEMA_SUFFIX):
        raise ValueError(
            f"unsupported schema {schema!r} (expected '*{SELF_PROOF_SCHEMA_SUFFIX}')"
        )
    verdict = raw.get("verdict")
    if verdict not in ("PASS", "FAIL"):
        raise ValueError(f"verdict must be 'PASS' or 'FAIL', got {verdict!r}")
    finished_at = raw.get("finished_at")
    if not isinstance(finished_at, str):
        raise ValueError("finished_at must be an ISO-8601 string")
    _parse_iso(finished_at)  # ValueError when not ISO-8601
    source = raw.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("commit"), str):
        raise ValueError("source.commit must be a string")
    if not source["commit"]:
        raise ValueError("source.commit must not be empty")
    ref = source.get("ref")
    if ref is not None and not isinstance(ref, str):
        raise ValueError("source.ref must be a string")
    claims = raw.get("claims")
    if not isinstance(claims, dict):
        raise ValueError("claims must be an object")
    counts = {}
    for key in ("ok", "committed", "verified"):
        value = claims.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"claims.{key} must be a non-negative integer")
        counts[key] = value
    failures = raw.get("failures", [])
    if not isinstance(failures, list) or not all(isinstance(f, str) for f in failures):
        raise ValueError("failures must be a list of strings")
    return SelfProof(
        schema=schema,
        verdict=verdict,
        finished_at=finished_at,
        commit=source["commit"],
        ref=ref,
        failures=tuple(failures),
        **counts,
    )


def parse_self_proof(
    text: str | bytes, *, origin: str = SELF_PROOF_FILENAME
) -> SelfProof | None:
    """Parse receipt *text*; malformed → ``None`` plus a logged warning."""
    try:
        return _from_mapping(json.loads(text))
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError included
        log.warning("ignoring %s: %s", origin, exc)
        return None


def load_self_proof(path: str | Path) -> SelfProof | None:
    """Read a receipt file; absent → ``None``, malformed → ``None`` + warning."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        text = path.read_bytes()
    except OSError as exc:
        log.warning("ignoring %s: %s", path, exc)
        return None
    return parse_self_proof(text, origin=str(path))
