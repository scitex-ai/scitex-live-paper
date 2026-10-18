"""STX-TQ tests for the ``_django`` skeleton — issue #8 done-when checks.

AAA blocks. Each test pins the input, runs the action, then asserts on
the response. The only branch that needs the real bundle pinned in env
is ``bundle-info``; ``ping`` and the SPA shell work without one.
"""

from __future__ import annotations

import json
import os

import pytest


# ──────────────────────────────────────────────────────────────────
# viewer_page (SPA shell)
# ──────────────────────────────────────────────────────────────────


def test_viewer_page_returns_200(client):
    # arrange
    url = "/"
    # act
    response = client.get(url)
    # assert
    assert response.status_code == 200


def test_viewer_page_contains_data_api_base_attribute(client):
    # arrange
    url = "/"
    # act
    response = client.get(url)
    # assert
    body = response.content.decode("utf-8")
    assert 'data-api-base="/api/"' in body


def test_viewer_page_references_scitex_clew_boundary(client):
    # arrange
    url = "/"
    # act
    body = client.get(url).content.decode("utf-8")
    # assert
    assert "scitex-clew" in body


# ──────────────────────────────────────────────────────────────────
# api/ping
# ──────────────────────────────────────────────────────────────────


def test_api_ping_returns_200(client):
    # arrange
    url = "/api/ping"
    # act
    response = client.get(url)
    # assert
    assert response.status_code == 200


def test_api_ping_returns_ok_true(client):
    # arrange
    url = "/api/ping"
    # act
    payload = json.loads(client.get(url).content)
    # assert
    assert payload == {"ok": True, "app": "scitex-live-paper"}


# ──────────────────────────────────────────────────────────────────
# api/bundle-info
# ──────────────────────────────────────────────────────────────────


def test_api_bundle_info_returns_200(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    response = client.get(url)
    # assert
    assert response.status_code == 200


def test_api_bundle_info_reports_three_claims(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    payload = json.loads(client.get(url).content)
    # assert — bundle-min ships exactly three claims
    assert payload["claim_count"] == 3


def test_api_bundle_info_carries_clew_schema_version(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    payload = json.loads(client.get(url).content)
    # assert — schema string owned by scitex-clew, mirrored verbatim
    assert payload["schema"] == "scitex-clew.claims/v1"


def test_api_bundle_info_reports_manuscript_pdf(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    payload = json.loads(client.get(url).content)
    # assert
    assert payload["manuscript"] == "manuscript.pdf"


def test_api_bundle_info_reports_dag_present(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    payload = json.loads(client.get(url).content)
    # assert — bundle-min ships a non-empty dag.mmd
    assert payload["dag_present"] is True


def test_api_bundle_info_resolves_absolute_bundle_path(client, bundle_env):
    # arrange
    url = "/api/bundle-info"
    # act
    payload = json.loads(client.get(url).content)
    # assert
    assert payload["bundle_path"].endswith("bundle-min")


def test_api_bundle_info_without_env_returns_500(client):
    # Arrange
    from scitex_live_paper._django import services

    previous = os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
    services.clear_cache()
    try:
        # Act
        response = client.get("/api/bundle-info")
    finally:
        if previous is not None:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        services.clear_cache()
    # Assert — services.resolve_bundle_path raises RuntimeError → dispatcher 500
    assert response.status_code == 500


# ──────────────────────────────────────────────────────────────────
# HANDLERS registry + dispatcher
# ──────────────────────────────────────────────────────────────────


def test_handlers_registry_lists_known_endpoints():
    # arrange
    from scitex_live_paper._django.handlers import HANDLERS

    # act
    keys = set(HANDLERS.keys())
    # assert
    assert {"api/ping", "api/bundle-info"} <= keys


def test_handlers_registry_values_are_callables():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS
    # Act
    # Assert
    for endpoint, fn in HANDLERS.items():
        assert callable(fn), f"{endpoint!r} → non-callable"


def test_unknown_endpoint_returns_404(client):
    # arrange
    url = "/api/does-not-exist"
    # act
    response = client.get(url)
    # assert
    assert response.status_code == 404


def test_unknown_endpoint_returns_json_error_body__assert_error_in_payload(client):
    # Arrange
    url = "/api/does-not-exist"
    # Act
    payload = json.loads(client.get(url).content)
    # Assert
    assert "error" in payload


def test_unknown_endpoint_returns_json_error_body__assert_does_not_exist_in_payload(client):
    # Arrange
    url = "/api/does-not-exist"
    # Act
    payload = json.loads(client.get(url).content)
    # Assert
    assert "does-not-exist" in payload["error"]




# ──────────────────────────────────────────────────────────────────
# services cache behaviour
# ──────────────────────────────────────────────────────────────────


def test_services_cache_reuses_state_within_ttl(bundle_env):
    # arrange
    from scitex_live_paper._django import services

    # act
    first = services.get_bundle_state()
    second = services.get_bundle_state()
    # assert — same object id implies the in-process cache hit
    assert first is second


def test_services_resolve_bundle_path_raises_without_env():
    # Arrange
    from scitex_live_paper._django import services

    previous = os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
    services.clear_cache()
    try:
        # Act
        # Assert — the raises block is the single assertion construct
        with pytest.raises(RuntimeError, match="SCITEX_LIVE_PAPER_BUNDLE"):
            services.resolve_bundle_path()
    finally:
        if previous is not None:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        services.clear_cache()


# ──────────────────────────────────────────────────────────────────
# Manifest + apps
# ──────────────────────────────────────────────────────────────────


def test_manifest_slug_is_live_paper():
    # arrange
    from importlib import resources

    # act
    data = json.loads(
        resources.files("scitex_live_paper._django")
        .joinpath("manifest.json")
        .read_text(encoding="utf-8")
    )
    # assert
    assert data["slug"] == "live-paper"


def test_apps_config_exposes_correct_name__assert_livepaperconfig_name_scit():
    # Arrange
    # Act
    from scitex_live_paper._django.apps import LivePaperConfig
    # Assert
    assert LivePaperConfig.name == "scitex_live_paper._django"


def test_apps_config_exposes_correct_name__assert_livepaperconfig_label_sci():
    # Arrange
    # Act
    from scitex_live_paper._django.apps import LivePaperConfig
    # Assert
    assert LivePaperConfig.label == "scitex_live_paper"




# ──────────────────────────────────────────────────────────────────
# CLI `serve` subcommand surface
# ──────────────────────────────────────────────────────────────────


def test_cli_top_level_help_lists_serve__assert_result_exit_code_0():
    # Arrange
    from click.testing import CliRunner
    from scitex_live_paper._cli import cli
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert result.exit_code == 0


def test_cli_top_level_help_lists_serve__assert_serve_in_result_output():
    # Arrange
    from click.testing import CliRunner
    from scitex_live_paper._cli import cli
    # Act
    result = CliRunner().invoke(cli, ["--help"])
    # Assert
    assert "serve" in result.output




def test_cli_serve_help_describes_django_extra__assert_result_exit_code_0_2():
    # Arrange
    from click.testing import CliRunner
    from scitex_live_paper._cli import cli
    # Act
    result = CliRunner().invoke(cli, ["serve", "--help"])
    # Assert
    assert result.exit_code == 0


def test_cli_serve_help_describes_django_extra__assert_django_in_result_output_l():
    # Arrange
    from click.testing import CliRunner
    from scitex_live_paper._cli import cli
    # Act
    result = CliRunner().invoke(cli, ["serve", "--help"])
    # Assert
    assert "django" in result.output.lower() or "[django]" in result.output


