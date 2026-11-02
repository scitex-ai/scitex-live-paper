"""Execute the browser URL resolver with Node's real URL implementation."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

NODE = shutil.which("node")
MODULE = (
    Path(__file__).resolve().parents[2]
    / "src/scitex_live_paper/_django/static/live_paper/js/_utils.js"
)
SCRIPT = """
import fs from 'node:fs';
const source = fs.readFileSync(process.argv[1], 'utf8');
const {withBundleContext} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const [url, page] = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(withBundleContext(url, page)));
"""


@pytest.mark.skipif(
    NODE is None, reason="Node.js is needed to execute the real browser helper"
)
@pytest.mark.parametrize(
    "url,page,expected",
    [
        (
            "/apps/live-paper/api/ping",
            "https://dev.example/apps/live-paper/?project=owner/mnist&working_dir=/home/owner/demo",
            "https://dev.example/apps/live-paper/api/ping?project=owner%2Fmnist&working_dir=%2Fhome%2Fowner%2Fdemo",
        ),
        (
            "/apps/live-paper/api/pdf?doc_type=manuscript&t=1",
            "https://dev.example/apps/live-paper/?working_dir=/demo",
            "https://dev.example/apps/live-paper/api/pdf?doc_type=manuscript&t=1&working_dir=%2Fdemo",
        ),
        (
            "/apps/live-paper/api/comments?working_dir=/explicit",
            "https://dev.example/apps/live-paper/?working_dir=/other&project=owner/mnist",
            "https://dev.example/apps/live-paper/api/comments?working_dir=%2Fexplicit&project=owner%2Fmnist",
        ),
        (
            "/api/comments",
            "https://dev.example/?embed=1&token=private&project=owner/mnist",
            "https://dev.example/api/comments?project=owner%2Fmnist",
        ),
        (
            "https://other.example/api/ping",
            "https://dev.example/?working_dir=/private/path",
            "https://other.example/api/ping",
        ),
        ("/api/ping", "https://dev.example/", "https://dev.example/api/ping"),
    ],
)
def test_browser_requests_preserve_explicit_bundle(url, page, expected):
    # Arrange
    command = [
        NODE,
        "--input-type=module",
        "-e",
        SCRIPT,
        str(MODULE),
        json.dumps([url, page]),
    ]
    # Act
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=10, check=True
    )
    # Assert
    assert json.loads(completed.stdout) == expected
