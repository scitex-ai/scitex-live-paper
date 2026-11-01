"""Native headers describe the authorized view without remembering navigation."""

import json
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings
from scitex_sdk.ui.project_scope import LocalProjectProvider, ProjectSelection

from scitex_live_paper import BundleContext, BundleSource
from scitex_live_paper._django.views import viewer_page


class FixtureProjectProvider(LocalProjectProvider):
    def __init__(self):
        super().__init__(
            Path(settings.BASE_DIR) / "projects",
            state_file=Path(settings.BASE_DIR) / "preference.json",
        )


class ViewMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = None
        self.pickers = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id") == "live-paper-root":
            self.root = attrs
        if "data-stx-project-picker" in attrs:
            self.pickers.append(attrs)


@pytest.fixture(params=[False, True])
def embedded(request):
    return request.param


@pytest.fixture(params=[False, True], ids=["bundle", "empty-project"])
def selected_view(tmp_path, embedded, request):
    for project in ["selected", "remembered"]:
        (tmp_path / "projects" / project).mkdir(parents=True)
    preference = tmp_path / "preference.json"
    preference.write_text(json.dumps({"project": "remembered"}))
    before = preference.read_bytes()
    page_request = RequestFactory().get(
        "/", {"project": "untrusted-raw-alias", **({"embed": "1"} if embedded else {})}
    )
    page_request.user = SimpleNamespace(is_authenticated=True)
    page_request.live_paper_view_selection = ProjectSelection("project", "selected")
    if request.param:
        page_request.live_paper_empty_reason = "No LivePaper bundle in this project"
    else:
        fixture = Path(__file__).resolve().parents[1] / "fixtures/bundle-min"
        page_request.live_paper_context = BundleContext(
            source=BundleSource.from_directory(fixture)
        )
    with override_settings(
        BASE_DIR=tmp_path,
        SCITEX_PROJECT_PROVIDER=f"{__name__}.FixtureProjectProvider",
        SCITEX_PROJECT_PROVIDER_URL="/project-scope/",
    ):
        response = viewer_page(page_request)
    markup = ViewMarkup()
    markup.feed(response.content.decode())
    return markup, before, preference


def test_requested_body_view_preserves_the_different_stored_project(selected_view):
    # Arrange
    markup, before, preference = selected_view
    # Act
    observed = (
        markup.root["data-view-scope"],
        markup.root["data-view-project"],
        preference.read_bytes(),
    )
    # Assert
    assert observed == ("project", "selected", before)


@pytest.mark.parametrize("embedded", [False], indirect=True)
def test_full_header_matches_authorized_view_without_raw_current_alias(selected_view):
    # Arrange
    markup, _before, _preference = selected_view
    # Act
    picker_views = [
        (picker["data-view-scope"], picker["data-view-project"], picker["data-current"])
        for picker in markup.pickers
    ]
    # Assert
    assert picker_views == [("project", "selected", "")]
