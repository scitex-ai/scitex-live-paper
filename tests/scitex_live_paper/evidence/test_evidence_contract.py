"""Contract tests for the evidence-provider seam (no mocks).

A REAL provider written for these tests (``_reference_provider``) assesses
a real on-disk project; live-paper renders whatever it reports. Checked:
the contract validator agrees with the shipped JSON Schema; states and
reasons pass through; untagged text is never marked; needs-inspection
comes first; every human view agrees with the machine packet; with no
provider the site renders without states; and the source names no
specific provider. STX-TQ: AAA markers, one assert per test.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
from click.testing import CliRunner
from scitex_live_paper._cli import cli
from scitex_live_paper._cli.render import render_site
from scitex_live_paper.evidence import (
    ContractError,
    available_providers,
    build_review_packet,
    collect_report,
    find_provider,
    iter_entries,
    schema_path,
    validate_report,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _reference_provider as ref

PDF = HERE.parent / "fixtures" / "bundle-min" / "manuscript.pdf"


# --- fixtures -----------------------------------------------------------------


@pytest.fixture(scope="module")
def workdir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("evidence")


@pytest.fixture(scope="module")
def project(workdir: Path) -> Path:
    return ref.build_project(workdir / "project")


@pytest.fixture(scope="module")
def bundle(workdir: Path) -> Path:
    return ref.write_bundle(workdir / "bundle", PDF)


@pytest.fixture
def report(project: Path) -> dict:
    return ref.ReferenceProvider().evidence_report(str(project), None, {})


@pytest.fixture(scope="module")
def report_file(workdir: Path, project: Path) -> Path:
    path = workdir / "report.json"
    path.write_text(
        json.dumps(ref.ReferenceProvider().evidence_report(str(project), None, {}))
    )
    return path


@pytest.fixture(scope="module")
def site(workdir: Path, bundle: Path, report_file: Path):
    out = workdir / "site"
    result = render_site(bundle, out, evidence_report=report_file)
    return out, result, json.loads(result.review_json.read_text())


@pytest.fixture
def installed_provider(tmp_path: Path):
    """The reference provider, discoverable through real entry-point metadata."""
    site_dir = tmp_path / "site-packages"
    ref.install_entry_point(site_dir)
    sys.path.insert(0, str(site_dir))
    try:
        yield ref.PROVIDER_NAME
    finally:
        sys.path.remove(str(site_dir))


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


def _marks(html: str, tag: str, cls: str) -> list:
    parser = _Marks(tag, cls)
    parser.feed(html)
    return parser.found


def _expected(packet) -> dict:
    return {
        e["claim_id"]: (e["state"], f"{e['label']}: {e['reason']}")
        for e in iter_entries(packet)
    }


# --- contract -----------------------------------------------------------------


def test_reference_provider_reports_the_expected_states(report):
    # Arrange
    validate_report(report)
    # Act
    states = {c["claim_id"]: c["state"] for c in report["claims"]}
    # Assert
    assert states == ref.EXPECTED_STATES


def test_shipped_json_schema_accepts_a_conforming_report(report):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(schema_path().read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    # Act
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(report))
    # Assert
    assert errors == []


_MUTATIONS = {
    "foreign_state": lambda r: r["claims"][0].__setitem__("state", "verified"),
    "no_reason": lambda r: r["claims"][0].pop("reason"),
    "major_2": lambda r: r.__setitem__("schema_version", "2.0.0"),
    "no_provider_name": lambda r: r["provider"].pop("name"),
    "foreign_node_kind": lambda r: r["claims"][0]["graph"]["nodes"][0].__setitem__(
        "kind", "run"
    ),
}


@pytest.mark.parametrize("mutation", sorted(_MUTATIONS))
def test_validator_and_json_schema_reject_the_same_bad_report(report, mutation):
    # Arrange
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(schema_path().read_text())
    bad = copy.deepcopy(report)
    _MUTATIONS[mutation](bad)
    # Act
    schema_rejects = bool(
        list(jsonschema.Draft202012Validator(schema).iter_errors(bad))
    )
    try:
        validate_report(bad)
        validator_rejects = False
    except ContractError:
        validator_rejects = True
    # Assert
    assert (schema_rejects, validator_rejects) == (True, True)


def test_packet_lists_needs_inspection_in_review_order(report):
    # Arrange
    packet = build_review_packet(report)
    # Act
    order = [e["state"] for e in packet["needs_inspection"]]
    # Assert
    assert order == [
        "not_supported",
        "not_supported",
        "not_checkable",
        "no_evidence_graph",
    ]


def test_packet_lists_supported_claims_after(report):
    # Arrange
    packet = build_review_packet(report)
    # Act
    supported = [e["claim_id"] for e in packet["supported"]]
    # Assert
    assert supported == ["auc"]


def test_packet_carries_the_providers_specific_reason(report):
    # Arrange
    packet = build_review_packet(report)
    # Act
    n_rows = next(e for e in iter_entries(packet) if e["claim_id"] == "n_rows")
    # Assert
    assert n_rows["reason"] == "value in source differs: 2 in source vs 3 stated"


def test_packet_is_versioned(report):
    # Arrange
    packet = build_review_packet(report)
    # Act
    version = (packet["schema"], packet["schema_version"])
    # Assert
    assert version == ("scitex-live-paper.review-packet", "1.0.0")


def test_graph_is_fetched_on_demand_when_the_report_omits_it(project):
    # Arrange
    lazy = ref.ReferenceProvider(embed_graphs=False)
    # Act
    collected = collect_report(lazy, str(project))
    # Assert
    kinds = {
        n["kind"]
        for n in next(c for c in collected["claims"] if c["claim_id"] == "auc")[
            "graph"
        ]["nodes"]
    }
    assert kinds == {"process", "input", "output", "claim"}


def test_installed_provider_is_found_through_entry_points(installed_provider):
    # Arrange
    # Act
    name, adapter = find_provider(installed_provider)
    # Assert
    assert (name in available_providers(), callable(adapter.evidence_report)) == (
        True,
        True,
    )


# --- rendered site ----------------------------------------------------------------


def test_render_with_installed_provider_marks_every_registered_claim(
    tmp_path, bundle, project, installed_provider
):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = render_site(
        bundle, out, evidence_provider=installed_provider, evidence_root=project
    )
    # Assert
    marks = _marks(result.paper_html.read_text(), "mark", "lp-claim-span")
    assert {cid: st for cid, st, _ in marks} == ref.EXPECTED_STATES


def test_untagged_text_is_never_marked(site):
    # Arrange
    _out, result, _packet = site
    # Act
    line = next(
        l for l in result.paper_html.read_text().splitlines() if "42 degrees" in l
    )
    # Assert
    assert ("<mark" not in line, ref.UNTAGGED_TEXT in line) == (True, True)


def test_claims_page_shows_needs_inspection_before_supported(site):
    # Arrange
    out, _result, _packet = site
    # Act
    html = (out / "claims.html").read_text()
    # Assert
    assert html.index("Needs inspection (4)") < html.index("Supported by evidence (1)")


def test_paper_marks_agree_with_the_packet(site):
    # Arrange
    _out, result, packet = site
    # Act
    marks = _marks(result.paper_html.read_text(), "mark", "lp-claim-span")
    # Assert
    assert {cid: (st, title) for cid, st, title in marks} == _expected(packet)


def test_claims_page_list_agrees_with_the_packet_in_order(site):
    # Arrange
    out, _result, packet = site
    # Act
    listed = _marks((out / "claims.html").read_text(), "li", "lp-inspection-item")
    # Assert
    assert [(cid, st) for cid, st, _ in listed] == [
        (e["claim_id"], e["state"]) for e in iter_entries(packet)
    ]


def test_claims_page_shows_every_reason(site):
    # Arrange
    out, _result, packet = site
    html = (out / "claims.html").read_text()
    # Act
    missing = [e["reason"] for e in iter_entries(packet) if e["reason"] not in html]
    # Assert
    assert missing == []


def test_graph_pages_agree_with_the_packet(site):
    # Arrange
    out, _result, packet = site
    # Act
    pages = [
        _marks((out / e["graph_url"]).read_text(), "section", "lp-claim-evidence")[0][
            :2
        ]
        for e in iter_entries(packet)
    ]
    # Assert
    assert pages == [(e["claim_id"], e["state"]) for e in iter_entries(packet)]


def test_graph_page_draws_the_providers_nodes(site):
    # Arrange
    out, _result, packet = site
    # Act
    html = (out / packet["supported"][0]["graph_url"]).read_text()
    # Assert
    assert "Processing<br/>scripts/compute.py" in html


def test_review_text_agrees_with_the_packet(site):
    # Arrange
    out, _result, packet = site
    text = (out / "review.txt").read_text()
    # Act
    missing = [
        e["claim_id"]
        for e in iter_entries(packet)
        if f"{e['label']}: {e['claim_id']}" not in text or e["reason"] not in text
    ]
    # Assert
    assert missing == []


def test_no_provider_renders_claims_without_states(tmp_path, bundle):
    # Arrange
    out = tmp_path / "site"
    # Act
    result = render_site(bundle, out)
    # Assert
    assert (
        result.review_json,
        result.paper_html,
        "data-support" in (out / "claims.html").read_text(),
    ) == (None, None, False)


# --- CLI + MCP ------------------------------------------------------------------------


def test_cli_export_review_writes_the_packet(tmp_path, report_file):
    # Arrange
    out = tmp_path / "review.json"
    # Act
    res = CliRunner().invoke(
        cli, ["export-review", "--evidence-report", str(report_file), "--out", str(out)]
    )
    # Assert
    assert (res.exit_code, json.loads(out.read_text())["counts"]) == (
        0,
        {
            "not_supported": 2,
            "not_checkable": 1,
            "no_evidence_graph": 1,
            "supported": 1,
        },
    )


def test_cli_export_review_text_lists_needs_inspection(report_file):
    # Arrange
    args = ["export-review", "--evidence-report", str(report_file), "--format", "text"]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert "== NEEDS INSPECTION (4) ==" in res.output


def test_invalid_report_is_a_clean_cli_error(tmp_path, bundle, report):
    # Arrange
    report["claims"][0]["state"] = "verified"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(report))
    args = [
        "render",
        str(bundle),
        "--out",
        str(tmp_path / "s"),
        "--evidence-report",
        str(bad),
    ]
    # Act
    res = CliRunner().invoke(cli, args)
    # Assert
    assert (res.exit_code != 0, "unknown state 'verified'" in res.output) == (
        True,
        True,
    )


def test_mcp_claim_tool_returns_the_same_entry_as_the_packet(report_file, site):
    # Arrange
    from scitex_live_paper._mcp_server import live_paper_evidence_claim

    _out, _result, packet = site
    # Act
    entry = live_paper_evidence_claim("n_rows", evidence_report=str(report_file))
    # Assert
    assert {k: v for k, v in entry.items() if k != "graph_url"} == {
        k: v
        for k, v in next(
            e for e in iter_entries(packet) if e["claim_id"] == "n_rows"
        ).items()
        if k != "graph_url"
    }


# --- neutrality -------------------------------------------------------------------------

#: Specific evidence-provider packages live-paper must never name in its source.
PROVIDER_PACKAGES = re.compile(r"scitex[_-]?clew|\bclew\b", re.IGNORECASE)
#: Third-party vendored bundles are not live-paper source.
VENDORED = ("assets/pdfjs/", "assets/mermaid/", "static/live_paper/pdfjs/", "/vendor/")
SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".mjs",
    ".css",
    ".j2",
    ".html",
    ".json",
    ".md",
    ".ts",
    ".toml",
    ".yaml",
}


def test_source_names_no_specific_provider():
    # Arrange
    src = HERE.parents[2] / "src" / "scitex_live_paper"
    files = [
        p
        for p in src.rglob("*")
        if p.is_file()
        and p.suffix in SOURCE_SUFFIXES
        and not any(v in p.relative_to(src).as_posix() for v in VENDORED)
    ]
    # Act
    offenders = [
        f"{p.relative_to(src)}:{n}: {line.strip()[:100]}"
        for p in files
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
        if PROVIDER_PACKAGES.search(line)
    ]
    # Assert
    assert offenders == [], "live-paper must stay provider-neutral:\n" + "\n".join(
        offenders
    )


def test_pyproject_declares_no_provider_dependency():
    # Arrange
    pyproject = (HERE.parents[2] / "pyproject.toml").read_text()
    # Act
    found = PROVIDER_PACKAGES.findall(pyproject)
    # Assert
    assert found == []
