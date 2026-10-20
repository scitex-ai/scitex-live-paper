"""Smoke: the package entry points launch and answer `--help` (PS-211).

Subprocess-driven (`sys.executable -m ...`) so this proves the
installed entry points resolve — an in-process call would not.
Hermetic: no network, no credentials, no writes outside tmp dirs.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.smoke


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    """Run `python -m scitex_live_paper` with the given args."""
    return subprocess.run(
        [sys.executable, "-m", "scitex_live_paper", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_package_module_answers_help():
    # Arrange
    argv = "--help"
    # Act
    completed = _run_module(argv)
    # Assert
    assert (completed.returncode, "Usage:" in completed.stdout) == (0, True)


def test_package_module_answers_version():
    # Arrange
    argv = "--version"
    # Act
    completed = _run_module(argv)
    # Assert
    assert (completed.returncode, "0.2.7" in completed.stdout) == (0, True)
