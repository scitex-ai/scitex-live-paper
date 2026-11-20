"""Sphinx configuration for the shared Live Paper architecture source."""

from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path

project = "SciTeX Live Paper"
author = "Yusuke Watanabe"
copyright = "2026, Yusuke Watanabe"
try:
    release = distribution_version("scitex-live-paper")
except PackageNotFoundError:
    release = "0.0.0+source"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "sphinx_click",
    "sphinxcontrib.mermaid",
]
exclude_patterns = ["_build", "to_claude"]
html_theme = "sphinx_rtd_theme"
html_static_path = [
    "_static",
    str(Path(__file__).resolve().parents[2] / "src/scitex_live_paper/_django/static/live_paper/js/vendor"),
]
html_css_files = ["architecture.css"]
html_theme_options = {"navigation_depth": 2}
html_context = {
    "display_github": True,
    "github_user": "scitex-ai",
    "github_repo": "scitex-live-paper",
    "github_version": "develop",
    "conf_py_path": "/docs/sphinx/",
}
myst_fence_as_directive = {"mermaid"}
mermaid_use_local = "mermaid-loader.mjs"
mermaid_fullscreen = False
mermaid_init_config = {
    "startOnLoad": False,
    "securityLevel": "strict",
    "theme": "neutral",
    "flowchart": {"curve": "linear"},
}
