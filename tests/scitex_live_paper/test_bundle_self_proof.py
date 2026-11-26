"""No-mocks tests for the optional ``self-proof.json`` reproduction receipt.

A paper project's ``make self-proof`` re-derives every claim from a fresh
clone and writes the receipt into the bundle. ``bundle.load`` reads only the
versioned contract keys; an absent receipt is ``None`` and a malformed one is
``None`` plus a logged warning, never an error that stops the paper.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pytest
from scitex_live_paper import bundle as bundle_module
from scitex_live_paper._self_proof import parse_self_proof
from scitex_live_paper.bundle import SelfProof

BUNDLE_MIN = Path(__file__).resolve().parent / "fixtures" / "bundle-min"


def receipt(**overrides) -> dict:
    doc = {
        "schema": "paper-scitex-clew/self-proof/v1",
        "verdict": "PASS",
        "finished_at": "2026-11-26T03:04:05Z",
        "source": {
            "commit": "0123456789abcdef0123456789abcdef01234567",
            "ref": "develop",
        },
        "claims": {"ok": 12, "committed": 12, "verified": 12},
        "failures": [],
        "steps": [{"name": "clone", "seconds": 3.2}],  # not in the contract
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    shutil.copytree(BUNDLE_MIN, root)
    return root


def write(root: Path, content) -> None:
    text = content if isinstance(content, str) else json.dumps(content)
    (root / "self-proof.json").write_text(text, encoding="utf-8")


def test_absent_receipt_loads_as_none(bundle_dir, caplog):
    # Arrange
    caplog.set_level(logging.WARNING)
    # Act
    loaded = bundle_module.load(bundle_dir)
    # Assert
    assert (loaded.self_proof, caplog.records) == (None, [])


def test_present_receipt_mirrors_only_the_contract_keys(bundle_dir):
    # Arrange
    write(bundle_dir, receipt())
    # Act
    proof = bundle_module.load(bundle_dir).self_proof
    # Assert
    assert proof == SelfProof(
        schema="paper-scitex-clew/self-proof/v1",
        verdict="PASS",
        finished_at="2026-11-26T03:04:05Z",
        commit="0123456789abcdef0123456789abcdef01234567",
        ref="develop",
        ok=12,
        committed=12,
        verified=12,
        failures=(),
    )


def test_receipt_packet_form_carries_the_utc_date(bundle_dir):
    # Arrange
    write(bundle_dir, receipt(finished_at="2026-11-26T23:30:00-02:00"))
    # Act
    packet_form = bundle_module.load(bundle_dir).self_proof.to_dict()
    # Assert
    assert packet_form == {
        "schema": "paper-scitex-clew/self-proof/v1",
        "verdict": "PASS",
        "finished_at": "2026-11-26T23:30:00-02:00",
        "date": "2026-11-27",
        "source": {
            "commit": "0123456789abcdef0123456789abcdef01234567",
            "ref": "develop",
        },
        "claims": {"ok": 12, "committed": 12, "verified": 12},
        "failures": [],
    }


def test_any_producer_namespace_with_v1_suffix_is_accepted(bundle_dir):
    # Arrange
    write(
        bundle_dir,
        receipt(
            schema="another-paper/self-proof/v1",
            verdict="FAIL",
            failures=["claim fig2-auc: value differs"],
        ),
    )
    # Act
    proof = bundle_module.load(bundle_dir).self_proof
    # Assert
    assert (proof.schema, proof.verdict, proof.failures) == (
        "another-paper/self-proof/v1",
        "FAIL",
        ("claim fig2-auc: value differs",),
    )


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("{not json", id="invalid-json"),
        pytest.param("[]", id="not-an-object"),
        pytest.param(
            receipt(schema="paper-scitex-clew/self-proof/v2"), id="wrong-schema-version"
        ),
        pytest.param(
            receipt(schema="paper-scitex-clew/evidence/v1"), id="wrong-schema-kind"
        ),
        pytest.param(receipt(schema=None), id="missing-schema"),
        pytest.param(receipt(verdict="OK"), id="unknown-verdict"),
        pytest.param(receipt(finished_at="yesterday"), id="non-iso-time"),
        pytest.param(receipt(source={"ref": "develop"}), id="missing-commit"),
        pytest.param(
            receipt(claims={"ok": "12", "committed": 12, "verified": 12}),
            id="string-count",
        ),
        pytest.param(
            receipt(claims={"ok": True, "committed": 12, "verified": 12}),
            id="bool-count",
        ),
        pytest.param(receipt(failures="claim broke"), id="failures-not-a-list"),
    ],
)
def test_malformed_receipt_loads_as_none_with_a_warning(bundle_dir, caplog, content):
    # Arrange
    write(bundle_dir, content)
    caplog.set_level(logging.WARNING)
    # Act
    loaded = bundle_module.load(bundle_dir)
    # Assert
    warned = [r for r in caplog.records if "self-proof.json" in r.getMessage()]
    assert (loaded.self_proof, len(warned), len(loaded.claims) > 0) == (None, 1, True)


def test_parse_self_proof_reads_bytes_as_served_by_the_resource_reader():
    # Arrange
    raw = json.dumps(receipt()).encode("utf-8")
    # Act
    proof = parse_self_proof(raw)
    # Assert
    assert (proof.verdict, proof.ok, proof.committed) == ("PASS", 12, 12)
