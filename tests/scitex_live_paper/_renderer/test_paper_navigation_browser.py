"""The paper page's claim navigation, driven in a real browser (no mocks).

The site is rendered from a REAL provider's report (``_reference_provider``)
and opened straight from disk (``file://``), the way a static export is
read. Checks: a mark opens the evidence panel in place with the inline
minimal graph; a not-supported claim shows its broken node; graph nodes
show their details; Esc closes and restores focus; the navigator scrolls to
and highlights a claim; ``#claim-<id>`` deep links; back/forward; a
keyboard-only walk.

Skips cleanly when Playwright or a Chromium build is not available. Set
``LP_SCREENSHOT_DIR`` to also save screenshots of the flows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

#: Set in the CI browser leg: a missing Playwright/Chromium FAILS instead of
#: skipping, so that leg cannot pass by not running.
REQUIRE_BROWSER = os.environ.get("LP_REQUIRE_BROWSER") == "1"

if REQUIRE_BROWSER:
    from playwright import sync_api
else:
    sync_api = pytest.importorskip("playwright.sync_api")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidence"))
from _reference_provider import (  # noqa: F401
    EXPECTED_STATES,
    UNTAGGED_TEXT,
    ref_bundle,
    ref_project,
    ref_report,
    ref_report_file,
    ref_site,
)

SHOTS = os.environ.get("LP_SCREENSHOT_DIR")


@pytest.fixture(scope="module")
def browser():
    pw = sync_api.sync_playwright().start()
    try:
        try:
            b = pw.chromium.launch()
        except Exception as exc:  # no browser build installed
            reason = f"no Chromium for Playwright: {str(exc).splitlines()[0]}"
            if REQUIRE_BROWSER:
                pytest.fail(reason)
            pytest.skip(reason)
        yield b
        b.close()
    finally:
        pw.stop()


@pytest.fixture
def page(browser, ref_site):
    out, _result, _packet = ref_site
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.lp_url = (out / "paper.html").as_uri()
    pg.lp_errors = errors
    yield pg
    ctx.close()
    assert errors == [], f"page errors: {errors}"


def _load(pg, fragment: str = "") -> None:
    pg.goto(pg.lp_url + fragment)
    pg.wait_for_selector("html[data-lp-paper-ready]", state="attached")


def _panel(pg):
    return pg.locator("#lp-claim-panel")


def _graph_drawn(pg) -> None:
    pg.wait_for_selector("#lp-claim-panel .lp-claim-graph[data-lp-rendered] svg")


def _shot(pg, name: str) -> None:
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(SHOTS) / f"{name}.png"), full_page=False)


def test_clicking_a_supported_claim_opens_its_panel_with_the_graph(page):
    # Arrange
    _load(page)
    # Act
    page.click("mark#claim-auc a")
    _graph_drawn(page)
    _shot(page, "popover-supported")
    # Assert
    panel = _panel(page)
    assert (
        panel.get_attribute("data-support"),
        "Supported by evidence" in panel.text_content(),
        page.locator("#lp-claim-panel g.node[data-lp-node-kind]").count(),
        page.locator("#lp-claim-panel g.node[data-lp-failure]").count(),
        page.url.endswith("#claim-auc"),
    ) == ("supported", True, 4, 0, True)


def test_not_supported_claim_shows_the_broken_node_in_the_graph(page):
    # Arrange
    _load(page)
    # Act
    page.click("mark#claim-cohort2 a")
    _graph_drawn(page)
    _shot(page, "popover-not-supported-broken-node")
    # Assert
    broken = page.locator("#lp-claim-panel g.node[data-lp-failure]")
    assert (
        _panel(page).get_attribute("data-support"),
        broken.count(),
        broken.first.get_attribute("data-lp-failure"),
        "⚠ CHANGED" in broken.first.text_content(),
        "Where the evidence broke (1 node" in _panel(page).text_content(),
    ) == ("not_supported", 1, "changed", True, True)


def test_panel_shows_stated_vs_source_value(page):
    # Arrange
    _load(page)
    # Act
    page.click("mark#claim-n_rows a")
    text = _panel(page).locator(".lp-claim-values").inner_text()
    # Assert
    assert ("3" in text, "2" in text, "differs from the stated value" in text) == (
        True,
        True,
        True,
    )


def test_clicking_a_graph_node_shows_file_hash_run_and_failure(page):
    # Arrange
    _load(page)
    page.click("mark#claim-cohort2 a")
    _graph_drawn(page)
    # Act
    page.click("#lp-claim-panel g.node[data-lp-failure]")
    details = page.locator("#lp-claim-panel .lp-node-details").inner_text()
    _shot(page, "popover-node-details")
    # Assert
    assert (
        "data/input2.csv" in details,
        "Hash" in details,
        "Read by run" in details and "scripts/compute.py" in details,
        "hash differs from the recorded run" in details,
    ) == (True, True, True, True)


def test_escape_closes_the_panel_and_returns_focus_to_the_claim(page):
    # Arrange
    _load(page)
    page.click("mark#claim-auc a")
    # Act
    page.keyboard.press("Escape")
    # Assert
    assert (
        _panel(page).is_hidden(),
        page.evaluate("document.activeElement.closest('mark')?.id"),
        "#claim-" in page.url,
    ) == (True, "claim-auc", False)


def test_navigator_lists_needs_inspection_first_and_opens_the_claim(page):
    # Arrange
    _load(page)
    order = page.eval_on_selector_all(
        ".lp-claim-nav-item", "els => els.map(e => e.dataset.support)"
    )
    # Act
    page.click(".lp-claim-nav-item[data-claim-id='calib']")
    _shot(page, "navigator")
    # Assert
    assert (
        order.index("supported") == len(order) - 1,
        page.get_attribute("mark#claim-calib", "data-lp-active"),
        page.get_attribute(".lp-claim-nav-item[data-claim-id='calib']", "aria-current"),
        _panel(page).get_attribute("data-claim-id"),
    ) == (True, "", "true", "calib")


def test_deep_link_opens_the_panel_on_load(page):
    # Arrange
    fragment = "#claim-cohort2"
    # Act
    _load(page, fragment)
    # Assert
    assert (_panel(page).is_visible(), _panel(page).get_attribute("data-claim-id")) == (
        True,
        "cohort2",
    )


def test_back_and_forward_step_through_the_claims_opened(page):
    # Arrange
    _load(page)
    page.click("mark#claim-auc a")
    page.click("#lp-claim-panel .lp-next-inspection")
    first_next = _panel(page).get_attribute("data-claim-id")
    # Act
    page.go_back()
    after_back = _panel(page).get_attribute("data-claim-id")
    page.go_back()
    closed = _panel(page).is_hidden()
    page.go_forward()
    # Assert
    assert (
        first_next,
        after_back,
        closed,
        _panel(page).get_attribute("data-claim-id"),
    ) == (
        "n_rows",
        "auc",
        True,
        "auc",
    )


def test_untagged_text_is_not_interactive(page):
    # Arrange
    _load(page)
    # Act
    line = page.locator(".lp-paper-line", has_text="42 degrees")
    # Assert
    assert (line.locator("mark, a").count(), UNTAGGED_TEXT in line.inner_text()) == (
        0,
        True,
    )


def test_keyboard_only_walk_through_the_claims(page):
    # Arrange
    _load(page)
    page.focus("mark#claim-auc a")
    # Act: open with Enter, jump to the next claim needing inspection, open
    # the source node's details, then close with Esc — keyboard only.
    page.keyboard.press("Enter")
    opened = page.evaluate("document.activeElement.id")
    page.locator("#lp-claim-panel .lp-next-inspection").focus()
    page.keyboard.press("Enter")
    page.locator("#lp-claim-panel .lp-source-node-btn").focus()
    page.keyboard.press("Enter")
    focused_node = page.evaluate("document.activeElement.textContent")
    _graph_drawn(page)
    _shot(page, "keyboard-flow")
    page.keyboard.press("Escape")
    # Assert
    assert (
        opened,
        "results/results.json" in focused_node,
        "MISMATCHED" in focused_node.upper(),
        page.evaluate("document.activeElement.closest('mark')?.id"),
    ) == ("lp-claim-panel-title", True, True, "claim-n_rows")


def test_every_registered_claim_has_one_interactive_mark(page):
    # Arrange
    _load(page)
    # Act
    ids = page.eval_on_selector_all(
        "mark.lp-claim-span a[aria-controls='lp-claim-panel']",
        "els => els.map(e => e.closest('mark').dataset.claimId)",
    )
    # Assert
    assert sorted(ids) == sorted(EXPECTED_STATES)


def test_narrow_screen_shows_the_panel_as_a_bottom_sheet(browser, ref_site):
    # Arrange
    out, _result, _packet = ref_site
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844}, has_touch=True, reduced_motion="reduce"
    )
    pg = ctx.new_page()
    pg.goto((out / "paper.html").as_uri())
    pg.wait_for_selector("html[data-lp-paper-ready]", state="attached")
    nav_open = pg.evaluate("document.querySelector('.lp-claim-nav-box').open")
    # Act
    pg.tap("mark#claim-cohort2 a")
    pg.wait_for_selector("#lp-claim-panel .lp-claim-graph[data-lp-rendered] svg")
    sheet = pg.locator("#lp-claim-panel").bounding_box()
    mark = pg.locator("mark#claim-cohort2").bounding_box()
    _shot(pg, "mobile-bottom-sheet")
    ctx.close()
    # Assert: a full-width sheet, the claim visible above it, navigator collapsed
    assert (
        sheet["width"] == 390,
        sheet["y"] > 200,
        0 <= mark["y"] and mark["y"] + mark["height"] <= sheet["y"],
        nav_open,
    ) == (True, True, True, False)


@pytest.mark.parametrize("width", [1440, 390])
def test_latex_reader_source_toggle_preserves_one_claim_and_evidence_panel(
    browser, ref_site, tmp_path, width
):
    # Arrange
    from copy import deepcopy

    from scitex_live_paper._renderer.paper import render_paper
    from scitex_live_paper.evidence import iter_entries

    _out, _result, packet = ref_site
    review = deepcopy(packet)
    lines = [r"\documentclass{article}", r"\title{A readable manuscript}",
             r"\begin{document}", r"\maketitle", r"\section*{Results}"]
    for entry in iter_entries(review):
        lines.append(r"The registered value is \vclaim{" + entry["claim_id"] + "}.")
        entry["location"].update(file="manuscript.tex", line=len(lines))
    lines.append(r"\end{document}")
    text = "\n".join(lines)
    result = render_paper(review, tmp_path / "reader", read_text=lambda _name: text)
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Act
    try:
        page.goto(result.paper_html.as_uri())
        page.wait_for_selector("html[data-lp-paper-ready]", state="attached")
        article = page.locator(".lp-paper-text")
        reader = article.inner_text()
        title = page.locator('.lp-tex-title').inner_text()
        reader_marks = page.locator("mark#claim-cohort2").count()
        page.locator("mark#claim-cohort2 a").click()
        page.wait_for_selector("#lp-claim-panel svg")
        verdict = _panel(page).get_attribute("data-support")
        page.keyboard.press("Escape")
        page.locator(".lp-source-toggle").check()
        source = article.inner_text()
        source_marks = page.locator("mark#claim-cohort2").count()
        page.locator(".lp-source-toggle").uncheck()
        restored = article.inner_text()
    finally:
        context.close()
    # Assert
    assert (r"\documentclass" not in reader, r"\section" not in reader, title, reader_marks, verdict, r"\documentclass{article}" in source, r"\section*{Results}" in source, source_marks, r"\documentclass" not in restored, errors) == (True, True, "A readable manuscript", 1, "not_supported", True, True, 1, True, [])


def _render_variant(ref_site, tmp_path, edit):
    """Render the paper page from a copy of the reference packet after *edit*."""
    from copy import deepcopy

    from scitex_live_paper._renderer.paper import render_paper

    _out, _result, packet = ref_site
    review = deepcopy(packet)
    edit(review)
    return render_paper(review, tmp_path / "variant").paper_html.as_uri()


def _entry(review, claim_id):
    from scitex_live_paper.evidence import iter_entries

    return next(e for e in iter_entries(review) if e["claim_id"] == claim_id)


def test_supported_claim_with_a_numeric_string_source_shows_equal(
    browser, ref_site, tmp_path
):
    # Arrange: a two-value claim whose source holds the same numbers as strings
    def edit(review):
        entry = _entry(review, "auc")
        entry["stated_text"] = "0.91"
        entry["stated_value"] = {"correct": 476, "judged": 476}
        entry["source"].update(
            value={"correct": "476", "judged": "476"}, value_reported=True
        )

    url = _render_variant(ref_site, tmp_path, edit)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    # Act
    pg.goto(url)
    pg.wait_for_selector("html[data-lp-paper-ready]", state="attached")
    pg.click("mark#claim-auc a")
    values = _panel(pg).locator(".lp-claim-values").inner_text()
    relation = (
        _panel(pg).locator("[data-value-relation]").get_attribute("data-value-relation")
    )
    ctx.close()
    # Assert
    assert (
        relation,
        "= matches the stated value" in values,
        "differs" in values,
        "correct = 476, judged = 476" in values,
    ) == ("equal", True, False, True)


def test_wide_minimal_graph_is_not_squashed_in_the_panel(browser, ref_site, tmp_path):
    # Arrange: one run reading 33 files, the shape that drew as a thin strip
    def edit(review):
        entry = _entry(review, "auc")
        nodes = [{"id": "p", "kind": "process", "label": "scripts/run.py"}]
        edges = []
        for i in range(33):
            nodes.append(
                {
                    "id": f"i{i}",
                    "kind": "input",
                    "label": f"data/file_{i:02d}.csv",
                    "hash": "0" * 8,
                }
            )
            edges.append({"source": f"i{i}", "target": "p", "kind": "input"})
        nodes += [
            {"id": "o", "kind": "output", "label": "results/out.json", "hash": "1" * 8},
            {"id": "c", "kind": "claim", "label": "auc"},
        ]
        edges += [
            {"source": "p", "target": "o", "kind": "output"},
            {"source": "o", "target": "c", "kind": "supports"},
        ]
        entry["graph"] = {"nodes": nodes, "edges": edges, "summary": "1 run, 34 files"}

    url = _render_variant(ref_site, tmp_path, edit)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    # Act
    pg.goto(url)
    pg.wait_for_selector("html[data-lp-paper-ready]", state="attached")
    pg.click("mark#claim-auc a")
    _graph_drawn(pg)
    _shot(pg, "popover-wide-graph")
    box = pg.locator("#lp-claim-panel .lp-claim-graph svg").bounding_box()
    nodes = pg.locator("#lp-claim-panel g.node[data-lp-node-kind]").count()
    ctx.close()
    # Assert: drawn at a readable aspect, every node present
    assert (box["width"] / box["height"] <= 2.5, box["height"] >= 150, nodes) == (
        True,
        True,
        36,
    )


def test_latex_reader_renders_common_inline_latex(browser, ref_site, tmp_path):
    # Arrange
    from copy import deepcopy

    from scitex_live_paper._renderer.paper import render_paper
    from scitex_live_paper.evidence import iter_entries

    _out, _result, packet = ref_site
    review = deepcopy(packet)
    lines = [
        r"\section{Results}\label{sec:results}",
        r"\begin{abstract} \pdfbookmark[1]{Abstract}{abstract}",
        r"input $\rightarrow$ output, \emph{slices}, 10\,\% in 0.7--0.8~s (Section~\ref{sec:results}).",
        r"\end{abstract}",
    ]
    for entry in iter_entries(review):
        lines.append(r"Value \vclaim{" + entry["claim_id"] + "}.")
        entry["location"].update(file="main.tex", line=len(lines))
    text = "\n".join(lines)
    result = render_paper(review, tmp_path / "inline", read_text=lambda _name: text)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    # Act
    pg.goto(result.paper_html.as_uri())
    pg.wait_for_selector("html[data-lp-paper-ready]", state="attached")
    article = pg.locator(".lp-paper-text")
    reader = article.inner_text()
    pg.locator(".lp-tex-ref").click()
    ref_url = pg.url
    pg.locator(".lp-source-toggle").check()
    source = article.inner_text()
    ctx.close()
    # Assert
    assert (
        any(raw in reader for raw in ("\\", "$", "~", "--")),
        "input → output" in reader,
        "10 %" in reader,
        "0.7–0.8" in reader,
        ref_url.endswith("#lp-label-sec:results"),
        r"\begin{abstract} \pdfbookmark[1]{Abstract}{abstract}" in source,
        r"$\rightarrow$" in source and r"10\,\%" in source,
    ) == (False, True, True, True, True, True, True)
