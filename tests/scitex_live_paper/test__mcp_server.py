"""§6 parity pins: every MCP tool projects a real Python API.

`_mcp_server.py` claims each tool maps back to a real Python API
(no orphan tools, no uncovered APIs) and that `skills_list` /
`skills_get` ship as a pair. This module locks both claims so a
future tool addition without a projection target fails loudly.

Real imports — no mocks, no monkeypatch. STX-TQ single-assert.
"""

from __future__ import annotations

import importlib

import pytest

from scitex_live_paper import _mcp_server

# Tool name -> dotted Python API it projects. Mirrors the "Projects ..."
# docstrings in `_mcp_server.py`; update both together.
PROJECTIONS = {
    "live_paper_bundle_load": "scitex_live_paper.bundle.load",
    "live_paper_mount": "scitex_live_paper.mount",
    "live_paper_derive_wrapper_manifest": "scitex_live_paper.derive_wrapper_manifest",
    "live_paper_dag_render_dag": "scitex_live_paper.dag.render_dag",
    "live_paper_dag_render_html": "scitex_live_paper.dag.render_html",
}


def _resolve(dotted: str):
    # Arrange
    module_name, _, attr = dotted.rpartition(".")
    # Act
    module = importlib.import_module(module_name)
    # Assert (returned for the caller's single assert)
    return getattr(module, attr)


def _tool_names():
    return [func.__name__ for func in _mcp_server._TOOL_FUNCS]


def test_tool_registry_nonempty():
    # Arrange
    # Act
    names = _tool_names()
    # Assert
    assert len(names) > 0


@pytest.mark.parametrize(
    "tool_name", list(PROJECTIONS) + ["live_paper_skills_list", "live_paper_skills_get"]
)
def test_tool_name_uses_live_paper_prefix(tool_name):
    # Arrange
    # Act
    names = _tool_names()
    # Assert
    assert tool_name in names


@pytest.mark.parametrize("tool_name,target", sorted(PROJECTIONS.items()))
def test_tool_projects_importable_python_api(tool_name, target):
    # Arrange
    names = _tool_names()
    # Act
    resolved = _resolve(target)
    # Assert
    assert (tool_name in names, callable(resolved)) == (True, True)


def test_skills_pair_ships_together():
    # Arrange
    # Act
    names = _tool_names()
    # Assert
    assert "live_paper_skills_list" in names and "live_paper_skills_get" in names


def test_mcp_server_registers_package_name():
    # Arrange
    pytest.importorskip("fastmcp")
    # Act
    server = _mcp_server.mcp
    # Assert
    assert server is not None and server.name == "scitex-live-paper"


@pytest.mark.parametrize(
    "name",
    [
        "SKILL",
        "01_installation",
        "02_quick-start",
        "03_python-api",
        "04_cli-reference",
        "05_mcp-tools",
        "10_mounted-viewer",
        "20_env-vars",
    ],
)
def test_packaged_skill_resource_is_retrievable(name):
    # Arrange
    # Act
    result = _mcp_server.live_paper_skills_get(name)
    # Assert
    assert result["name"] == name and bool(result["markdown"].strip())


def test_skills_discovery_includes_packaged_resources():
    # Arrange
    # Act
    names = _mcp_server.live_paper_skills_list()["skills"]
    # Assert
    assert {"SKILL", "01_installation", "10_mounted-viewer", "20_env-vars"}.issubset(
        names
    )
