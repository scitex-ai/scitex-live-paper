"""Provider discovery and on-demand graphs (real entry-point metadata, no mocks)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scitex_live_paper.evidence import (
    ProviderNotFound,
    available_providers,
    collect_report,
    find_provider,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _reference_provider import (  # noqa: E402,F401
    ReferenceProvider,
    ref_installed_provider,
    ref_project,
)


def test_graph_is_fetched_on_demand_when_the_report_omits_it(ref_project):
    # Arrange
    lazy = ReferenceProvider(embed_graphs=False)
    # Act
    collected = collect_report(lazy, str(ref_project))
    # Assert
    auc = next(c for c in collected["claims"] if c["claim_id"] == "auc")
    assert {n["kind"] for n in auc["graph"]["nodes"]} == {
        "process",
        "input",
        "output",
        "claim",
    }


def test_on_demand_graph_is_null_when_the_claim_has_none(ref_project):
    # Arrange
    lazy = ReferenceProvider(embed_graphs=False)
    # Act
    collected = collect_report(lazy, str(ref_project))
    # Assert
    assert (
        next(c for c in collected["claims"] if c["claim_id"] == "calib")["graph"]
        is None
    )


def test_installed_provider_is_found_through_entry_points(ref_installed_provider):
    # Arrange
    # Act
    name, adapter = find_provider(ref_installed_provider)
    # Assert
    assert (name in available_providers(), callable(adapter.evidence_report)) == (
        True,
        True,
    )


def test_unknown_provider_name_is_reported():
    # Arrange
    # Act
    # Assert
    with pytest.raises(ProviderNotFound):
        find_provider("no-such-provider")
