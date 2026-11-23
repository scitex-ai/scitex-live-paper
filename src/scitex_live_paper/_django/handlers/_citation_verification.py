"""Load PDF-bound citation evidence from the request's authorized bundle."""

import json

from scitex_live_paper.evidence.citations import (
    CITATION_REPORT,
    CITATION_SCHEMA,
    citation_entries,
    stream_sha256,
)

from .._evidence_files import ResourceError, ResourceReader


def read_citation_verification(bundle):
    pdf = bundle.manuscript_path
    if pdf.suffix.lower() != ".pdf":
        return {}
    try:
        with ResourceReader(bundle.root) as reader:
            report = json.loads(reader.read(CITATION_REPORT, limit=1_048_576))
            if not isinstance(report, dict) or report.get("schema") != CITATION_SCHEMA:
                return {}
            with reader.open_regular_file(pdf) as stream:
                if stream_sha256(stream) != report.get("pdf_sha256"):
                    return {}
    except (ResourceError, OSError, ValueError):
        return {}
    return citation_entries(report.get("citations"))
