"""Shared fixtures for the re-verify endpoint tests (no mocks).

The endpoints ask an evidence provider through the provider-neutral
contract. These fixtures install the REAL reference provider from
``tests/scitex_live_paper/evidence/_reference_provider.py`` through REAL
``*.dist-info`` entry-point metadata on ``sys.path`` (exactly how an
installed distribution is found), build a real on-disk project for it to
assess, and pin a live-paper bundle that lists the project's registered
claims. Environment changes are snapshotted and restored.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

EVIDENCE_TESTS = Path(__file__).resolve().parents[2] / "evidence"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PDF = FIXTURES / "bundle-min" / "manuscript.pdf"
PINNED_COMMIT = "feedc0de1234"

if str(EVIDENCE_TESTS) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_TESTS))
import _reference_provider as ref

#: A second real provider (wraps the reference one) that appends every
#: ``evidence_report`` call to ``<project>/provider-calls.jsonl``.
COUNTING_PROVIDER_SOURCE = """\
import json
from pathlib import Path

from _reference_provider import ReferenceProvider


class CountingProvider(ReferenceProvider):
    def evidence_report(self, project_root, claim_ids, options):
        with (Path(project_root) / "provider-calls.jsonl").open("a") as fh:
            fh.write(json.dumps(claim_ids) + "\\n")
        return super().evidence_report(project_root, claim_ids, options)


class CountingEntry:
    port = "evidence"
    name = "counting"
    adapter = CountingProvider()
"""


@pytest.fixture
def env_snapshot() -> Iterator[None]:
    """Restore ``os.environ`` exactly after the test."""
    from scitex_live_paper._django import services

    snap = dict(os.environ)
    try:
        yield
    finally:
        for key in list(os.environ):
            if key not in snap:
                del os.environ[key]
        for key, value in snap.items():
            os.environ[key] = value
        services.clear_cache()


def pin_bundle(path: Path) -> None:
    """Point the Django surface at *path* and drop the bundle cache."""
    from scitex_live_paper._django import services

    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(path)
    services.clear_cache()


def _discoverable(site: Path, name: str) -> Iterator[str]:
    """Put *site* (holding a provider's dist-info) on ``sys.path``."""
    sys.path.insert(0, str(site))
    try:
        yield name
    finally:
        sys.path.remove(str(site))


@pytest.fixture
def reference_provider(tmp_path: Path) -> Iterator[str]:
    """The reference provider, discoverable as the only evidence provider."""
    site = tmp_path / "site"
    ref.install_entry_point(site)
    yield from _discoverable(site, ref.PROVIDER_NAME)


@pytest.fixture
def counting_provider(tmp_path: Path) -> Iterator[str]:
    """A call-recording real provider, discoverable as the only one."""
    site = tmp_path / "counting-site"
    dist = site / "counting_evidence_provider-1.0.dist-info"
    dist.mkdir(parents=True)
    (site / "counting_evidence_provider.py").write_text(COUNTING_PROVIDER_SOURCE)
    (dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: counting-evidence-provider\nVersion: 1.0\n"
    )
    (dist / "entry_points.txt").write_text(
        "[scitex.livepaper.renderers]\n"
        "counting = counting_evidence_provider:CountingEntry\n"
    )
    yield from _discoverable(site, "counting")


def _write_state(root: Path) -> None:
    (root / "state.yaml").write_text(
        f'stage: accepted\npinned_commit: "{PINNED_COMMIT}"\n'
    )


def _make_evidence_bundle(root: Path, *, extra_claim_ids: tuple = ()) -> Path:
    """A bundle that is also the project the provider assesses.

    ``extra_claim_ids`` adds bundle claims the provider has not registered.
    """
    ref.write_bundle(root, PDF)
    ref.build_project(root)
    if extra_claim_ids:
        claims = json.loads((root / "claims.json").read_text())
        claims += [
            {
                "claim_id": cid,
                "file_path": "paper/paper.tex",
                "claim_type": "value",
                "line_number": 7,
                "claim_value": cid,
            }
            for cid in extra_claim_ids
        ]
        (root / "claims.json").write_text(json.dumps(claims, indent=1))
    _write_state(root)
    return root


@pytest.fixture
def evidence_bundle(tmp_path: Path, env_snapshot) -> Path:
    """Pinned bundle whose root is the provider's project."""
    root = _make_evidence_bundle(tmp_path / "paper-bundle")
    pin_bundle(root)
    return root


@pytest.fixture
def bundle_with_unregistered_claim(tmp_path: Path, env_snapshot) -> Path:
    """Pinned bundle listing one claim (``ghost_claim``) the provider lacks."""
    root = _make_evidence_bundle(
        tmp_path / "paper-bundle", extra_claim_ids=("ghost_claim",)
    )
    pin_bundle(root)
    return root


@pytest.fixture
def separate_project(tmp_path: Path, env_snapshot) -> Path:
    """Pinned bundle WITHOUT project files; returns the separate project root."""
    bundle = ref.write_bundle(tmp_path / "bundle-only", PDF)
    _write_state(bundle)
    pin_bundle(bundle)
    return ref.build_project(tmp_path / "project")


@pytest.fixture
def broken_registry_bundle(evidence_bundle: Path) -> Path:
    """Pinned bundle whose registry is corrupt, so the provider really raises."""
    (evidence_bundle / "registry.json").write_text("{ this is not json")
    return evidence_bundle
