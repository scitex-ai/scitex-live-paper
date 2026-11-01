"""Actual standalone dispatch: missing resources404, malformed data500."""

import os

import pytest
from django.test import Client

from scitex_live_paper._django import services


@pytest.mark.parametrize(
    "endpoint", ["dashboard", "bundle-info", "claims", "comments", "pdf"]
)
@pytest.mark.parametrize(
    "state", ["missing-manuscript", "missing-claims", "malformed-claims"]
)
def test_read_api_distinguishes_missing_from_malformed(tmp_path, endpoint, state):
    if state != "missing-manuscript":
        (tmp_path / "manuscript.tex").write_text(
            r"\documentclass{article}\begin{document}Test\end{document}"
        )
    if state != "missing-claims":
        (tmp_path / "claims.json").write_text(
            "not-json" if state == "malformed-claims" else "[]"
        )
    previous = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(tmp_path)
    services.clear_cache()
    try:
        response = Client().get("/api/" + endpoint)
    finally:
        if previous is None:
            os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
        else:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        services.clear_cache()
    assert response.status_code == (500 if state == "malformed-claims" else 404)
