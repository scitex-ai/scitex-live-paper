"""The paper page carries everything its claim navigation needs (no browser).

Rendered from a REAL provider's report (``_reference_provider``). The
embedded claims data must be the review packet's entries in its order, with
the same mermaid source the graph pages draw; the navigator lists needs
inspection first; the panel and its assets ship with the static site; the
marks still link to the graph pages so the page works without JavaScript.
The browser behaviour is checked in ``test_paper_navigation_browser.py``.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from scitex_live_paper._renderer.dag import graph_to_mermaid
from scitex_live_paper._renderer.paper import claims_data
from scitex_live_paper.evidence import iter_entries

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidence"))
from _reference_provider import (  # noqa: F401
    ref_bundle,
    ref_project,
    ref_report,
    ref_report_file,
    ref_site,
)


class _Attrs(HTMLParser):
    """Attributes of every start tag matching *tag* + *cls*."""

    def __init__(self, tag: str, cls: str | None = None):
        super().__init__()
        self.tag, self.cls, self.found = tag, cls, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == self.tag and (
            self.cls is None or self.cls in (a.get("class") or "").split()
        ):
            self.found.append(a)


def _attrs(html: str, tag: str, cls: str | None = None) -> list[dict]:
    parser = _Attrs(tag, cls)
    parser.feed(html)
    return parser.found


def _embedded(html: str) -> list:
    m = re.search(
        r'<script id="lp-claims-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    return json.loads(m.group(1))


def test_embedded_claims_are_the_packet_entries_in_packet_order(ref_site):
    # Arrange
    _out, result, packet = ref_site
    # Act
    data = _embedded(result.paper_html.read_text())
    # Assert
    assert [(c["claim_id"], c["state"], c["reason"]) for c in data] == [
        (e["claim_id"], e["state"], e["reason"]) for e in iter_entries(packet)
    ]


def test_embedded_graph_is_the_graph_pages_mermaid_source(ref_site):
    # Arrange
    _out, result, packet = ref_site
    expected = {
        e["claim_id"]: (
            graph_to_mermaid(e["graph"], state=e["state"])[0] if e["graph"] else None
        )
        for e in iter_entries(packet)
    }
    # Act
    data = _embedded(result.paper_html.read_text())
    # Assert
    assert {c["claim_id"]: c["mermaid"] for c in data} == expected


def test_embedded_failing_nodes_match_the_packet(ref_site):
    # Arrange
    _out, result, packet = ref_site
    # Act
    data = _embedded(result.paper_html.read_text())
    # Assert
    assert {c["claim_id"]: c["failing_nodes"] for c in data} == {
        e["claim_id"]: e["failing_nodes"] for e in iter_entries(packet)
    }


def test_claims_data_adds_only_the_mermaid_source_and_value_display(ref_site):
    # Arrange
    _out, _result, packet = ref_site
    added = {"mermaid", "stated_display", "value_check"}
    # Act
    data = claims_data(packet)
    # Assert: every packet value is passed through unchanged
    assert all(
        {k: v for k, v in c.items() if k not in added}.items() <= dict(e).items()
        and added <= set(c)
        for c, e in zip(data, iter_entries(packet))
    )


def test_navigator_lists_needs_inspection_first_with_claim_links(ref_site):
    # Arrange
    _out, result, packet = ref_site
    # Act
    items = _attrs(result.paper_html.read_text(), "a", "lp-claim-nav-item")
    # Assert
    assert [(a["data-claim-id"], a["href"]) for a in items] == [
        (e["claim_id"], f"#claim-{e['claim_id']}") for e in iter_entries(packet)
    ]


def test_marks_open_the_panel_and_still_link_to_the_graph_page(ref_site):
    # Arrange
    _out, result, packet = ref_site
    urls = {e["claim_id"]: e["graph_url"] for e in iter_entries(packet)}
    html = result.paper_html.read_text()
    # Act
    links = re.findall(
        r'<mark class="lp-claim-span" id="claim-([^"]+)"[^>]*><a href="([^"]+)" '
        r'aria-haspopup="dialog" aria-controls="lp-claim-panel">',
        html,
    )
    # Assert
    assert dict(links) == urls


def test_panel_is_an_accessible_non_modal_dialog(ref_site):
    # Arrange
    _out, result, _packet = ref_site
    # Act
    (panel,) = _attrs(result.paper_html.read_text(), "aside", "lp-claim-panel")
    # Assert
    assert (
        panel["role"],
        panel["aria-modal"],
        panel["aria-labelledby"],
        "hidden" in panel,
    ) == ("dialog", "false", "lp-claim-panel-title", True)


def test_paper_page_ships_its_scripts_as_classic_scripts(ref_site):
    # Arrange
    out, result, _packet = ref_site
    html = result.paper_html.read_text()
    # Act
    scripts = [a for a in _attrs(html, "script") if a.get("src") and "type" not in a]
    # Assert
    assert (
        [(a["src"], a.get("type")) for a in scripts],
        all((out / a["src"]).is_file() for a in scripts),
        (out / "assets" / "paper.css").is_file(),
    ) == (
        [
            ("assets/mermaid/mermaid.min.js", None),
            ("assets/paper-panel.js", None),
            ("assets/paper.js", None),
        ],
        True,
        True,
    )


def test_packet_carries_the_source_value_the_provider_read(ref_site):
    # Arrange
    _out, _result, packet = ref_site
    # Act
    by_id = {e["claim_id"]: e["source"] for e in iter_entries(packet)}
    # Assert
    assert (
        (by_id["n_rows"]["value"], by_id["n_rows"]["value_reported"]),
        (by_id["accuracy"]["value"], by_id["accuracy"]["value_reported"]),
    ) == ((2, True), (None, False))


def test_graph_page_shows_stated_and_source_value(ref_site):
    # Arrange
    out, _result, packet = ref_site
    entry = next(e for e in iter_entries(packet) if e["claim_id"] == "n_rows")
    # Act
    html = (out / entry["graph_url"]).read_text()
    # Assert
    assert "Stated value <code>3</code> · source value <code>2</code>" in html


def test_review_text_prints_stated_and_source_value(ref_site):
    # Arrange
    out, _result, _packet = ref_site
    # Act
    text = (out / "review.txt").read_text()
    # Assert
    assert "stated value: 3  source value: 2" in text
