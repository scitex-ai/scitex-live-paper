"""Regression locks for the M2 runbook + README status sync.

Cheap doc-content assertions so a future README rewrite doesn't
accidentally drop the M2-shipped status (the lifecycle the operator
relies on when reading "what's done?").

Real file IO — no mocks, no monkeypatch.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────
# Runbook exists + pins the operator-facing facts
# ──────────────────────────────────────────────────────────────────


def test_m2_runbook_exists():
    # Arrange
    # Act
    # Assert
    assert (ROOT / "docs/dev/m2-reverify-runbook.md").is_file()


def test_runbook_names_the_clew_extra():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "scitex-live-paper[clew" in text


def test_runbook_documents_both_verify_endpoints__assert_api_claim_verify_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "api/claim/verify" in text


def test_runbook_documents_both_verify_endpoints__assert_api_claims_verify_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "api/claims/verify" in text




def test_runbook_documents_re_verify_enabled_gate():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "re_verify_enabled" in text


def test_runbook_documents_graceful_degradation__assert_fallback_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "fallback" in text


def test_runbook_documents_graceful_degradation__assert_stale_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "stale" in text




def test_runbook_documents_hub_mount_resolver__assert_mount_resolver_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "mount(resolver=" in text


def test_runbook_documents_hub_mount_resolver__assert_hub_resolver_in_text():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "hub_resolver" in text




# ──────────────────────────────────────────────────────────────────
# README pins M1+M2 as shipped
# ──────────────────────────────────────────────────────────────────


def test_readme_no_longer_says_pre_alpha_scaffold():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "pre-alpha scaffold" not in text


def test_readme_marks_m1_shipped():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "M1" in text and "shipped" in text


def test_readme_marks_m2_shipped():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "M2" in text and "shipped" in text


def test_readme_links_to_m2_runbook():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "docs/dev/m2-reverify-runbook.md" in text


# ──────────────────────────────────────────────────────────────────
# Dev quickstart cross-references the runbook
# ──────────────────────────────────────────────────────────────────


def test_dev_quickstart_links_to_m2_runbook():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "dev/m2-reverify-runbook.md" in text
