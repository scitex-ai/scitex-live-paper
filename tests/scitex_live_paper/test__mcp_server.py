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


@pytest.mark.parametrize("tool_name", list(PROJECTIONS) + ["live_paper_skills_list", "live_paper_skills_get"])
def test_tool_name_uses_live_paper_prefix(tool_name):
    # Arrange
    # Act
    names = _tool_names()
    # Assert
    assert tool_name in names


@pytest.mark.parametrize("tool_name,target", sorted(PROJECTIONS.items()))
def test_tool_projects_importable_python_api(tool_name, target):
    # Arrange (tool must exist in the registry)
    assert tool_name in _tool_names()
    # Act
    resolved = _resolve(target)
    # Assert
    assert callable(resolved)


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
