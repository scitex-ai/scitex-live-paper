"""Portable Clew citation verdicts bound to the PDF they describe."""

from hashlib import sha256
from pathlib import Path

CITATION_REPORT = "citation-verification.json"
CITATION_SCHEMA = "scitex-live-paper/citation-verification/v1"
CITATION_STATES = frozenset({"verified", "stub", "unverified", "unknown"})
DETAIL_FIELDS = ("doi", "source_id", "link", "reason", "resolver_source", "provenance", "claim_id")


def citation_verification(pdf: Path, citations: dict) -> dict:
    """Bind the per-key output of Clew verification to a compiled PDF.

    Entries can also carry the matching Scholar provider, provenance, and
    an evidence claim ID. These fields are supplied by the tracing workflow.
    """
    with Path(pdf).open("rb") as stream:
        digest = stream_sha256(stream)
    return {
        "schema": CITATION_SCHEMA,
        "pdf_sha256": digest,
        "citations": citation_entries(citations),
    }


def citation_entries(entries: object) -> dict:
    if not isinstance(entries, dict):
        return {}
    return {
        key: {
            "status": entry["status"],
            **{field: entry[field] for field in DETAIL_FIELDS
               if isinstance(entry.get(field), str) and entry[field]},
        }
        for key, entry in entries.items()
        if isinstance(key, str) and key and isinstance(entry, dict)
        and isinstance(entry.get("status"), str) and entry["status"] in CITATION_STATES
    }


def stream_sha256(stream):
    digest = sha256()
    for chunk in iter(lambda: stream.read(131_072), b""):
        digest.update(chunk)
    return digest.hexdigest()
