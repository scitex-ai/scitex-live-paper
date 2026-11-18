"""No-mocks tests for the bulk re-verify endpoint + Re-verify-all UI.

The endpoint collects ONE evidence report for every target claim through
the provider-neutral contract. Every collaborator is real: a real Django
test ``Client``, real bundles on disk, and REAL providers (see
``conftest.py``) discovered through real entry-point metadata — the
reference provider, and a call-recording provider built on it that logs
each ``evidence_report`` call to a file. No ``monkeypatch``, no
``mock.patch``, no fake modules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("django")

from scitex_live_paper._django import services  # noqa: E402

from .conftest import PINNED_COMMIT, ref  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"
BUNDLE_CLAIM_IDS = ["auc", "n_rows", "accuracy", "calib", "cohort2"]


def _pin(path: Path) -> None:
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(path)
    services.clear_cache()


def _verify_all(client, payload=None):
    return client.post(
        "/api/claims/verify",
        data="" if payload is None else json.dumps(payload),
        content_type="application/json",
    )


def _by_id(body) -> dict:
    return {r["claim_id"]: r for r in body["results"]}


def _provider_calls(project_root: Path) -> list:
    log = project_root / "provider-calls.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


# ──────────────────────────────────────────────────────────────────
# Method + body validation
# ──────────────────────────────────────────────────────────────────


def test_bulk_get_returns_405(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.get("/api/claims/verify")
    # Assert
    assert response.status_code == 405


def test_bulk_non_object_body_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claims/verify",
        data=json.dumps(["claim_a"]),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_bulk_claim_ids_not_a_list_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = _verify_all(client, {"claim_ids": "auc"})
    # Assert
    assert response.status_code == 400


def test_bulk_claim_ids_with_non_string_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = _verify_all(client, {"claim_ids": ["auc", 7]})
    # Assert
    assert response.status_code == 400


def test_bulk_claim_ids_with_empty_string_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = _verify_all(client, {"claim_ids": ["auc", "  "]})
    # Assert
    assert response.status_code == 400


def test_bulk_without_any_pinned_commit_returns_400(client, env_snapshot):
    # Arrange — bundle-min has no state.yaml pin and the body supplies none
    _pin(BUNDLE_MIN)
    # Act
    response = _verify_all(client)
    # Assert
    assert response.status_code == 400


# ──────────────────────────────────────────────────────────────────
# Target selection + pinned_commit
# ──────────────────────────────────────────────────────────────────


def test_bulk_without_body_verifies_every_bundle_claim(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert [r["claim_id"] for r in body["results"]] == BUNDLE_CLAIM_IDS


def test_bulk_empty_object_body_verifies_every_bundle_claim(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client, {}).content)
    # Assert
    assert body["count"] == len(BUNDLE_CLAIM_IDS)


def test_bulk_body_pinned_commit_is_echoed(client, evidence_bundle, reference_provider):
    # Arrange
    body_commit = "cafebabe0000"
    # Act
    body = json.loads(_verify_all(client, {"pinned_commit": body_commit}).content)
    # Assert
    assert body["verified_against"] == body_commit


def test_bulk_falls_back_to_bundle_state_pinned_commit(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["verified_against"] == PINNED_COMMIT


def test_bulk_per_result_envelope_echoes_pinned_commit(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert {r["verified_against"] for r in body["results"]} == {PINNED_COMMIT}


def test_bulk_filter_verifies_only_requested_ids(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client, {"claim_ids": ["n_rows"]}).content)
    # Assert
    assert [r["claim_id"] for r in body["results"]] == ["n_rows"]


def test_bulk_unknown_filter_id_is_reported_unknown(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(
        _verify_all(client, {"claim_ids": ["auc", "no_such_claim"]}).content
    )
    # Assert
    assert _by_id(body)["no_such_claim"]["status"] == "unknown"


def test_bulk_unknown_filter_id_reason_says_not_in_bundle(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(
        _verify_all(client, {"claim_ids": ["auc", "no_such_claim"]}).content
    )
    # Assert
    assert "not found in bundle" in _by_id(body)["no_such_claim"]["reason"]


def test_bulk_unknown_filter_id_flips_sweep_to_not_ok(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(
        _verify_all(client, {"claim_ids": ["auc", "no_such_claim"]}).content
    )
    # Assert
    assert body["ok"] is False


def test_bulk_unknown_filter_id_keeps_known_result(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(
        _verify_all(client, {"claim_ids": ["auc", "no_such_claim"]}).content
    )
    # Assert
    assert _by_id(body)["auc"]["status"] == "supported"


# ──────────────────────────────────────────────────────────────────
# ONE provider call per sweep
# ──────────────────────────────────────────────────────────────────


def test_bulk_asks_the_provider_exactly_once(
    client, evidence_bundle, counting_provider
):
    # Arrange
    # Act
    _verify_all(client)
    # Assert
    assert len(_provider_calls(evidence_bundle)) == 1


def test_bulk_single_provider_call_names_every_target_id(
    client, evidence_bundle, counting_provider
):
    # Arrange
    # Act
    _verify_all(client)
    # Assert
    assert _provider_calls(evidence_bundle) == [BUNDLE_CLAIM_IDS]


def test_bulk_only_unknown_ids_never_asks_the_provider(
    client, evidence_bundle, counting_provider
):
    # Arrange
    # Act
    _verify_all(client, {"claim_ids": ["no_such_claim"]})
    # Assert
    assert _provider_calls(evidence_bundle) == []


# ──────────────────────────────────────────────────────────────────
# No provider installed → per-result fallback
# ──────────────────────────────────────────────────────────────────


def test_bulk_without_provider_returns_200(client, evidence_bundle):
    # Arrange
    # Act
    response = _verify_all(client)
    # Assert
    assert response.status_code == 200


def test_bulk_without_provider_sweep_is_not_ok(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["ok"] is False


def test_bulk_without_provider_every_result_is_unassessed_fallback(
    client, evidence_bundle
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert {(r["status"], r["fallback"]) for r in body["results"]} == {
        ("unassessed", True)
    }


# ──────────────────────────────────────────────────────────────────
# Provider installed → evidence states
# ──────────────────────────────────────────────────────────────────


def test_bulk_statuses_are_the_provider_evidence_states(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert {r["claim_id"]: r["status"] for r in body["results"]} == ref.EXPECTED_STATES


def test_bulk_sweep_is_ok_when_every_claim_was_assessed(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["ok"] is True


def test_bulk_result_reason_is_the_provider_reason(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert _by_id(body)["accuracy"]["reason"] == "no locator, value not checked"


def test_bulk_count_matches_results_length(client, evidence_bundle, reference_provider):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["count"] == len(body["results"])


# ──────────────────────────────────────────────────────────────────
# Failures fold into per-result envelopes
# ──────────────────────────────────────────────────────────────────


def test_bulk_claim_missing_from_report_is_not_found(
    client, bundle_with_unregistered_claim, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert _by_id(body)["ghost_claim"]["status"] == "not_found"


def test_bulk_claim_missing_from_report_flips_sweep_to_not_ok(
    client, bundle_with_unregistered_claim, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["ok"] is False


def test_bulk_provider_failure_does_not_500_the_sweep(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    response = _verify_all(client)
    # Assert
    assert response.status_code == 200


def test_bulk_provider_failure_sweep_is_not_ok(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert body["ok"] is False


def test_bulk_provider_failure_gives_every_result_an_error(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify_all(client).content)
    # Assert
    assert all(r["ok"] is False and r["error"] for r in body["results"])
# ──────────────────────────────────────────────────────────────────
# HANDLERS registration
# ──────────────────────────────────────────────────────────────────


def test_handlers_registry_includes_api_claims_verify():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS, handle_reverify_all
    # Act
    # Assert
    assert HANDLERS["api/claims/verify"] is handle_reverify_all


# ──────────────────────────────────────────────────────────────────
# Frontend module split — refactor regression
# ──────────────────────────────────────────────────────────────────


def _js_bundle_text() -> str:
    """Concatenated text of every JS module under live_paper/js/."""
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    js_dir = pkg_root / "_django/static/live_paper/js"
    parts = []
    for name in (
        "viewer.js",
        "pdf-viewer.js",
        "claims-sidebar.js",
        "reverify-all.js",
        "_utils.js",
    ):
        parts.append((js_dir / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


def _module_file(name: str) -> Path:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return pkg_root / "_django/static/live_paper/js" / name


def test_module_files_all_exist():
    # Arrange
    # Act
    # Assert
    for name in ("viewer.js", "pdf-viewer.js", "claims-sidebar.js", "reverify-all.js", "_utils.js"):
        assert _module_file(name).is_file(), f"missing module: {name}"


def test_viewer_js_imports_from_split_modules__assert_from_utils_js_in_text():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./_utils.js"' in text


def test_viewer_js_imports_from_split_modules__assert_from_pdf_viewer_js_in_tex():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./pdf-viewer.js"' in text


def test_viewer_js_imports_from_split_modules__assert_from_claims_sidebar_js_in():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./claims-sidebar.js"' in text




def test_pdf_viewer_exports_pdfviewer_class():
    # Arrange
    # Act
    text = _module_file("pdf-viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "export class PDFViewer" in text


def test_claims_sidebar_exports_render_claims_sidebar():
    # Arrange
    # Act
    text = _module_file("claims-sidebar.js").read_text(encoding="utf-8")
    # Assert
    assert "export function renderClaimsSidebar" in text


def test_reverify_all_exports_render_button():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert "export function renderReverifyAllButton" in text


# ──────────────────────────────────────────────────────────────────
# Bulk UI wiring (reverify-all.js source)
# ──────────────────────────────────────────────────────────────────


def test_reverify_all_button_posts_to_claims_verify():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert 'apiBase + "claims/verify"' in text


def test_reverify_all_button_flips_rows_to_verifying_first():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert '"verifying"' in text


def test_reverify_all_walks_results_per_claim():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert "payload.results" in text


def test_reverify_all_handles_fallback_envelope():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert "result.fallback === true" in text


def test_reverify_all_handles_network_error():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert "network error" in text


def test_reverify_all_re_enables_per_claim_buttons_in_finally():
    # Arrange
    # Act
    text = _module_file("reverify-all.js").read_text(encoding="utf-8")
    # Assert
    assert "b.disabled = false" in text
