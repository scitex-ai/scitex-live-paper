"""Tests for ``api/dag`` — bundle DAG mermaid source for the SPA DAG pane."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402

from scitex_live_paper import BundleContext, BundleSource  # noqa: E402
from scitex_live_paper._django import views  # noqa: E402

FIXTURE_BUNDLE = Path(__file__).resolve().parents[2] / "fixtures" / "bundle-min"


def _request(path):
    return RequestFactory().get(path)


def test_dag_returns_bundle_mermaid_verbatim():
    # Arrange
    request = _request("/api/dag")
    request.live_paper_context = BundleContext(
        source=BundleSource.from_directory(FIXTURE_BUNDLE),
    )
    # Act
    response = views.api_dispatch(request, "api/dag")
    # Assert
    assert (response.status_code, json.loads(response.content)["mermaid"][:8]) == (
        200,
        "graph LR",
    )


def test_dag_response_carries_present_flag():
    # Arrange
    request = _request("/api/dag")
    request.live_paper_context = BundleContext(
        source=BundleSource.from_directory(FIXTURE_BUNDLE),
    )
    # Act
    response = views.api_dispatch(request, "api/dag")
    # Assert
    assert json.loads(response.content)["present"] is True


def test_dag_missing_mmd_404s_with_named_error(tmp_path):
    # Arrange — bundle copy without dag.mmd
    overlay = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, overlay)
    (overlay / "dag.mmd").unlink()
    request = _request("/api/dag")
    request.live_paper_context = BundleContext(
        source=BundleSource.from_directory(overlay),
    )
    # Act
    response = views.api_dispatch(request, "api/dag")
    # Assert
    assert (
        response.status_code,
        "no dag.mmd" in json.loads(response.content)["error"],
    ) == (404, True)
