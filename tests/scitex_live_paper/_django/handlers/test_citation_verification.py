import json
from types import SimpleNamespace

from scitex_live_paper._django.handlers._citation_verification import read_citation_verification
from scitex_live_paper._renderer.dag import graph_to_mermaid
from scitex_live_paper.evidence.citations import CITATION_REPORT, citation_verification


def test_citation_verdicts_are_bound_to_the_pdf(tmp_path):
    pdf = tmp_path / "manuscript.pdf"
    pdf.write_bytes(b"first manuscript")
    bundle = SimpleNamespace(root=tmp_path, manuscript_path=pdf)
    states = {state: {"status": state} for state in ("verified", "stub", "unverified", "unknown")}
    report = citation_verification(pdf, {**states, "invalid": {"status": "guessed"}})
    path = tmp_path / CITATION_REPORT
    path.write_text(json.dumps(report))
    assert read_citation_verification(bundle) == states

    pdf.write_bytes(b"recompiled manuscript")
    assert read_citation_verification(bundle) == {}

    pdf.write_bytes(b"first manuscript")
    outside = tmp_path / "aliased.json"
    path.rename(outside)
    path.symlink_to(outside)
    assert read_citation_verification(bundle) == {}


def test_author_interpretation_is_an_explicit_incoming_edge():
    graph = {
        "nodes": [
            {"id": "raw", "label": "data.csv", "kind": "input", "author_registered": True},
            {"id": "result", "label": "result.json", "kind": "output"},
            {"id": "verified", "label": "The recorded value is above 0.5", "kind": "claim"},
            {"id": "interpreted", "label": "The method is reliable", "kind": "claim"},
        ],
        "edges": [
            {"source": "result", "target": "verified"},
            {"source": "result", "target": "interpreted", "relation": "author_interpretation"},
        ],
    }
    source, _ = graph_to_mermaid(graph, state="supported")
    assert "n1 --> n2" in source
    assert "n1 -->|Author interpretation| n3" in source
    assert 'n0["Input · ✒ Author-registered source<br/>data.csv"]:::author_source' in source
    assert 'n2["Claim<br/>The recorded value is above 0.5"]:::supported' in source
    assert 'n3["Claim · ✒ Author interpretation<br/>The method is reliable"]:::supported' in source
