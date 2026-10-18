"""No-mocks tests for the reusable-component public surface.

These tests pin the contract :mod:`scitex_live_paper._types` exposes to
host apps (``scitex-writer``, ``scitex-scholar``, ``scitex-hub``). The
underlying implementation will be wired into the renderers / Django
mount by follow-up PRs; this file locks the shapes today so the host
apps can build against a stable target.

All collaborators are real — real :class:`Bundle` loaded from the
in-tree fixture, real :class:`BundleSource` constructors, real
``__post_init__`` defaults. No ``monkeypatch``, no ``mock.patch``.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest

from scitex_live_paper import (
    Bundle,
    BundleContext,
    BundleError,
    BundleResolver,
    BundleSource,
    Claim,
    PaperStage,
    PaperState,
    RendererOptions,
    bundle as bundle_module,
    RendererTheme,
)

FIXTURE_BUNDLE = (
    Path(__file__).resolve().parents[2] / "tests" / "scitex_live_paper" / "fixtures" / "bundle-min"
)


# ──────────────────────────────────────────────────────────────────
# Top-level re-exports — host apps import from `scitex_live_paper`
# ──────────────────────────────────────────────────────────────────


def test_top_level_reexports_bundle_model__assert_lp_bundle_is_bundle():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert lp.Bundle is Bundle


def test_top_level_reexports_bundle_model__assert_lp_claim_is_claim():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert lp.Claim is Claim


def test_top_level_reexports_bundle_model__assert_lp_bundleerror_is_bundlee():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert lp.BundleError is BundleError




def test_top_level_reexports_render_time_types():
    # Arrange
    import scitex_live_paper as lp
    # Act
    # Assert
    for name in (
        "BundleContext",
        "BundleResolver",
        "BundleSource",
        "PaperStage",
        "PaperState",
        "RendererOptions",
        "RendererTheme",
    ):
        assert hasattr(lp, name), f"top-level package missing public type {name!r}"


def test_all_lists_every_public_type():
    # Arrange
    import scitex_live_paper as lp
    must_export = {
        "Bundle", "BundleError", "Claim",
        "BundleContext", "BundleResolver", "BundleSource",
        "PaperStage", "PaperState",
        "RendererOptions", "RendererTheme",
    }
    # Act
    # Assert
    assert must_export <= set(lp.__all__)


# ──────────────────────────────────────────────────────────────────
# PaperState — defaults, header labels, derived flags
# ──────────────────────────────────────────────────────────────────


def test_paper_state_default_is_preprint():
    # Arrange
    # Act
    state = PaperState()
    # Assert
    assert state.stage == "preprint"


def test_paper_state_is_frozen():
    # Arrange
    # Act
    state = PaperState()
    # Assert
    with pytest.raises(Exception):
        state.stage = "accepted"  # type: ignore[misc]


def test_paper_stage_literal_lists_all_five_stages():
    # Arrange
    # Act
    stages = set(get_args(PaperStage))
    # Assert
    assert stages == {"draft", "preprint", "in_review", "accepted", "published"}


@pytest.mark.parametrize(
    "stage, expected",
    [
        ("draft", "Draft"),
        ("preprint", "Preprint"),
        ("in_review", "Under Review"),  # no journal
        ("accepted", "Accepted"),       # no journal
        ("published", "Published"),     # no journal/doi
    ],
)
def test_header_label_default_per_stage(stage, expected):
    # Arrange
    # Act
    label = PaperState(stage=stage).header_label()
    # Assert
    assert label == expected


def test_header_label_in_review_names_journal():
    # arrange
    state = PaperState(stage="in_review", journal="Nature")
    # act
    label = state.header_label()
    # assert
    assert label == "Under Review at Nature"


def test_header_label_accepted_names_journal():
    # arrange
    state = PaperState(stage="accepted", journal="eLife")
    # act
    label = state.header_label()
    # assert
    assert label == "Accepted by eLife"


def test_header_label_published_with_journal_and_doi():
    # arrange
    state = PaperState(
        stage="published",
        journal="Nature Comm",
        doi="10.1038/s41467-2026-99999",
    )
    # act
    label = state.header_label()
    # assert — bullet separator pins the operator-visible format
    assert label == "Nature Comm · DOI: 10.1038/s41467-2026-99999"


def test_show_verification_badge_off_for_draft_stages():
    # Arrange
    off_stages = ("draft", "preprint", "in_review")
    # Act
    badges = [PaperState(stage=stage).show_verification_badge for stage in off_stages]
    # Assert — one assertion: no pre-accepted stage shows the badge
    assert badges == [False, False, False]


def test_show_verification_badge_on_for_accepted_stages():
    # Arrange
    on_stages = ("accepted", "published")
    # Act
    badges = [PaperState(stage=stage).show_verification_badge for stage in on_stages]
    # Assert — one assertion: accepted+ stages show the badge
    assert badges == [True, True]


def test_re_verify_requires_accepted_plus_pinned_commit__assert_accepted_no_commit_re_ver():
    # Arrange
    accepted_no_commit = PaperState(stage="accepted")
    accepted_with_commit = PaperState(stage="accepted", pinned_commit="abc123")
    # Act
    preprint_with_commit = PaperState(stage="preprint", pinned_commit="abc123")
    # Assert
    assert accepted_no_commit.re_verify_enabled is False


def test_re_verify_requires_accepted_plus_pinned_commit__assert_accepted_with_commit_re_v():
    # Arrange
    accepted_no_commit = PaperState(stage="accepted")
    accepted_with_commit = PaperState(stage="accepted", pinned_commit="abc123")
    # Act
    preprint_with_commit = PaperState(stage="preprint", pinned_commit="abc123")
    # Assert
    assert accepted_with_commit.re_verify_enabled is True


def test_re_verify_requires_accepted_plus_pinned_commit__assert_preprint_with_commit_re_v():
    # Arrange
    accepted_no_commit = PaperState(stage="accepted")
    accepted_with_commit = PaperState(stage="accepted", pinned_commit="abc123")
    # Act
    preprint_with_commit = PaperState(stage="preprint", pinned_commit="abc123")
    # Assert
    assert preprint_with_commit.re_verify_enabled is False




# ──────────────────────────────────────────────────────────────────
# BundleSource — constructors + load() + kind property
# ──────────────────────────────────────────────────────────────────


def test_bundle_source_from_directory_resolves_path__assert_source_directory_tmp_path(tmp_path):
    # Arrange
    rel = tmp_path / "."
    # Act
    source = BundleSource.from_directory(rel)
    # Assert
    assert source.directory == tmp_path.resolve()


def test_bundle_source_from_directory_resolves_path__assert_source_kind_directory(tmp_path):
    # Arrange
    rel = tmp_path / "."
    # Act
    source = BundleSource.from_directory(rel)
    # Assert
    assert source.kind == "directory"




def test_bundle_source_from_bundle_keeps_instance__assert_source_bundle_is_real_bun():
    # Arrange
    real_bundle = bundle_module.load(FIXTURE_BUNDLE)
    # Act
    source = BundleSource.from_bundle(real_bundle)
    # Assert
    assert source.bundle is real_bundle


def test_bundle_source_from_bundle_keeps_instance__assert_source_kind_bundle():
    # Arrange
    real_bundle = bundle_module.load(FIXTURE_BUNDLE)
    # Act
    source = BundleSource.from_bundle(real_bundle)
    # Assert
    assert source.kind == "bundle"




def test_bundle_source_from_resolver_stores_callable__assert_source_resolver_is_resolv():
    # Arrange
    def resolver() -> Bundle:
        return bundle_module.load(FIXTURE_BUNDLE)
    # Act
    source = BundleSource.from_resolver(resolver)
    # Assert
    assert source.resolver is resolver


def test_bundle_source_from_resolver_stores_callable__assert_source_kind_resolver():
    # Arrange
    def resolver() -> Bundle:
        return bundle_module.load(FIXTURE_BUNDLE)
    # Act
    source = BundleSource.from_resolver(resolver)
    # Assert
    assert source.kind == "resolver"




def test_bundle_source_load_from_directory_calls_real_loader__assert_len_bundle_claims_3():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # Act
    bundle = source.load()
    # Assert
    assert len(bundle.claims) == 3


def test_bundle_source_load_from_directory_calls_real_loader__assert_bundle_schema_version_sci():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # Act
    bundle = source.load()
    # Assert
    assert bundle.schema_version == "scitex-clew.claims/v1"




def test_bundle_source_load_from_bundle_returns_same_instance():
    # arrange
    pre_loaded = bundle_module.load(FIXTURE_BUNDLE)
    source = BundleSource.from_bundle(pre_loaded)
    # act
    loaded = source.load()
    # assert
    assert loaded is pre_loaded


def test_bundle_source_load_from_resolver_invokes_callable__assert_len_calls_1():
    # Arrange
    calls: list[int] = []
    def resolver() -> Bundle:
        calls.append(1)
        return bundle_module.load(FIXTURE_BUNDLE)
    source = BundleSource.from_resolver(resolver)
    # Act
    bundle = source.load()
    # Assert
    assert len(calls) == 1


def test_bundle_source_load_from_resolver_invokes_callable__assert_isinstance_bundle_bundle():
    # Arrange
    calls: list[int] = []
    def resolver() -> Bundle:
        calls.append(1)
        return bundle_module.load(FIXTURE_BUNDLE)
    source = BundleSource.from_resolver(resolver)
    # Act
    bundle = source.load()
    # Assert
    assert isinstance(bundle, Bundle)




def test_bundle_source_load_empty_raises_value_error():
    # Arrange
    # Act
    source = BundleSource()
    # Assert
    with pytest.raises(ValueError, match="no populated slot"):
        source.load()


def test_bundle_source_kind_empty_for_unpopulated():
    # Arrange
    # Act
    source = BundleSource()
    # Assert
    assert source.kind == "empty"


def test_bundle_resolver_alias_is_callable_type():
    # Arrange
    # Act
    def resolver() -> Bundle:
        return bundle_module.load(FIXTURE_BUNDLE)
    typed: BundleResolver = resolver
    # Assert
    assert typed is resolver


# ──────────────────────────────────────────────────────────────────
# BundleContext — composition + defaults + load_bundle()
# ──────────────────────────────────────────────────────────────────


def test_bundle_context_defaults_paper_state_to_preprint():
    # arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # act
    ctx = BundleContext(source=source)
    # assert
    assert ctx.paper_state.stage == "preprint"


def test_bundle_context_defaults_api_base_to_slash_api():
    # arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # act
    ctx = BundleContext(source=source)
    # assert
    assert ctx.api_base == "/api/"


def test_bundle_context_defaults_options_to_empty_renderer_options__assert_isinstance_ctx_options_re():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # Act
    ctx = BundleContext(source=source)
    # Assert
    assert isinstance(ctx.options, RendererOptions)


def test_bundle_context_defaults_options_to_empty_renderer_options__assert_ctx_options_title_is_none():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # Act
    ctx = BundleContext(source=source)
    # Assert
    assert ctx.options.title is None


def test_bundle_context_defaults_options_to_empty_renderer_options__assert_ctx_options_embed_mode_is():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    # Act
    ctx = BundleContext(source=source)
    # Assert
    assert ctx.options.embed_mode is False




def test_bundle_context_load_bundle_delegates_to_source():
    # arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    ctx = BundleContext(source=source)
    # act
    bundle = ctx.load_bundle()
    # assert
    assert len(bundle.claims) == 3


def test_bundle_context_is_frozen():
    # Arrange
    # Act
    ctx = BundleContext(source=BundleSource.from_directory(FIXTURE_BUNDLE))
    # Assert
    with pytest.raises(Exception):
        ctx.api_base = "/other/"  # type: ignore[misc]


def test_bundle_context_carries_paper_state_through__assert_ctx_paper_state_journal_e():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    state = PaperState(stage="accepted", journal="eLife", pinned_commit="abc")
    # Act
    ctx = BundleContext(source=source, paper_state=state)
    # Assert
    assert ctx.paper_state.journal == "eLife"


def test_bundle_context_carries_paper_state_through__assert_ctx_paper_state_re_verify():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    state = PaperState(stage="accepted", journal="eLife", pinned_commit="abc")
    # Act
    ctx = BundleContext(source=source, paper_state=state)
    # Assert
    assert ctx.paper_state.re_verify_enabled is True




def test_bundle_context_carries_options_through__assert_ctx_options_title_my_pape():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    opts = RendererOptions(title="My Paper", embed_mode=True, theme="dark")
    # Act
    ctx = BundleContext(source=source, options=opts)
    # Assert
    assert ctx.options.title == "My Paper"


def test_bundle_context_carries_options_through__assert_ctx_options_embed_mode_is_2():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    opts = RendererOptions(title="My Paper", embed_mode=True, theme="dark")
    # Act
    ctx = BundleContext(source=source, options=opts)
    # Assert
    assert ctx.options.embed_mode is True


def test_bundle_context_carries_options_through__assert_ctx_options_theme_dark():
    # Arrange
    source = BundleSource.from_directory(FIXTURE_BUNDLE)
    opts = RendererOptions(title="My Paper", embed_mode=True, theme="dark")
    # Act
    ctx = BundleContext(source=source, options=opts)
    # Assert
    assert ctx.options.theme == "dark"




# ──────────────────────────────────────────────────────────────────
# RendererOptions — defaults + theme literal
# ──────────────────────────────────────────────────────────────────


def test_renderer_options_defaults_match_design__assert_opts_title_is_none():
    # Arrange
    # Act
    opts = RendererOptions()
    # Assert
    assert opts.title is None


def test_renderer_options_defaults_match_design__assert_opts_embed_mode_is_false():
    # Arrange
    # Act
    opts = RendererOptions()
    # Assert
    assert opts.embed_mode is False


def test_renderer_options_defaults_match_design__assert_opts_theme_auto():
    # Arrange
    # Act
    opts = RendererOptions()
    # Assert
    assert opts.theme == "auto"


def test_renderer_options_defaults_match_design__assert_opts_extra():
    # Arrange
    # Act
    opts = RendererOptions()
    # Assert
    assert opts.extra == {}




def test_renderer_options_is_frozen():
    # Arrange
    # Act
    opts = RendererOptions()
    # Assert
    with pytest.raises(Exception):
        opts.title = "X"  # type: ignore[misc]


def test_renderer_theme_literal_lists_auto_light_dark():
    # Arrange
    # Act
    themes = set(get_args(RendererTheme))
    # Assert
    assert themes == {"auto", "light", "dark"}


def test_renderer_options_extra_accepts_arbitrary_mapping():
    # arrange — hosts use this for analytics IDs / tenant labels
    extra = {"tenant": "scitex.ai", "analytics_id": "G-XXX"}
    # act
    opts = RendererOptions(extra=extra)
    # assert
    assert opts.extra == extra
