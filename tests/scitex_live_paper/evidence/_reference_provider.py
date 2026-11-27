"""A small, REAL evidence provider used to exercise the contract.

Not a stand-in for any particular tool: it is a complete provider of its
own. A project registers claims in ``registry.json``; a "run" records the
SHA-256 of every input and output it touched (``runs.json``). The provider
then checks, per registered claim:

1. a source is linked                     else no_evidence_graph
2. the source exists                      else not_supported
3. a recorded run produced the source     else no_evidence_graph
4. every recorded hash still matches      else not_supported
5. the claim has a locator                else not_checkable
6. the value at the locator == stated     else not_supported (with values)
                                          then supported

The minimal graph is the producing run with its inputs and output, plus the
claim node. Nodes where the evidence broke carry ``failure`` (contract 1.1.0):
``changed`` (hash differs from the run), ``missing`` (file gone), or
``mismatched`` (the source holds another value than the claim states).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROVIDER_NAME = "reference"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pointer(doc: Any, pointer: str) -> Any:
    for part in [p for p in pointer.split("/") if p]:
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


class ReferenceProvider:
    """Implements the ``evidence`` port (``evidence_report`` + ``evidence_graph``)."""

    def __init__(self, *, embed_graphs: bool = True) -> None:
        self.embed_graphs = embed_graphs

    # -- helpers --------------------------------------------------------
    @staticmethod
    def _load(root: Path) -> tuple[list[dict], list[dict]]:
        registry = json.loads((root / "registry.json").read_text())
        runs_file = root / "runs.json"
        runs = json.loads(runs_file.read_text()) if runs_file.exists() else []
        return registry, runs

    @staticmethod
    def _producer(runs: list[dict], source: str) -> dict | None:
        for run in runs:
            if source in run["outputs"]:
                return run
        return None

    def _assess(
        self, root: Path, claim: dict, runs: list[dict]
    ) -> tuple[str, str, list[str]]:
        source = claim.get("source")
        if not source:
            return (
                "no_evidence_graph",
                "no evidence graph: no source is linked to the claim",
                [],
            )
        path = root / source
        if not path.exists():
            return (
                "not_supported",
                "the source file is missing",
                [f"{source} not found"],
            )
        run = self._producer(runs, source)
        if run is None:
            return (
                "no_evidence_graph",
                "no evidence graph: the source has no recorded computation behind it",
                [f"no run recorded {source} as an output"],
            )
        recorded = {**run["inputs"], **run["outputs"]}
        changed = [p for p, h in recorded.items() if sha256(root / p) != h]
        if changed:
            return (
                "not_supported",
                "source changed after the run",
                [f"hash changed: {p}" for p in changed],
            )
        if not claim.get("pointer"):
            return "not_checkable", "no locator, value not checked", []
        actual = _pointer(json.loads(path.read_text()), claim["pointer"])
        if actual != claim["value"]:
            return (
                "not_supported",
                f"value in source differs: {actual} in source vs {claim['value']} stated",
                [f"{claim['pointer']}: {actual!r} != {claim['value']!r}"],
            )
        return "supported", "value and sources check out against the recorded run", []

    @staticmethod
    def _source(root: Path, claim: dict) -> dict:
        """Report ``source`` (1.2.0: ``value`` only when it was actually read)."""
        source, pointer = claim.get("source"), claim.get("pointer")
        out: dict[str, Any] = {"file": source, "locator": pointer}
        if source and pointer and (root / source).exists():
            out["value"] = _pointer(json.loads((root / source).read_text()), pointer)
        return out

    @staticmethod
    def _failures(root: Path, claim: dict, run: dict) -> dict[str, dict]:
        """``{file: failure}`` for every recorded file where the evidence broke."""
        out: dict[str, dict] = {}
        for p, h in {**run["inputs"], **run["outputs"]}.items():
            if not (root / p).exists():
                out[p] = {"kind": "missing", "detail": f"{p} not found"}
            elif sha256(root / p) != h:
                out[p] = {
                    "kind": "changed",
                    "detail": "hash differs from the recorded run",
                }
        source = claim["source"]
        if out or not claim.get("pointer"):
            return out
        actual = _pointer(json.loads((root / source).read_text()), claim["pointer"])
        if actual != claim["value"]:
            out[source] = {
                "kind": "mismatched",
                "detail": f"{actual} in source vs {claim['value']} stated",
            }
        return out

    def _graph(self, root: Path, claim: dict, runs: list[dict]) -> dict | None:
        source = claim.get("source")
        run = self._producer(runs, source) if source else None
        if run is None:
            return None
        failures = self._failures(root, claim, run)
        nodes = [{"id": "p", "kind": "process", "label": run["script"]}]
        edges = []
        for i, (p, h) in enumerate(sorted(run["inputs"].items())):
            nodes.append({"id": f"i{i}", "kind": "input", "label": p, "hash": h})
            edges.append({"source": f"i{i}", "target": "p", "kind": "input"})
        nodes.append(
            {
                "id": "o",
                "kind": "output",
                "label": source,
                "hash": run["outputs"][source],
            }
        )
        for n in nodes:
            if n["label"] in failures:
                n["failure"] = failures[n["label"]]
        nodes.append({"id": "c", "kind": "claim", "label": claim["claim_id"]})
        edges += [
            {"source": "p", "target": "o", "kind": "output"},
            {"source": "o", "target": "c", "kind": "supports"},
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": f"1 process, {len(run['inputs']) + 1} file(s)",
        }

    # -- the port --------------------------------------------------------
    def evidence_report(
        self,
        project_root: str,
        claim_ids: Sequence[str] | None,
        options: Mapping[str, Any],
    ) -> dict:
        root = Path(project_root)
        registry, runs = self._load(root)
        wanted = set(claim_ids) if claim_ids else None
        claims = []
        for c in registry:
            if wanted is not None and c["claim_id"] not in wanted:
                continue
            state, reason, details = self._assess(root, c, runs)
            entry = {
                "claim_id": c["claim_id"],
                "location": {
                    "file": c["file"],
                    "line": c["line"],
                    "label": f"{c['file']}:L{c['line']}",
                },
                "claim_type": "value",
                "stated_text": c["text"],
                "stated_value": c.get("value"),
                "state": state,
                "reason": reason,
                "source": self._source(root, c),
                "details": details,
                "provider_status": {"name": state.upper(), "code": None},
            }
            if self.embed_graphs:
                graph = self._graph(root, c, runs)
                entry["graph"] = graph
                if graph is None:
                    entry["graph_error"] = "no recorded run produced the source"
            claims.append(entry)
        return {
            "schema": "scitex-live-paper.evidence-report",
            "schema_version": "1.3.0",
            "provider": {"name": PROVIDER_NAME, "version": "1.0"},
            "project_name": root.name,
            "claims": claims,
        }

    def evidence_graph(
        self, project_root: str, claim_id: str, options: Mapping[str, Any]
    ):
        root = Path(project_root)
        registry, runs = self._load(root)
        claim = next(c for c in registry if c["claim_id"] == claim_id)
        return self._graph(root, claim, runs)


class ReferenceEntry:
    """Entry-point object for the ``scitex.livepaper.renderers`` group."""

    port = "evidence"
    name = PROVIDER_NAME
    adapter = ReferenceProvider()


# ---------------------------------------------------------------------------
# A small project for the provider to assess
# ---------------------------------------------------------------------------

PAPER = """\\section{Results}
The classifier reached AUC = 0.91 on the held-out set.
We analysed n = 3 recordings in total.
Overall accuracy was 0.77 across folds.
The calibration constant was k = 5 for every run.
The second cohort summed to 60 units.
The room temperature was 42 degrees during acquisition.
"""

#: claim_id -> {failing node label: failure kind} for build_project().
EXPECTED_FAILURES = {
    "auc": {},
    "n_rows": {"results/results.json": "mismatched"},
    "accuracy": {},
    "cohort2": {"data/input2.csv": "changed"},
}

#: claim_id -> state the reference provider must report for build_project().
EXPECTED_STATES = {
    "auc": "supported",
    "n_rows": "not_supported",
    "accuracy": "not_checkable",
    "calib": "no_evidence_graph",
    "cohort2": "not_supported",
}
UNTAGGED_TEXT = "The room temperature was 42 degrees during acquisition."


def build_project(root: Path) -> Path:
    """Write a project, record two runs, register claims, plant two faults."""
    (root / "paper").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "results").mkdir()
    (root / "paper" / "paper.tex").write_text(PAPER)
    (root / "data" / "input.csv").write_text("x,y\n1,2\n3,4\n")
    (root / "data" / "input2.csv").write_text("x\n10\n20\n30\n")
    (root / "results" / "results.json").write_text('{"auc": 0.91, "n_rows": 2}\n')
    (root / "results" / "results2.json").write_text('{"sum_x": 60}\n')
    (root / "paper" / "manual.json").write_text('{"k": 5}\n')

    def run(script: str, inputs: list[str], output: str) -> dict:
        return {
            "script": script,
            "inputs": {p: sha256(root / p) for p in inputs},
            "outputs": {output: sha256(root / output)},
        }

    runs = [
        run("scripts/compute.py", ["data/input.csv"], "results/results.json"),
        run("scripts/compute.py", ["data/input2.csv"], "results/results2.json"),
    ]
    (root / "runs.json").write_text(json.dumps(runs, indent=1))
    tex = "paper/paper.tex"
    registry = [
        {
            "claim_id": "auc",
            "file": tex,
            "line": 2,
            "text": "AUC = 0.91",
            "value": 0.91,
            "source": "results/results.json",
            "pointer": "/auc",
        },
        {
            "claim_id": "n_rows",
            "file": tex,
            "line": 3,
            "text": "n = 3",
            "value": 3,
            "source": "results/results.json",
            "pointer": "/n_rows",
        },
        {
            "claim_id": "accuracy",
            "file": tex,
            "line": 4,
            "text": "0.77",
            "value": 0.77,
            "source": "results/results.json",
        },
        {
            "claim_id": "calib",
            "file": tex,
            "line": 5,
            "text": "k = 5",
            "value": 5,
            "source": "paper/manual.json",
            "pointer": "/k",
        },
        {
            "claim_id": "cohort2",
            "file": tex,
            "line": 6,
            "text": "60 units",
            "value": 60,
            "source": "results/results2.json",
            "pointer": "/sum_x",
        },
    ]
    (root / "registry.json").write_text(json.dumps(registry, indent=1))
    # Fault planted after the run: an input of run 2 changes.
    (root / "data" / "input2.csv").write_text("x\n10\n20\n31\n")
    return root


def write_bundle(bundle_dir: Path, manuscript_pdf: Path) -> Path:
    """A live-paper bundle whose claims.json lists the registered claims."""
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "manuscript.pdf").write_bytes(manuscript_pdf.read_bytes())
    claims = [
        {
            "claim_id": cid,
            "file_path": "paper/paper.tex",
            "claim_type": "value",
            "line_number": line,
            "claim_value": text,
        }
        for cid, line, text in [
            ("auc", 2, "AUC = 0.91"),
            ("n_rows", 3, "n = 3"),
            ("accuracy", 4, "0.77"),
            ("calib", 5, "k = 5"),
            ("cohort2", 6, "60 units"),
        ]
    ]
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=1))
    return bundle_dir


def install_entry_point(site_dir: Path) -> Path:
    """Make ReferenceEntry discoverable through REAL entry-point metadata.

    Writes a minimal ``*.dist-info`` (METADATA + entry_points.txt) into
    *site_dir*; with *site_dir* and this module's directory on ``sys.path``,
    ``importlib.metadata.entry_points`` finds it exactly as it finds an
    installed distribution.
    """
    dist = site_dir / "reference_evidence_provider-1.0.dist-info"
    dist.mkdir(parents=True)
    (dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: reference-evidence-provider\nVersion: 1.0\n"
    )
    (dist / "entry_points.txt").write_text(
        "[scitex.livepaper.renderers]\n"
        f"{PROVIDER_NAME} = _reference_provider:ReferenceEntry\n"
    )
    return dist


# ---------------------------------------------------------------------------
# Shared pytest fixtures (function-scoped; import them into a test module)
# ---------------------------------------------------------------------------

import sys as _sys

import pytest

FIXTURE_PDF = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "bundle-min"
    / "manuscript.pdf"
)


@pytest.fixture
def ref_project(tmp_path: Path) -> Path:
    return build_project(tmp_path / "project")


@pytest.fixture
def ref_bundle(tmp_path: Path) -> Path:
    return write_bundle(tmp_path / "bundle", FIXTURE_PDF)


@pytest.fixture
def ref_report(ref_project: Path) -> dict:
    return ReferenceProvider().evidence_report(str(ref_project), None, {})


@pytest.fixture
def ref_report_file(tmp_path: Path, ref_report: dict) -> Path:
    path = tmp_path / "report.json"
    path.write_text(json.dumps(ref_report))
    return path


@pytest.fixture
def ref_site(
    tmp_path: Path, ref_bundle: Path, ref_report_file: Path, ref_project: Path
):
    """(site dir, RenderResult, review packet) rendered from the report file."""
    from scitex_live_paper._cli.render import render_site

    out = tmp_path / "site"
    result = render_site(
        ref_bundle,
        out,
        evidence_report=ref_report_file,
        evidence_root=ref_project,
    )
    return out, result, json.loads(result.review_json.read_text())


@pytest.fixture
def ref_installed_provider(tmp_path: Path):
    """The reference provider, discoverable through real entry-point metadata."""
    site_dir = tmp_path / "site-packages"
    install_entry_point(site_dir)
    _sys.path.insert(0, str(site_dir))
    try:
        yield PROVIDER_NAME
    finally:
        _sys.path.remove(str(site_dir))
