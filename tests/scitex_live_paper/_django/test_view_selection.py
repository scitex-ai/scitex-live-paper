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


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_requested_view_and_body_agree_while_stored_project_stays_different(
    tmp_path, embedded, empty
):
    for project in ["selected", "remembered"]:
        (tmp_path / "projects" / project).mkdir(parents=True)
    preference = tmp_path / "preference.json"
    preference.write_text(json.dumps({"project": "remembered"}))
    before = preference.read_bytes()
    request = RequestFactory().get(
        "/", {"project": "untrusted-raw-alias", **({"embed": "1"} if embedded else {})}
    )
    request.user = SimpleNamespace(is_authenticated=True)
    request.live_paper_view_selection = ProjectSelection("project", "selected")
    if empty:
        request.live_paper_empty_reason = "No LivePaper bundle in this project"
    else:
        fixture = Path(__file__).resolve().parents[1] / "fixtures/bundle-min"
        request.live_paper_context = BundleContext(
            source=BundleSource.from_directory(fixture)
        )
    with override_settings(
        BASE_DIR=tmp_path,
        SCITEX_PROJECT_PROVIDER=f"{__name__}.FixtureProjectProvider",
        SCITEX_PROJECT_PROVIDER_URL="/project-scope/",
    ):
        response = viewer_page(request)
    markup = ViewMarkup()
    markup.feed(response.content.decode())
    observed = (markup.root["data-view-scope"], markup.root["data-view-project"])
    if not embedded:
        assert len(markup.pickers) == 1
        assert (
            markup.pickers[0]["data-view-scope"],
            markup.pickers[0]["data-view-project"],
        ) == observed
        assert markup.pickers[0]["data-current"] != "untrusted-raw-alias"
    assert (observed, preference.read_bytes()) == (("project", "selected"), before)
