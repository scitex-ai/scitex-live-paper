"""No-mocks tests for PR #4 — `Bundle.paper_state` wired into the renderers.

PR #5 landed `Bundle.paper_state` from the bundle's optional
`state.yaml`. This PR makes the renderers actually flex on it:

- Landing page header carries the stage label
  (``"Preprint"`` / ``"Accepted by eLife"`` / ``"Nature · DOI ..."``).
- Verification badge is visible only when ``show_verification_badge`` is True.
- Landing page meta dl exposes stage / journal / doi / pinned_commit.
- `bundle-info` API surfaces the full `paper_state` dict.

All collaborators are real: on-disk fixtures (``bundle-min`` for
preprint, ``bundle-accepted`` for eLife), real `bundle.load()`, real
Jinja2 render. No `monkeypatch`, no `unittest.mock`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scitex_live_paper import bundle as bundle_module
from scitex_live_paper._renderer.index import render_index

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"  # absent state.yaml → preprint default
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"  # accepted at eLife


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _render(tmp_path: Path, bundle_path: Path) -> str:
    """Render the landing page and return the emitted HTML body."""
    bundle = bundle_module.load(bundle_path)
    artifacts = render_index(bundle, tmp_path / "site")
    return artifacts.index_html.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────
# Preprint default (bundle-min has no state.yaml)
# ──────────────────────────────────────────────────────────────────


def test_landing_page_preprint_carries_data_paper_stage_preprint(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert 'data-paper-stage="preprint"' in body


def test_landing_page_preprint_shows_preprint_label(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "Preprint" in body


def test_landing_page_preprint_hides_verification_badge(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "lp-verification-badge" not in body


def test_landing_page_preprint_meta_shows_stage_preprint__assert_class_lp_paper_state_meta(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert 'class="lp-paper-state-meta"' in body


def test_landing_page_preprint_meta_shows_stage_preprint__assert_preprint_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert ">preprint<" in body




def test_landing_page_preprint_meta_omits_journal_dt__assert_dt_journal_dt_not_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "<dt>Journal</dt>" not in body


def test_landing_page_preprint_meta_omits_journal_dt__assert_dt_doi_dt_not_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "<dt>DOI</dt>" not in body


def test_landing_page_preprint_meta_omits_journal_dt__assert_dt_re_verify_pin_dt_not_i(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "<dt>Re-verify pin</dt>" not in body




# ──────────────────────────────────────────────────────────────────
# Accepted bundle (bundle-accepted has state.yaml @ eLife)
# ──────────────────────────────────────────────────────────────────


def test_landing_page_accepted_carries_data_paper_stage_accepted(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert 'data-paper-stage="accepted"' in body


def test_landing_page_accepted_shows_accepted_by_journal_label(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "Accepted by eLife" in body


def test_landing_page_accepted_shows_verification_badge__assert_lp_verification_badge_in(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "lp-verification-badge" in body


def test_landing_page_accepted_shows_verification_badge__assert_data_re_verify_enabled_tr(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert 'data-re-verify-enabled="true"' in body




def test_landing_page_accepted_meta_lists_journal__assert_dt_journal_dt_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "<dt>Journal</dt>" in body


def test_landing_page_accepted_meta_lists_journal__assert_elife_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "eLife" in body




def test_landing_page_accepted_meta_lists_doi__assert_dt_doi_dt_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "<dt>DOI</dt>" in body


def test_landing_page_accepted_meta_lists_doi__assert_10_7554_elife_99999_in_bo(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "10.7554/eLife.99999" in body




def test_landing_page_accepted_meta_lists_pinned_commit__assert_dt_re_verify_pin_dt_in_bo(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "<dt>Re-verify pin</dt>" in body


def test_landing_page_accepted_meta_lists_pinned_commit__assert_deadbeefcafef00d12345678(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_ACCEPTED)
    # Assert
    assert "deadbeefcafef00d12345678" in body




# ──────────────────────────────────────────────────────────────────
# Verification badge: shown iff PaperState.show_verification_badge
# ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stage",
    [
        "draft",
        "preprint",
        "in_review",
    ],
)
def test_verification_badge_hidden_for_unaccepted_stages(tmp_path, stage):
    # Arrange — synthesize a bundle with a given stage via state.yaml
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for name in ("claims.json", "dag.mmd", "provenance.yaml", "manuscript.pdf"):
        (bundle_dir / name).write_bytes((BUNDLE_MIN / name).read_bytes())
    (bundle_dir / "figz").mkdir()
    (bundle_dir / "state.yaml").write_text(f"stage: {stage}\n", encoding="utf-8")

    # Act
    body = _render(tmp_path, bundle_dir)

    # Assert
    assert "lp-verification-badge" not in body


@pytest.mark.parametrize(
    "stage",
    [
        "accepted",
        "published",
    ],
)
def test_verification_badge_shown_for_accepted_stages(tmp_path, stage):
    # Arrange — synthesize a bundle with a given stage via state.yaml
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for name in ("claims.json", "dag.mmd", "provenance.yaml", "manuscript.pdf"):
        (bundle_dir / name).write_bytes((BUNDLE_MIN / name).read_bytes())
    (bundle_dir / "figz").mkdir()
    (bundle_dir / "state.yaml").write_text(f"stage: {stage}\n", encoding="utf-8")

    # Act
    body = _render(tmp_path, bundle_dir)

    # Assert
    assert "lp-verification-badge" in body


# ──────────────────────────────────────────────────────────────────
# Verification badge: re_verify_enabled flag carried to data attribute
# ──────────────────────────────────────────────────────────────────


def test_verification_badge_re_verify_disabled_without_pinned_commit__assert_lp_verification_badge_in_2(tmp_path):
    # Arrange
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for name in ("claims.json", "dag.mmd", "provenance.yaml", "manuscript.pdf"):
        (bundle_dir / name).write_bytes((BUNDLE_MIN / name).read_bytes())
    (bundle_dir / "figz").mkdir()
    (bundle_dir / "state.yaml").write_text(
        "stage: accepted\njournal: Nature\n",
        encoding="utf-8",
    )
    # Act
    body = _render(tmp_path, bundle_dir)
    # Assert
    assert "lp-verification-badge" in body


def test_verification_badge_re_verify_disabled_without_pinned_commit__assert_data_re_verify_enabled_fa(tmp_path):
    # Arrange
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for name in ("claims.json", "dag.mmd", "provenance.yaml", "manuscript.pdf"):
        (bundle_dir / name).write_bytes((BUNDLE_MIN / name).read_bytes())
    (bundle_dir / "figz").mkdir()
    (bundle_dir / "state.yaml").write_text(
        "stage: accepted\njournal: Nature\n",
        encoding="utf-8",
    )
    # Act
    body = _render(tmp_path, bundle_dir)
    # Assert
    assert 'data-re-verify-enabled="false"' in body




# ──────────────────────────────────────────────────────────────────
# Published stage with DOI + journal — header label composition
# ──────────────────────────────────────────────────────────────────


def test_published_stage_header_label_joins_journal_and_doi(tmp_path):
    # Arrange
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for name in ("claims.json", "dag.mmd", "provenance.yaml", "manuscript.pdf"):
        (bundle_dir / name).write_bytes((BUNDLE_MIN / name).read_bytes())
    (bundle_dir / "figz").mkdir()
    (bundle_dir / "state.yaml").write_text(
        'stage: published\njournal: Nature\ndoi: "10.1038/x"\n',
        encoding="utf-8",
    )
    # Act
    body = _render(tmp_path, bundle_dir)
    # Assert
    assert "Nature · DOI: 10.1038/x" in body


# ──────────────────────────────────────────────────────────────────
# Regression: existing index sections still rendered
# ──────────────────────────────────────────────────────────────────


def test_landing_page_still_links_to_viewer_claims_dag__assert_viewer_html_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "viewer.html" in body


def test_landing_page_still_links_to_viewer_claims_dag__assert_claims_html_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "claims.html" in body


def test_landing_page_still_links_to_viewer_claims_dag__assert_dag_html_in_body(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "dag.html" in body




def test_landing_page_still_shows_manuscript_filename(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert "manuscript.pdf" in body


def test_landing_page_still_shows_total_claim_count(tmp_path):
    # Arrange
    # Act
    body = _render(tmp_path, BUNDLE_MIN)
    # Assert
    assert ">3<" in body or " 3 claims" in body
