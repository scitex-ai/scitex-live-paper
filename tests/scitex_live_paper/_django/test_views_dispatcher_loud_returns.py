"""Dispatcher handler-return contract — loud failure on non-mapping/non-HttpResponse.

Before this fix, a handler that returned a ``list``, ``None``, ``str``,
etc. would propagate a bare ``TypeError`` from ``JsonResponse``'s
``safe=True`` check, leaving the operator to chase the failure deep
inside ``django.http.response`` rather than seeing which handler
violated the contract.

After this fix, the dispatcher checks ``isinstance(payload, Mapping)``
inside the same ``try`` block as the handler call and raises a
``TypeError`` whose message names the endpoint + the actual type. The
existing ``except Exception`` catches it and surfaces a JSON 500 the
operator can grep.

All collaborators are real: live ``HANDLERS`` dict mutated under a
snapshot fixture, Django ``RequestFactory`` for the request — no
mocks, no monkeypatch.
"""

from __future__ import annotations

import json
from typing import Iterator

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402

from scitex_live_paper._django import views  # noqa: E402
from scitex_live_paper._django.handlers import HANDLERS  # noqa: E402


# ──────────────────────────────────────────────────────────────────
# Fixtures (real state, restored on teardown — no monkeypatch)
# ──────────────────────────────────────────────────────────────────


@pytest.fixture
def handlers_snapshot() -> Iterator[dict]:
    """Snapshot HANDLERS, yield the live dict, restore on teardown."""
    snapshot = dict(HANDLERS)
    try:
        yield HANDLERS
    finally:
        HANDLERS.clear()
        HANDLERS.update(snapshot)


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


# ──────────────────────────────────────────────────────────────────
# Loud-failure assertions for every non-conformant return type
# ──────────────────────────────────────────────────────────────────


def test_list_return_surfaces_as_500_not_typeerror(handlers_snapshot, rf):
    # arrange — a handler that returns a list (the documented Card B gap)
    def list_handler(request):
        return [1, 2, 3]

    handlers_snapshot["api/list"] = list_handler

    # act — must NOT raise; must return a JSON 500 the operator can read
    response = views.api_dispatch(rf.get("/api/list"), "api/list")

    # assert
    assert response.status_code == 500


def test_list_return_names_endpoint_in_error_body(handlers_snapshot, rf):
    # arrange
    def list_handler(request):
        return [1, 2, 3]

    handlers_snapshot["api/list"] = list_handler

    # act
    response = views.api_dispatch(rf.get("/api/list"), "api/list")
    payload = json.loads(response.content)

    # assert — the endpoint name appears so the operator can grep logs
    assert "api/list" in payload["error"]


def test_list_return_names_actual_type_in_error_body(handlers_snapshot, rf):
    # arrange
    def list_handler(request):
        return [1, 2, 3]

    handlers_snapshot["api/list"] = list_handler

    # act
    response = views.api_dispatch(rf.get("/api/list"), "api/list")
    payload = json.loads(response.content)

    # assert — "list" tells the operator *what* the handler returned
    assert "list" in payload["error"]


def test_list_return_mentions_contract_in_error_body__assert_mapping_in_payload_error(handlers_snapshot, rf):
    # Arrange
    def list_handler(request):
        return [1, 2, 3]
    handlers_snapshot["api/list"] = list_handler
    response = views.api_dispatch(rf.get("/api/list"), "api/list")
    # Act
    payload = json.loads(response.content)
    # Assert
    assert "Mapping" in payload["error"]


def test_list_return_mentions_contract_in_error_body__assert_httpresponse_in_payload_e(handlers_snapshot, rf):
    # Arrange
    def list_handler(request):
        return [1, 2, 3]
    handlers_snapshot["api/list"] = list_handler
    response = views.api_dispatch(rf.get("/api/list"), "api/list")
    # Act
    payload = json.loads(response.content)
    # Assert
    assert "HttpResponse" in payload["error"]




def test_none_return_surfaces_as_500__assert_response_status_code_500(handlers_snapshot, rf):
    # Arrange
    def none_handler(request):
        return None
    handlers_snapshot["api/none"] = none_handler
    # Act
    response = views.api_dispatch(rf.get("/api/none"), "api/none")
    # Assert
    assert response.status_code == 500


def test_none_return_surfaces_as_500__assert_nonetype_in_json_loads_re(handlers_snapshot, rf):
    # Arrange
    def none_handler(request):
        return None
    handlers_snapshot["api/none"] = none_handler
    # Act
    response = views.api_dispatch(rf.get("/api/none"), "api/none")
    # Assert
    assert "NoneType" in json.loads(response.content)["error"]




def test_str_return_surfaces_as_500__assert_response_status_code_500_2(handlers_snapshot, rf):
    # Arrange
    def str_handler(request):
        return "raw string body"
    handlers_snapshot["api/str"] = str_handler
    # Act
    response = views.api_dispatch(rf.get("/api/str"), "api/str")
    # Assert
    assert response.status_code == 500


def test_str_return_surfaces_as_500__assert_str_in_json_loads_respons(handlers_snapshot, rf):
    # Arrange
    def str_handler(request):
        return "raw string body"
    handlers_snapshot["api/str"] = str_handler
    # Act
    response = views.api_dispatch(rf.get("/api/str"), "api/str")
    # Assert
    assert "str" in json.loads(response.content)["error"]




def test_int_return_surfaces_as_500__assert_response_status_code_500_3(handlers_snapshot, rf):
    # Arrange
    def int_handler(request):
        return 42
    handlers_snapshot["api/int"] = int_handler
    # Act
    response = views.api_dispatch(rf.get("/api/int"), "api/int")
    # Assert
    assert response.status_code == 500


def test_int_return_surfaces_as_500__assert_int_in_json_loads_respons(handlers_snapshot, rf):
    # Arrange
    def int_handler(request):
        return 42
    handlers_snapshot["api/int"] = int_handler
    # Act
    response = views.api_dispatch(rf.get("/api/int"), "api/int")
    # Assert
    assert "int" in json.loads(response.content)["error"]




def test_tuple_return_surfaces_as_500__assert_response_status_code_500_4(handlers_snapshot, rf):
    # Arrange
    def tuple_handler(request):
        return (1, 2)
    handlers_snapshot["api/tuple"] = tuple_handler
    # Act
    response = views.api_dispatch(rf.get("/api/tuple"), "api/tuple")
    # Assert
    assert response.status_code == 500


def test_tuple_return_surfaces_as_500__assert_tuple_in_json_loads_respo(handlers_snapshot, rf):
    # Arrange
    def tuple_handler(request):
        return (1, 2)
    handlers_snapshot["api/tuple"] = tuple_handler
    # Act
    response = views.api_dispatch(rf.get("/api/tuple"), "api/tuple")
    # Assert
    assert "tuple" in json.loads(response.content)["error"]




# ──────────────────────────────────────────────────────────────────
# Regression: the happy paths the fix moved INSIDE the try block
# still work exactly as before.
# ──────────────────────────────────────────────────────────────────


def test_dict_return_still_wraps_as_jsonresponse_200__assert_response_status_code_200(handlers_snapshot, rf):
    # Arrange
    def dict_handler(request):
        return {"hello": "world"}
    handlers_snapshot["api/dict"] = dict_handler
    # Act
    response = views.api_dispatch(rf.get("/api/dict"), "api/dict")
    # Assert
    assert response.status_code == 200


def test_dict_return_still_wraps_as_jsonresponse_200__assert_json_loads_response_conte(handlers_snapshot, rf):
    # Arrange
    def dict_handler(request):
        return {"hello": "world"}
    handlers_snapshot["api/dict"] = dict_handler
    # Act
    response = views.api_dispatch(rf.get("/api/dict"), "api/dict")
    # Assert
    assert json.loads(response.content) == {"hello": "world"}




def test_custom_mapping_subclass_passes_the_check__assert_response_status_code_200_2(handlers_snapshot, rf):
    # Arrange
    class _DictSubclass(dict):
        pass
    def mapping_handler(request):
        return _DictSubclass({"sub": True})
    handlers_snapshot["api/mapping"] = mapping_handler
    # Act
    response = views.api_dispatch(rf.get("/api/mapping"), "api/mapping")
    # Assert
    assert response.status_code == 200


def test_custom_mapping_subclass_passes_the_check__assert_json_loads_response_conte_2(handlers_snapshot, rf):
    # Arrange
    class _DictSubclass(dict):
        pass
    def mapping_handler(request):
        return _DictSubclass({"sub": True})
    handlers_snapshot["api/mapping"] = mapping_handler
    # Act
    response = views.api_dispatch(rf.get("/api/mapping"), "api/mapping")
    # Assert
    assert json.loads(response.content) == {"sub": True}




def test_httpresponse_passthrough_still_unwrapped__assert_response_is_sentinel(handlers_snapshot, rf):
    # `return` short-circuits before the Mapping check.
    # Arrange
    from django.http import HttpResponse
    sentinel = HttpResponse(b"raw", status=202)
    def http_handler(request):
        return sentinel
    handlers_snapshot["api/http"] = http_handler
    # Act
    response = views.api_dispatch(rf.get("/api/http"), "api/http")
    # Assert
    assert response is sentinel


def test_httpresponse_passthrough_still_unwrapped__assert_response_status_code_202(handlers_snapshot, rf):
    # `return` short-circuits before the Mapping check.
    # Arrange
    from django.http import HttpResponse
    sentinel = HttpResponse(b"raw", status=202)
    def http_handler(request):
        return sentinel
    handlers_snapshot["api/http"] = http_handler
    # Act
    response = views.api_dispatch(rf.get("/api/http"), "api/http")
    # Assert
    assert response.status_code == 202


