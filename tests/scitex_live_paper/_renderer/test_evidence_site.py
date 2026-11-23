"""Evidence pages of the site agree with the review packet (no mocks).

Rendered from a REAL provider's report (``_reference_provider``): the paper
marks, the claims page (needs-inspection first), the per-claim graph pages
and ``review.txt`` must all say what ``review.json`` says. Untagged text is
never marked; with no provider nothing is marked.
"""

from __future__ import annotations

import json
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from scitex_live_paper._cli.render import render_site
from scitex_live_paper.evidence import iter_entries

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidence"))
from _reference_provider import (  # noqa: F401
    EXPECTED_STATES,
    UNTAGGED_TEXT,
    ref_bundle,
    ref_installed_provider,
    ref_project,
    ref_report,
    ref_report_file,
    ref_site,
)


class _Marks(HTMLParser):
    """Collect (claim id, state, title) of elements with a given tag + class."""

    def __init__(self, tag: str, cls: str):
        super().__init__()
        self.tag, self.cls, self.found = tag, cls, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == self.tag and self.cls in (a.get("class") or "").split():
            self.found.append(
                (a.get("data-claim-id"), a.get("data-support"), a.get("title"))
            )


class _FailingItems(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and "lp-failing-node" in (a.get("class") or "").split():
            self.found.append((a.get("data-failure"), a.get("data-node-id")))


def _failing_items(html: str) -> list:
    parser = _FailingItems()
    parser.feed(html)
    return parser.found


def _marks(html: str, tag: str, cls: str) -> list:
    parser = _Marks(tag, cls)
    parser.feed(html)
    return parser.found


def test_render_with_installed_provider_marks_every_registered_claim(
    tmp_path, ref_bundle, ref_project, ref_installed_provider
):
    # Arrange
    out = tmp_path / "out"
    # Act
    result = render_site(
        ref_bundle,
        out,
        evidence_provider=ref_installed_provider,
        evidence_root=ref_project,
    )
    # Assert
    marks = _marks(result.paper_html.read_text(), "mark", "lp-claim-span")
    assert {cid: st for cid, st, _ in marks} == EXPECTED_STATES


def test_untagged_text_is_never_marked(ref_site):
    # Arrange
    _out, result, _packet = ref_site
    # Act
    line = next(
        l for l in result.paper_html.read_text().splitlines() if "42 degrees" in l
    )
    # Assert
    assert ("<mark" not in line, UNTAGGED_TEXT in line) == (True, True)


def test_claims_page_shows_needs_inspection_before_supported(ref_site):
    # Arrange
    out, _result, _packet = ref_site
    # Act
    html = (out / "claims.html").read_text()
    # Assert
    assert html.index("Needs inspection (4)") < html.index("Supported by evidence (1)")


def test_paper_marks_agree_with_the_packet(ref_site):
    # Arrange
    _out, result, packet = ref_site
    expected = {
        e["claim_id"]: (e["state"], f"{e['label']}: {e['reason']}")
        for e in iter_entries(packet)
    }
    # Act
    marks = _marks(result.paper_html.read_text(), "mark", "lp-claim-span")
    # Assert
    assert {cid: (st, title) for cid, st, title in marks} == expected


def test_claims_page_list_agrees_with_the_packet_in_order(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    listed = _marks((out / "claims.html").read_text(), "li", "lp-inspection-item")
    # Assert
    assert [(cid, st) for cid, st, _ in listed] == [
        (e["claim_id"], e["state"]) for e in iter_entries(packet)
    ]


def test_claims_page_shows_every_reason(ref_site):
    # Arrange
    out, _result, packet = ref_site
    html = (out / "claims.html").read_text()
    # Act
    missing = [e["reason"] for e in iter_entries(packet) if e["reason"] not in html]
    # Assert
    assert missing == []


def test_graph_pages_agree_with_the_packet(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    pages = [
        _marks((out / e["graph_url"]).read_text(), "section", "lp-claim-evidence")[0][
            :2
        ]
        for e in iter_entries(packet)
    ]
    # Assert
    assert pages == [(e["claim_id"], e["state"]) for e in iter_entries(packet)]


def test_graph_page_draws_the_providers_nodes(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    html = (out / packet["supported"][0]["graph_url"]).read_text()
    # Assert
    # Browser textContent decodes HTML entities before Mermaid reads its source.
    assert '<br/>scripts/compute.py' in unescape(html)


def test_graph_page_lists_exactly_the_packets_failing_nodes(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    listed = {
        e["claim_id"]: _failing_items((out / e["graph_url"]).read_text())
        for e in iter_entries(packet)
    }
    # Assert
    assert listed == {
        e["claim_id"]: [(f["failure"], f["id"]) for f in e["failing_nodes"]]
        for e in iter_entries(packet)
    }


def test_graph_page_draws_failing_nodes_with_class_and_text_label(ref_site):
    # Arrange
    out, _result, packet = ref_site
    entry = next(e for e in packet["needs_inspection"] if e["claim_id"] == "cohort2")
    # Act
    html = (out / entry["graph_url"]).read_text()
    # Assert
    assert (
        '<br/>data/input2.csv<br/>⚠ CHANGED"/]:::failing' in unescape(html)
        and "classDef failing" in html
        and "stroke-dasharray:12 4 3 4" in html
    )


def test_graph_page_of_a_supported_claim_marks_no_node_failing(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    html = (out / packet["supported"][0]["graph_url"]).read_text()
    # Assert
    assert (":::failing" not in html, "lp-failing-node" not in html) == (True, True)


def test_review_json_carries_failing_nodes(ref_site):
    # Arrange
    out, _result, packet = ref_site
    # Act
    on_disk = json.loads((out / "review.json").read_text())
    # Assert
    assert [e["failing_nodes"] for e in iter_entries(on_disk)] == [
        e["failing_nodes"] for e in iter_entries(packet)
    ]


def test_review_text_file_agrees_with_the_packet(ref_site):
    # Arrange
    out, _result, packet = ref_site
    text = (out / "review.txt").read_text()
    # Act
    missing = [
        e["claim_id"]
        for e in iter_entries(packet)
        if f"{e['label']}: {e['claim_id']}" not in text or e["reason"] not in text
    ]
    # Assert
    assert missing == []


def test_no_provider_renders_claims_without_states(tmp_path, ref_bundle):
    # Arrange
    out = tmp_path / "plain"
    # Act
    result = render_site(ref_bundle, out)
    # Assert
    assert (
        result.review_json,
        result.paper_html,
        "data-support" in (out / "claims.html").read_text(),
    ) == (None, None, False)
