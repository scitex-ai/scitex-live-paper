"""No-mocks tests for the M5 foundational slice — ``/doi/<doi>/``.

Lead green-lit (msg ``7aa6c00f``, 2026-06-14): foundational URL surface
ONLY. No CrossRef fetch, no DOI-format validation, no bundle-vs-DOI
verification, no DOI-keyed multi-tenant lookup. Just the route + view
shape + 404-on-mismatch contract, so later M5 slices have a stable
anchor.

Pins:

1. The route is registered with name ``doi_landing`` and uses
   ``<path:doi>`` so slash-bearing DOI suffixes work.
2. URL kwarg flow — the view receives ``doi`` as a string.
3. Match path — pinned-bundle DOI equals URL DOI → 200 + viewer.
4. Mismatch path — different DOI → 404 with a clean body.
5. Bundle-with-no-DOI path → 404 (no crash on ``paper_state.doi=None``).
6. Missing-env-bundle path → 404 (not 500 — the operator-facing
   answer is "no bundle for this DOI" regardless of whether ANY
   bundle is configured).
7. URL pattern ORDER — ``/doi/...`` is matched BEFORE the
   ``<path:endpoint>`` catch-all (so DOI hits never fall through to
   the api dispatcher).
8. Mount path is unaffected — ``mount(resolver=...)``'s patterns
   don't gain a DOI route (hosts handle DOI routing themselves via
   their own resolver if they want it).

All collaborators real — real ``RequestFactory``, real
``services.get_request_bundle_state``, real bundle fixtures,
real environment with snapshot/restore via fixture.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402
from django.urls import resolve, reverse  # noqa: E402

from scitex_live_paper._django import services, views  # noqa: E402
from scitex_live_paper._django.urls import urlpatterns  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"

# `bundle-accepted` ships `doi: "10.7554/eLife.99999"` in state.yaml.
ACCEPTED_DOI = "10.7554/eLife.99999"


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def env_snapshot() -> Iterator[None]:
    """Restore ``os.environ`` after the test (real state, no monkeypatch)."""
    snap = dict(os.environ)
    try:
        yield
    finally:
        for key in list(os.environ):
            if key not in snap:
                del os.environ[key]
        for key, value in snap.items():
            os.environ[key] = value


@pytest.fixture
def pinned_accepted_bundle(env_snapshot) -> Iterator[None]:
    """Pin ``SCITEX_LIVE_PAPER_BUNDLE`` to bundle-accepted and clear the cache."""
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(BUNDLE_ACCEPTED)
    services.clear_cache()
    yield
    services.clear_cache()


@pytest.fixture
def pinned_min_bundle(env_snapshot) -> Iterator[None]:
    """Pin ``SCITEX_LIVE_PAPER_BUNDLE`` to bundle-min (no DOI in state)."""
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(BUNDLE_MIN)
    services.clear_cache()
    yield
    services.clear_cache()


@pytest.fixture
def no_pinned_bundle(env_snapshot) -> Iterator[None]:
    """Ensure no bundle is env-pinned for the test."""
    os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
    services.clear_cache()
    yield
    services.clear_cache()


# ──────────────────────────────────────────────────────────────────
# Route registration + pattern shape
# ──────────────────────────────────────────────────────────────────


def test_doi_landing_pattern_is_registered():
    # Arrange
    names = [p.name for p in urlpatterns if p.name]
    # Act
    # Assert
    assert "doi_landing" in names


def test_doi_landing_uses_path_converter_for_slash_bearing_suffix():
    # The pattern MUST be `<path:doi>` (not `<str:doi>`) so DOI suffixes
    # like `10.1000/foo.bar/v2` (slashes legal per DOI handbook) match
    # without manual URL escaping.
    # Arrange
    # Act
    converters = next(
        (p.pattern.converters for p in urlpatterns if p.name == "doi_landing"),
        None,  # type: ignore[union-attr]
    )
    # Assert
    assert (
        converters is not None
        and "doi" in converters
        and type(converters["doi"]).__name__ == "PathConverter"
    )


def test_doi_landing_pattern_appears_before_catch_all__assert_doi_idx_is_not_none():
    # ORDER MATTERS — the `<path:endpoint>` catch-all would otherwise
    # swallow `/doi/<doi>/` hits and dispatch them to `api_dispatch`
    # (which 404s as an unknown endpoint).
    # Arrange
    doi_idx = None
    catch_all_idx = None
    # Act
    for i, p in enumerate(urlpatterns):
        if p.name == "doi_landing":
            doi_idx = i
        if p.name == "api_dispatch":
            catch_all_idx = i
    # Assert
    assert doi_idx is not None


def test_doi_landing_pattern_appears_before_catch_all__assert_catch_all_idx_is_not_none():
    # ORDER MATTERS — the `<path:endpoint>` catch-all would otherwise
    # swallow `/doi/<doi>/` hits and dispatch them to `api_dispatch`
    # (which 404s as an unknown endpoint).
    # Arrange
    doi_idx = None
    catch_all_idx = None
    # Act
    for i, p in enumerate(urlpatterns):
        if p.name == "doi_landing":
            doi_idx = i
        if p.name == "api_dispatch":
            catch_all_idx = i
    # Assert
    assert catch_all_idx is not None


def test_doi_landing_pattern_appears_before_catch_all__assert_doi_idx_catch_all_idx_doi():
    # ORDER MATTERS — the `<path:endpoint>` catch-all would otherwise
    # swallow `/doi/<doi>/` hits and dispatch them to `api_dispatch`
    # (which 404s as an unknown endpoint).
    # Arrange
    doi_idx = None
    catch_all_idx = None
    # Act
    for i, p in enumerate(urlpatterns):
        if p.name == "doi_landing":
            doi_idx = i
        if p.name == "api_dispatch":
            catch_all_idx = i
    # Assert
    assert doi_idx < catch_all_idx, (
        "doi_landing must precede api_dispatch in urlpatterns "
        "(else DOI hits fall through to the catch-all)"
    )




def test_reverse_yields_canonical_doi_url():
    # Arrange
    # Act
    url = reverse("live_paper:doi_landing", kwargs={"doi": "10.7554/eLife.99999"})
    # Assert
    assert url.endswith("/doi/10.7554/eLife.99999/")


def test_resolve_routes_slash_bearing_doi_to_doi_landing__assert_match_url_name_doi_landin():
    # Django's resolver MUST hand us the doi_landing view (not the
    # api_dispatch catch-all) for a slash-bearing DOI.
    # Arrange
    # Act
    match = resolve("/doi/10.1000/foo.bar/v2/")
    # Assert
    assert match.url_name == "doi_landing"


def test_resolve_routes_slash_bearing_doi_to_doi_landing__assert_match_kwargs_doi_10_1000():
    # Django's resolver MUST hand us the doi_landing view (not the
    # api_dispatch catch-all) for a slash-bearing DOI.
    # Arrange
    # Act
    match = resolve("/doi/10.1000/foo.bar/v2/")
    # Assert
    assert match.kwargs["doi"] == "10.1000/foo.bar/v2"




# ──────────────────────────────────────────────────────────────────
# Match path — pinned-bundle DOI equals URL DOI → 200 + viewer
# ──────────────────────────────────────────────────────────────────


def test_doi_landing_renders_viewer_when_doi_matches__assert_response_status_code_200(rf, pinned_accepted_bundle):
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    # Act
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Assert
    assert response.status_code == 200


def test_doi_landing_renders_viewer_when_doi_matches__assert_live_paper_root_in_body(rf, pinned_accepted_bundle):
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert "live-paper-root" in body




def test_doi_landing_match_renders_byte_identical_to_viewer_page__assert_matched_status_code_plain(
    rf, pinned_accepted_bundle,
):
    # Pin: the DOI URL is a pure alternate entry — when it matches,
    # the response body is the SAME as a `/` hit. No DOI chrome added,
    # no template variant, nothing.
    # Arrange
    match_request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    matched = views.doi_landing(match_request, doi=ACCEPTED_DOI)
    plain_request = rf.get("/")
    # Act
    plain = views.viewer_page(plain_request)
    # Assert
    assert matched.status_code == plain.status_code == 200


def test_doi_landing_match_renders_byte_identical_to_viewer_page__assert_matched_content_plain_con(
    rf, pinned_accepted_bundle,
):
    # Pin: the DOI URL is a pure alternate entry — when it matches,
    # the response body is the SAME as a `/` hit. No DOI chrome added,
    # no template variant, nothing.
    # Arrange
    match_request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    matched = views.doi_landing(match_request, doi=ACCEPTED_DOI)
    plain_request = rf.get("/")
    # Act
    plain = views.viewer_page(plain_request)
    # Assert
    assert matched.content == plain.content




# ──────────────────────────────────────────────────────────────────
# Mismatch path — different DOI → 404
# ──────────────────────────────────────────────────────────────────


def test_doi_landing_returns_404_when_doi_does_not_match__assert_response_status_code_404(rf, pinned_accepted_bundle):
    # Arrange
    request = rf.get("/doi/10.0000/wrong/")
    # Act
    response = views.doi_landing(request, doi="10.0000/wrong")
    # Assert
    assert response.status_code == 404


def test_doi_landing_returns_404_when_doi_does_not_match__assert_b_10_0000_wrong_in_respon(rf, pinned_accepted_bundle):
    # Arrange
    request = rf.get("/doi/10.0000/wrong/")
    # Act
    response = views.doi_landing(request, doi="10.0000/wrong")
    # Assert
    assert b"10.0000/wrong" in response.content




def test_doi_landing_returns_404_when_pinned_bundle_has_no_doi__assert_response_status_code_404_2(rf, pinned_min_bundle):
    # bundle-min has no state.yaml DOI (default PaperState → doi=None).
    # Any DOI request must 404 — None != "any string".
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    # Act
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Assert
    assert response.status_code == 404


def test_doi_landing_returns_404_when_pinned_bundle_has_no_doi__assert_accepted_doi_encode_in_re(rf, pinned_min_bundle):
    # bundle-min has no state.yaml DOI (default PaperState → doi=None).
    # Any DOI request must 404 — None != "any string".
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    # Act
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Assert
    assert ACCEPTED_DOI.encode() in response.content




def test_doi_landing_returns_404_when_no_bundle_pinned__assert_response_status_code_404_3(rf, no_pinned_bundle):
    # Graceful — same 404 answer as a DOI mismatch (don't leak whether
    # ANY bundle is configured vs whether THIS DOI matches).
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    # Act
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Assert
    assert response.status_code == 404


def test_doi_landing_returns_404_when_no_bundle_pinned__assert_accepted_doi_encode_in_re_2(rf, no_pinned_bundle):
    # Graceful — same 404 answer as a DOI mismatch (don't leak whether
    # ANY bundle is configured vs whether THIS DOI matches).
    # Arrange
    request = rf.get(f"/doi/{ACCEPTED_DOI}/")
    # Act
    response = views.doi_landing(request, doi=ACCEPTED_DOI)
    # Assert
    assert ACCEPTED_DOI.encode() in response.content




def test_doi_landing_404_body_does_not_leak_bundle_paths__assert_str_bundle_accepted_not_i(rf, pinned_accepted_bundle):
    # The 404 body should name the requested DOI but NOT include the
    # on-disk bundle path (operator-friendly + no info-leak).
    # Arrange
    request = rf.get("/doi/10.0000/wrong/")
    response = views.doi_landing(request, doi="10.0000/wrong")
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert str(BUNDLE_ACCEPTED) not in body


def test_doi_landing_404_body_does_not_leak_bundle_paths__assert_tmp_not_in_body(rf, pinned_accepted_bundle):
    # The 404 body should name the requested DOI but NOT include the
    # on-disk bundle path (operator-friendly + no info-leak).
    # Arrange
    request = rf.get("/doi/10.0000/wrong/")
    response = views.doi_landing(request, doi="10.0000/wrong")
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert "/tmp/" not in body




# ──────────────────────────────────────────────────────────────────
# DOI suffix shape — case-sensitivity + slashes + dots all work
# ──────────────────────────────────────────────────────────────────


def test_doi_with_dots_routes_correctly__assert_match_url_name_doi_landin_2():
    # Arrange
    # Act
    match = resolve("/doi/10.7554/eLife.99999/")
    # Assert
    assert match.url_name == "doi_landing"


def test_doi_with_dots_routes_correctly__assert_match_kwargs_doi_10_7554():
    # Arrange
    # Act
    match = resolve("/doi/10.7554/eLife.99999/")
    # Assert
    assert match.kwargs["doi"] == "10.7554/eLife.99999"




def test_doi_with_multiple_slashes_routes_correctly__assert_match_url_name_doi_landin_3():
    # Some DOIs have very long, slash-heavy suffixes (multi-segment
    # versions, sub-records). `path:` converter handles them all.
    # Arrange
    # Act
    match = resolve("/doi/10.1000/seg.a/seg.b/seg.c/")
    # Assert
    assert match.url_name == "doi_landing"


def test_doi_with_multiple_slashes_routes_correctly__assert_match_kwargs_doi_10_1000_2():
    # Some DOIs have very long, slash-heavy suffixes (multi-segment
    # versions, sub-records). `path:` converter handles them all.
    # Arrange
    # Act
    match = resolve("/doi/10.1000/seg.a/seg.b/seg.c/")
    # Assert
    assert match.kwargs["doi"] == "10.1000/seg.a/seg.b/seg.c"




def test_doi_match_is_case_sensitive(rf, pinned_accepted_bundle):
    # DOI handbook: resolution is case-INSENSITIVE but the DOI itself
    # is case-PRESERVING. For the foundational slice we do exact (case-
    # sensitive) comparison — operator can refine if they want
    # case-folding later. Pin: a different-case DOI is treated as
    # mismatch today.
    # Arrange
    mismatch_request = rf.get("/doi/10.7554/ELIFE.99999/")
    # Act
    mismatch = views.doi_landing(mismatch_request, doi="10.7554/ELIFE.99999")
    # Assert
    assert mismatch.status_code == 404


# ──────────────────────────────────────────────────────────────────
# Mount path — NOT touched (per design)
# ──────────────────────────────────────────────────────────────────


def test_mount_patterns_do_not_include_doi_landing():
    # Per design (lead msg 7aa6c00f, hub coordination msg fd0499c9):
    # the mount-side DOI surface is left to hosts. They register their
    # own DOI route + resolver under their mount prefix if they want
    # one. This test pins the absence so a future mount() change that
    # adds it has to come through a deliberate spec.
    # Arrange
    from scitex_live_paper import BundleContext, BundleSource, mount
    def stub_resolver(request, **kw):
        return BundleContext(source=BundleSource.from_directory(BUNDLE_MIN))
    # Act
    patterns, _ = mount(stub_resolver)
    names = [p.name for p in patterns if p.name]
    # Assert
    assert "doi_landing" not in names
