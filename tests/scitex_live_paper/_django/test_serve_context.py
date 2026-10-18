"""Tests for the standalone-serve bundle-context middleware."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402

from scitex_live_paper import BundleContext, BundleSource  # noqa: E402
from scitex_live_paper._django import views  # noqa: E402
from scitex_live_paper._django.serve_context import (  # noqa: E402
    LivePaperServeContextMiddleware,
)

FIXTURE_BUNDLE = Path(__file__).resolve().parents[1] / "fixtures" / "bundle-min"
ENV_VAR = "SCITEX_LIVE_PAPER_BUNDLE"


def _run_through_middleware(request, env_dir=None):
    previous = os.environ.get(ENV_VAR)
    if env_dir is None:
        os.environ.pop(ENV_VAR, None)
    else:
        os.environ[ENV_VAR] = str(env_dir)
    try:
        middleware = LivePaperServeContextMiddleware(lambda req: req)
        return middleware(request)
    finally:
        if previous is None:
            os.environ.pop(ENV_VAR, None)
        else:
            os.environ[ENV_VAR] = previous


def test_middleware_attaches_context_from_env_bundle():
    # Arrange
    request = RequestFactory().get("/api/ping")
    # Act
    result = _run_through_middleware(request, FIXTURE_BUNDLE)
    # Assert
    assert isinstance(result.live_paper_context, BundleContext)


def test_middleware_leaves_mount_contexts_alone():
    # Arrange
    sentinel = SimpleNamespace()
    request = RequestFactory().get("/api/ping")
    request.live_paper_context = sentinel
    # Act
    result = _run_through_middleware(request, FIXTURE_BUNDLE)
    # Assert — set-if-absent: host contexts are never clobbered
    assert result.live_paper_context is sentinel


def test_middleware_no_env_no_context():
    # Arrange
    request = RequestFactory().get("/api/ping")
    # Act
    result = _run_through_middleware(request, None)
    # Assert
    assert getattr(result, "live_paper_context", None) is None


def test_port_dispatch_reaches_default_adapter_in_serve_mode():
    # Arrange — request as the standalone middleware leaves it
    request = RequestFactory().get("/api/port/figure/fig-t1")
    _run_through_middleware(request, FIXTURE_BUNDLE)
    # Act
    response = views.api_dispatch(request, "api/port/figure/fig-t1")
    body = json.loads(response.content)
    # Assert — adapter reached (unknown target), not "no adapters"
    assert (response.status_code, "no claim carries" in body["error"]) == (404, True)


def test_explicit_host_figure_adapter_is_never_overridden():
    # Arrange — host injects its own figure adapter
    from scitex_live_paper.ports import Registry, figure_fragment

    class HostFigure:
        def render_figure(self, bundle, figure_id, options):
            return figure_fragment(
                figure_id, "<svg>host</svg>", [{"label": "h", "href": "h"}]
            )

    request = RequestFactory().get("/api/port/figure/fig-t1")
    request.live_paper_context = BundleContext(
        source=BundleSource.from_directory(FIXTURE_BUNDLE),
        renderers=Registry(),
    )
    request.live_paper_context.renderers.register("figure", HostFigure())
    # Act
    response = views.api_dispatch(request, "api/port/figure/fig-t1")
    # Assert — host adapter served, bundled default did not replace it
    assert (response.status_code, json.loads(response.content)["html"]) == (
        200,
        "<svg>host</svg>",
    )
