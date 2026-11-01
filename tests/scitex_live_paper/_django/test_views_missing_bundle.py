"""Actual standalone dispatch: missing resources404, malformed data500."""

import os

import pytest
from django.test import Client

from scitex_live_paper._django import services


@pytest.fixture(
    params=[
        ({"claims.json": "[]"}, 404),
        (
            {
                "manuscript.tex": r"\documentclass{article}\begin{document}Test\end{document}"
            },
            404,
        ),
        (
            {
                "manuscript.tex": r"\documentclass{article}\begin{document}Test\end{document}",
                "claims.json": "not-json",
            },
            500,
        ),
    ],
    ids=["missing-manuscript", "missing-claims", "malformed-claims"],
)
def resource_case(tmp_path, request):
    members, expected_status = request.param
    for name, content in members.items():
        (tmp_path / name).write_text(content)
    previous = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(tmp_path)
    services.clear_cache()
    try:
        yield expected_status
    finally:
        if previous is None:
            os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
        else:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        services.clear_cache()


@pytest.mark.parametrize(
    "endpoint", ["dashboard", "bundle-info", "claims", "comments", "pdf"]
)
def test_read_api_distinguishes_missing_from_malformed(resource_case, endpoint):
    # Arrange
    client = Client()
    # Act
    response = client.get("/api/" + endpoint)
    # Assert
    assert response.status_code == resource_case
