"""No-mocks tests for the single re-verify endpoint (``api/claim/verify``).

The endpoint asks an evidence provider through the provider-neutral
contract. Every collaborator is real: a real Django test ``Client``, real
bundles on disk, and the REAL reference provider (see ``conftest.py``)
discovered through real entry-point metadata and assessing a real
project. No ``monkeypatch``, no ``mock.patch``, no fake modules.

1. **Method + body validation** — POST-only, JSON object, claim_id,
   pinned_commit fallback chain.
2. **No provider** — a labelled fallback envelope, never a 500.
3. **Provider installed** — the claim's evidence state, plain label and
   reason come back verbatim in the envelope the SPA reads.
4. **Failures** — unknown claim → ``not_found``; provider raised → 500.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("django")

from scitex_live_paper._django import services
from scitex_live_paper._django.handlers.reverify import (
    ENV_EVIDENCE_PROVIDER,
    ENV_EVIDENCE_ROOT,
)
from scitex_live_paper.evidence import LABELS

from .conftest import PINNED_COMMIT, ref

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"


def _pin(path: Path) -> None:
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(path)
    services.clear_cache()


def _verify(client, claim_id: str = "auc", **extra):
    return client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": claim_id, **extra}),
        content_type="application/json",
    )


# ──────────────────────────────────────────────────────────────────
# Method + body validation
# ──────────────────────────────────────────────────────────────────


def test_reverify_get_returns_405(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.get("/api/claim/verify")
    # Assert
    assert response.status_code == 405


def test_reverify_get_error_says_method_not_allowed(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.get("/api/claim/verify")
    # Act
    body = json.loads(response.content)
    # Assert
    assert "method not allowed" in body["error"].lower()


def test_reverify_put_returns_405(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.put("/api/claim/verify")
    # Assert
    assert response.status_code == 405


def test_reverify_empty_body_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify", data="", content_type="application/json"
    )
    # Assert
    assert response.status_code == 400


def test_reverify_malformed_json_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify", data="not-json{{", content_type="application/json"
    )
    # Assert
    assert response.status_code == 400


def test_reverify_non_object_body_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps(["claim_a"]),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_reverify_non_object_body_error_names_json_object(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps(["claim_a"]),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "JSON object" in body["error"]


def test_reverify_missing_claim_id_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"pinned_commit": "abc"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_reverify_missing_claim_id_error_names_claim_id(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"pinned_commit": "abc"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "claim_id" in body["error"]


def test_reverify_blank_claim_id_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = _verify(client, claim_id="   ")
    # Assert
    assert response.status_code == 400


def test_reverify_without_any_pinned_commit_returns_400(client, env_snapshot):
    # Arrange — bundle-min has no state.yaml pin and the body supplies none
    _pin(BUNDLE_MIN)
    # Act
    response = _verify(client, claim_id="claim_a1b2c3d4e5f6")
    # Assert
    assert response.status_code == 400


def test_reverify_without_any_pinned_commit_error_names_pinned_commit(
    client, env_snapshot
):
    # Arrange
    _pin(BUNDLE_MIN)
    response = _verify(client, claim_id="claim_a1b2c3d4e5f6")
    # Act
    body = json.loads(response.content)
    # Assert
    assert "pinned_commit" in body["error"]


def test_reverify_body_pinned_commit_is_echoed_as_verified_against(
    client, evidence_bundle, reference_provider
):
    # Arrange
    body_commit = "cafebabe0000"
    # Act
    body = json.loads(_verify(client, pinned_commit=body_commit).content)
    # Assert
    assert body["verified_against"] == body_commit


def test_reverify_falls_back_to_bundle_state_pinned_commit(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["verified_against"] == PINNED_COMMIT


# ──────────────────────────────────────────────────────────────────
# No provider installed → graceful fallback
# ──────────────────────────────────────────────────────────────────


def test_reverify_without_provider_returns_200(client, evidence_bundle):
    # Arrange
    # Act
    response = _verify(client)
    # Assert
    assert response.status_code == 200


def test_reverify_without_provider_is_not_ok(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["ok"] is False


def test_reverify_without_provider_status_is_unassessed(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["status"] == "unassessed"


def test_reverify_without_provider_marks_fallback(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["fallback"] is True


def test_reverify_without_provider_reason_says_none_installed(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["reason"] == "no evidence provider is installed"


def test_reverify_without_provider_echoes_claim_id(client, evidence_bundle):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="n_rows").content)
    # Assert
    assert body["claim_id"] == "n_rows"


def test_reverify_configured_provider_not_installed_falls_back(
    client, evidence_bundle, reference_provider
):
    # Arrange
    os.environ[ENV_EVIDENCE_PROVIDER] = "absent-provider"
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["fallback"] is True


def test_reverify_configured_provider_not_installed_reason_names_it(
    client, evidence_bundle, reference_provider
):
    # Arrange
    os.environ[ENV_EVIDENCE_PROVIDER] = "absent-provider"
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert "absent-provider" in body["reason"]


# ──────────────────────────────────────────────────────────────────
# Provider installed → evidence state in the SPA envelope
# ──────────────────────────────────────────────────────────────────


def test_reverify_with_provider_returns_200(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    response = _verify(client)
    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("claim_id,state", sorted(ref.EXPECTED_STATES.items()))
def test_reverify_status_is_the_provider_evidence_state(
    client, evidence_bundle, reference_provider, claim_id, state
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id=claim_id).content)
    # Assert
    assert body["status"] == state


def test_reverify_assessed_claim_is_ok_even_when_not_supported(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="n_rows").content)
    # Assert
    assert body["ok"] is True


def test_reverify_state_field_equals_status(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="accuracy").content)
    # Assert
    assert body["state"] == body["status"]


def test_reverify_label_is_the_plain_language_label(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="calib").content)
    # Assert
    assert body["label"] == LABELS["no_evidence_graph"]


def test_reverify_reason_is_the_provider_reason_verbatim(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="n_rows").content)
    # Assert
    assert body["reason"] == "value in source differs: 2 in source vs 3 stated"


def test_reverify_verified_at_is_null(client, evidence_bundle, reference_provider):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["verified_at"] is None


def test_reverify_details_is_the_claims_report_entry(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="cohort2").content)
    # Assert
    assert body["details"]["details"] == ["hash changed: data/input2.csv"]


def test_reverify_details_carries_the_minimal_evidence_graph(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert {n["kind"] for n in body["details"]["graph"]["nodes"]} == {
        "process",
        "input",
        "output",
        "claim",
    }


def test_reverify_named_provider_is_used(client, evidence_bundle, reference_provider):
    # Arrange
    os.environ[ENV_EVIDENCE_PROVIDER] = reference_provider
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["status"] == "supported"


def test_reverify_evidence_root_env_points_provider_at_project(
    client, separate_project, reference_provider
):
    # Arrange
    os.environ[ENV_EVIDENCE_ROOT] = str(separate_project)
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["status"] == "supported"


# ──────────────────────────────────────────────────────────────────
# Failures
# ──────────────────────────────────────────────────────────────────


def test_reverify_claim_absent_from_report_returns_200(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    response = _verify(client, claim_id="ghost_claim")
    # Assert
    assert response.status_code == 200


def test_reverify_claim_absent_from_report_is_not_ok(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="ghost_claim").content)
    # Assert
    assert body["ok"] is False


def test_reverify_claim_absent_from_report_status_is_not_found(
    client, evidence_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client, claim_id="ghost_claim").content)
    # Assert
    assert body["status"] == "not_found"


def test_reverify_provider_failure_returns_500(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    response = _verify(client)
    # Assert
    assert response.status_code == 500


def test_reverify_provider_failure_is_not_ok(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["ok"] is False


def test_reverify_provider_failure_carries_error_message(
    client, broken_registry_bundle, reference_provider
):
    # Arrange
    # Act
    body = json.loads(_verify(client).content)
    # Assert
    assert body["error"]


def test_reverify_without_project_files_at_root_returns_500(
    client, separate_project, reference_provider
):
    # Arrange — no evidence-root override: the bundle root has no registry
    # Act
    response = _verify(client)
    # Assert
    assert response.status_code == 500


# ──────────────────────────────────────────────────────────────────
# HANDLERS registration
# ──────────────────────────────────────────────────────────────────


def test_handlers_registry_includes_api_claim_verify():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS, handle_reverify

    # Act
    handler = HANDLERS["api/claim/verify"]
    # Assert
    assert handler is handle_reverify
