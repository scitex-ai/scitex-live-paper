"""Mirror test for `examples/example_live_paper.py` (PS-303).

Runs the example as a subprocess and asserts it exits cleanly and
prints the bundle summary.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "example_live_paper.py"


def test_example_live_paper_runs_and_prints_summary():
    # Arrange
    argv = [sys.executable, str(EXAMPLE)]
    # Act
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    # Assert
    assert (completed.returncode, "claims: 3" in completed.stdout) == (0, True)
