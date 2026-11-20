"""Real mounted requests cannot turn report paths into storage authority."""

from __future__ import annotations

import copy
import json
import os
import shutil
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client, override_settings
from django.urls import include, path

from scitex_live_paper import BundleAccessDenied, BundleContext, BundleSource, mount
from scitex_live_paper._django._evidence_files import ResourceError, ResourceReader

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "bundle-min"


def make_report():
    return {
        "schema": "scitex-live-paper.evidence-report", "schema_version": "1.2.0",
        "provider": {"name": "recorded-test-evidence", "version": "1"},
        "project_root": "/untrusted/report/root",
        "claims": [{
            "claim_id": "value", "location": {"file": "paper.tex", "line": 1},
            "state": "not_supported", "reason": "Recorded source value differs",
            "stated_text": "", "stated_value": 20,
            "source": {"file": "result.json", "locator": "/value", "value": 21},
            "graph": {
                "nodes": [
                    {"id": "output", "kind": "output", "label": "result.json",
                     "failure": {"kind": "mismatched", "detail": "20 differs from 21"}},
                    {"id": "claim", "kind": "claim", "label": "value"},
                ],
                "edges": [{"source": "output", "target": "claim"}],
            },
        }],
    }


@pytest.fixture
def evidence_host(tmp_path):
    roots, reports, contexts, calls = {}, {}, {}, []
    for name in ("alice", "bob"):
        root = tmp_path / name
        shutil.copytree(FIXTURE, root)
        (root / "paper.tex").write_text(
            r"\vclaim{value} <img src=x onerror=alert(1)> " + name + " private manuscript\n"
        )
        report = make_report()
        roots[name], reports[name] = root, report
        contexts[name] = BundleContext(
            source=BundleSource.from_directory(root), evidence_report=report, resource_root=root,
        )

    def resolver(request, **_kwargs):
        name = request.GET.get("project")
        calls.append((name, request.path))
        if name not in contexts or request.headers.get("Authorization") != "Bearer " + name:
            raise BundleAccessDenied("Project is not accessible")
        return contexts[name]

    urlconf = type("EvidenceHostURLConf", (), {
        "urlpatterns": [path("mounted/paper/", include(mount(resolver=resolver)))],
    })
    with override_settings(ROOT_URLCONF=urlconf, ALLOWED_HOSTS=["testserver", "127.0.0.1"]):
        yield SimpleNamespace(
            client=Client(HTTP_AUTHORIZATION="Bearer alice"), roots=roots,
            reports=reports, contexts=contexts, calls=calls, urlconf=urlconf,
        )


def get(host, endpoint="paper.html", **query):
    return host.client.get("/mounted/paper/" + endpoint, {"project": "alice", **query})


class Resources(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = "src" if tag == "script" else "href" if tag == "link" else None
        if key and key in attrs:
            self.urls.append(attrs[key])


def test_manuscript_uses_trusted_root_escapes_text_and_preserves_values(evidence_host):
    # Arrange
    before = copy.deepcopy(evidence_host.reports)
    # Act
    response = get(evidence_host)
    html = response.content.decode()
    # Assert
    assert (
        response.status_code, "alice private manuscript" in html,
        "bob private manuscript" not in html,
        "&lt;img src=x onerror=alert(1)&gt;" in html and "<img src=x" not in html,
        'data-support="not_supported"' in html, "\\vclaim{value}" not in html,
        ">20<" in html and '"value": 21' in html, evidence_host.reports == before,
        response["Cache-Control"], "script-src 'self'" in response["Content-Security-Policy"],
    ) == (200, True, True, True, True, True, True, True, "private, no-store", True)


def test_all_page_assets_and_review_graph_links_keep_host_selectors(evidence_host):
    # Arrange
    resources = []
    # Act
    response = get(evidence_host, working_dir="manuscript with spaces", embed="1")
    urls = Resources(response.content.decode()).urls
    for url in urls:
        query = parse_qs(urlsplit(url).query)
        asset = evidence_host.client.get(url)
        resources.append((query["project"], query["working_dir"], asset.status_code,
                          asset["X-Content-Type-Options"], asset["Cache-Control"]))
    review = get(evidence_host, "review.json", working_dir="manuscript with spaces").json()
    entry = review["needs_inspection"][0]
    graph = evidence_host.client.get(entry["graph_url"])
    text = get(evidence_host, "review.txt").content
    # Assert
    assert (
        len(urls) >= 8,
        resources == [(["alice"], ["manuscript with spaces"], 200, "nosniff", "private, no-store")] * len(urls),
        review["project_root"], entry["stated_value"], entry["source"]["value"],
        graph.status_code, b"Where the evidence broke" in graph.content,
        b"project=alice" in graph.content and b"paper.html" in graph.content,
        b"Recorded source value differs" in text,
    ) == (True, True, ".", 20, 21, 200, True, True, True)


@pytest.mark.parametrize("endpoint", ["paper.html", "graph.html", "review.json", "review.txt", "assets"])
def test_every_page_and_asset_runs_host_authorization(evidence_host, endpoint):
    # Arrange
    before = len(evidence_host.calls)
    # Act
    response = get(evidence_host, endpoint, project="bob", claim_id="value", name="assets/paper.js")
    # Assert
    assert (response.status_code, len(evidence_host.calls) - before,
            b"private manuscript" not in response.content) == (403, 1, True)


@pytest.mark.parametrize("name", ["../bob/paper.tex", "/etc/passwd", "assets/../paper.tex", "assets/author.html"])
def test_asset_endpoint_never_serves_report_or_author_paths(evidence_host, name):
    # Arrange
    endpoint = "assets"
    # Act
    response = get(evidence_host, endpoint, name=name)
    # Assert
    assert response.status_code == 404


@pytest.mark.parametrize("location", ["../bob/paper.tex", "/etc/passwd", "linked/paper.tex", "linked.tex", "pipe"])
def test_outside_paths_symlinks_and_fifo_are_refused(evidence_host, location):
    # Arrange
    root = evidence_host.roots["alice"]
    (root / "linked").symlink_to(evidence_host.roots["bob"], target_is_directory=True)
    (root / "linked.tex").symlink_to(evidence_host.roots["bob"] / "paper.tex")
    os.mkfifo(root / "pipe")
    evidence_host.reports["alice"]["claims"][0]["location"]["file"] = location
    # Act
    response = get(evidence_host)
    # Assert
    assert (response.status_code, b"bob private manuscript" not in response.content) == (403, True)


def test_descriptor_root_survives_rename_and_refuses_component_replacement(tmp_path):
    # Arrange
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "nested").mkdir(parents=True)
    outside.mkdir()
    (root / "nested" / "text").write_text("authorized")
    (outside / "text").write_text("refused secret")
    # Act
    with ResourceReader(root) as reader:
        root.rename(tmp_path / "moved")
        root.symlink_to(outside, target_is_directory=True)
        content = reader.read("nested/text", limit=100)
        nested = tmp_path / "moved" / "nested"
        nested.rename(tmp_path / "original-nested")
        nested.symlink_to(outside, target_is_directory=True)
        try:
            reader.read("nested/text", limit=100)
        except ResourceError as error:
            status = error.status
        else:
            status = 200
    # Assert
    assert (content, status) == (b"authorized", 403)


def test_canonical_report_and_size_failures_are_loud(evidence_host):
    # Arrange
    context = evidence_host.contexts["alice"]
    evidence_host.contexts["alice"] = BundleContext(source=context.source)
    report_path = evidence_host.roots["alice"] / "evidence-report.json"
    # Act
    missing = get(evidence_host, "review.json").status_code
    report_path.write_text(json.dumps(evidence_host.reports["alice"]))
    present = get(evidence_host).status_code
    with override_settings(SCITEX_LIVE_PAPER_MAX_REPORT_BYTES=16):
        oversized_report = get(evidence_host, "review.json").status_code
    with override_settings(SCITEX_LIVE_PAPER_MAX_TEXT_BYTES=16):
        oversized_text = get(evidence_host).status_code
    report_path.write_text('{"secret-server-path": invalid')
    response = get(evidence_host)
    # Assert
    assert (missing, present, oversized_report, oversized_text, response.status_code,
            b"secret-server-path" not in response.content) == (404, 200, 413, 413, 400, True)


def test_reads_preserve_source_files_and_reject_post(evidence_host):
    # Arrange
    root = evidence_host.roots["alice"]
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    statuses = []
    # Act
    for endpoint in ("paper.html", "graph.html", "review.json", "review.txt", "assets"):
        get(evidence_host, endpoint, claim_id="value", name="assets/paper.js")
        response = evidence_host.client.post("/mounted/paper/" + endpoint + "?project=alice")
        statuses.append(response.status_code)
    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    # Assert
    assert (after, statuses) == (before, [405] * 5)


def test_report_metadata_is_escaped_in_manuscript_and_graph(evidence_host):
    # Arrange
    report = evidence_host.reports["alice"]
    report["provider"]["name"] = '<img src=x onerror="window.reportExecuted=1">'
    report["claims"][0]["reason"] = '<script src="/untrusted.js"></script>'
    observed = []
    # Act
    for endpoint in ("paper.html", "graph.html"):
        response = get(evidence_host, endpoint, claim_id="value")
        observed.append((response.status_code, b'<script src="/untrusted.js"' not in response.content,
                         b'<img src=x' not in response.content, b"&lt;script" in response.content))
    # Assert
    assert observed == [(200, True, True, True)] * 2


def test_viewer_links_to_the_bound_manuscript_when_report_exists(evidence_host):
    # Arrange
    observed = []
    # Act
    for embed in ("0", "1"):
        response = get(evidence_host, "", embed=embed, working_dir="chosen")
        html = response.content.decode()
        observed.append((response.status_code, "Read manuscript with evidence" in html,
                         "paper.html?project=alice&amp;embed=" in html, "working_dir=chosen" in html))
    # Assert
    assert observed == [(200, True, True, True)] * 2


@pytest.mark.parametrize("field,value", [("claim_id", {}), ("source", ["invalid"]), ("stated_text", 21)])
def test_malformed_report_fields_return_a_sanitized_contract_error(evidence_host, field, value):
    # Arrange
    evidence_host.reports["alice"]["claims"][0][field] = value
    # Act
    response = get(evidence_host)
    # Assert
    assert (response.status_code, response.content) == (400, b"Invalid evidence report contract")


def test_manuscript_limit_applies_across_all_source_files(evidence_host):
    # Arrange
    root = evidence_host.roots["alice"]
    original_size = (root / "paper.tex").stat().st_size
    (root / "second.tex").write_text("another source")
    claim = copy.deepcopy(evidence_host.reports["alice"]["claims"][0])
    claim.update(claim_id="second", location={"file": "second.tex", "line": 1})
    evidence_host.reports["alice"]["claims"].append(claim)
    # Act
    with override_settings(SCITEX_LIVE_PAPER_MAX_TEXT_BYTES=original_size):
        response = get(evidence_host)
    # Assert
    assert response.status_code == 413
