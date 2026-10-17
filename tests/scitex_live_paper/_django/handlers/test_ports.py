"""Tests for ``api/port/<port>/<target>`` dispatch.

The dispatcher routes the ``api/port/`` prefix to the injected
adapters on ``request.live_paper_context.renderers``. All
collaborators are real — real :class:`Registry`, real
:class:`BundleContext` over the in-tree fixture bundle, real
in-test adapter classes. No mocks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402

from scitex_live_paper import (  # noqa: E402
    BundleContext,
    BundleSource,
)
from scitex_live_paper._django import views  # noqa: E402
from scitex_live_paper.ports import (  # noqa: E402
    PortNotFound,
    Registry,
    figure_fragment,
    popup_fragment,
)

FIXTURE_BUNDLE = Path(__file__).resolve().parents[2] / "fixtures" / "bundle-min"


class FigureAdapter:
    """Minimal FigurePort over the fixture bundle."""

    def __init__(self) -> None:
        self.seen_options: dict = {}

    def render_figure(self, bundle, figure_id, options):
        self.seen_options = dict(options)
        if figure_id == "missing":
            raise PortNotFound(f"no such figure {figure_id!r}")
        return figure_fragment(
            figure_id,
            f"<svg>{figure_id}</svg>",
            [{"label": "data", "href": "data.csv"}],
        )


class SnippetAdapter:
    """Minimal SnippetPort."""

    def render_snippet(self, bundle, ref, options):
        return popup_fragment(
            ref, "<p>snippet</p>", [{"label": "code", "href": "plot.py"}]
        )


class GraphAdapter:
    """Minimal ClaimGraphPort."""

    def render_claim_graph(self, bundle, claim_id, options):
        return {"claim_id": claim_id, "nodes": [], "edges": []}


def _port_request(path, registry=None):
    request = RequestFactory().get(path)
    if registry is not None:
        request.live_paper_context = BundleContext(
            source=BundleSource.from_directory(FIXTURE_BUNDLE),
            renderers=registry,
        )
    return request


def _registry_with_all():
    registry = Registry()
    registry.register("figure", FigureAdapter())
    registry.register("snippet", SnippetAdapter())
    registry.register("claim-graph", GraphAdapter())
    return registry


# ---------------------------------------------------------------------------
# Happy paths — each port reaches its adapter method
# ---------------------------------------------------------------------------


def test_figure_port_returns_adapter_fragment_verbatim():
    # Arrange
    request = _port_request("/api/port/figure/fig1", _registry_with_all())
    # Act
    response = views.api_dispatch(request, "api/port/figure/fig1")
    # Assert
    assert (response.status_code, json.loads(response.content)["figure_id"]) == (
        200,
        "fig1",
    )


def test_snippet_port_routes_to_its_method():
    # Arrange
    request = _port_request("/api/port/snippet/s1", _registry_with_all())
    # Act
    response = views.api_dispatch(request, "api/port/snippet/s1")
    # Assert
    assert (response.status_code, json.loads(response.content)["title"]) == (200, "s1")


def test_claim_graph_port_routes_to_its_method():
    # Arrange
    request = _port_request("/api/port/claim-graph/c1", _registry_with_all())
    # Act
    response = views.api_dispatch(request, "api/port/claim-graph/c1")
    # Assert
    assert (response.status_code, json.loads(response.content)["claim_id"]) == (
        200,
        "c1",
    )


def test_query_params_forwarded_as_adapter_options():
    # Arrange
    adapter = FigureAdapter()
    registry = Registry()
    registry.register("figure", adapter)
    request = _port_request("/api/port/figure/fig1?theme=dark", registry)
    # Act
    response = views.api_dispatch(request, "api/port/figure/fig1")
    # Assert
    assert (response.status_code, adapter.seen_options) == (200, {"theme": "dark"})


# ---------------------------------------------------------------------------
# Failure paths — all 404, never 500, never empty 200
# ---------------------------------------------------------------------------


def test_unknown_port_404s():
    # Arrange
    request = _port_request("/api/port/nightmare/x", _registry_with_all())
    # Act
    response = views.api_dispatch(request, "api/port/nightmare/x")
    # Assert
    assert response.status_code == 404


def test_missing_registry_404s_with_named_error():
    # Arrange — standalone without injected adapters
    request = _port_request("/api/port/figure/fig1", None)
    # Act
    response = views.api_dispatch(request, "api/port/figure/fig1")
    # Assert
    assert (
        response.status_code,
        "no adapters registered" in json.loads(response.content)["error"],
    ) == (404, True)


def test_adapter_unknown_target_404s():
    # Arrange
    request = _port_request("/api/port/figure/missing", _registry_with_all())
    # Act
    response = views.api_dispatch(request, "api/port/figure/missing")
    # Assert
    assert response.status_code == 404


def test_malformed_port_endpoints_404():
    # Arrange
    registry = _registry_with_all()
    # Act
    bare = views.api_dispatch(_port_request("/api/port", registry), "api/port")
    no_target = views.api_dispatch(
        _port_request("/api/port/figure", registry), "api/port/figure"
    )
    # Assert
    assert (bare.status_code, no_target.status_code) == (404, 404)


def test_non_mapping_adapter_result_500s_loud():
    # Arrange — an adapter that breaks the JSON-plain contract
    class Bad:
        def render_figure(self, bundle, figure_id, options):
            return ["not", "a", "mapping"]

    registry = Registry()
    registry.register("figure", Bad())
    # Act
    response = views.api_dispatch(
        _port_request("/api/port/figure/fig1", registry), "api/port/figure/fig1"
    )
    # Assert — loud 500, never a silently wrong 200
    assert response.status_code == 500
