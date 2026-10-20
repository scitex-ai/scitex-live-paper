"""``_django/_server.serve`` — env-pinning + bad-bundle paths + SDK delegation.

All collaborators are real. The SDK ``run_standalone`` launcher is
reached through the module attribute (read at call time), so the
delegation tests swap in a real spy function with try/finally
restoration — the same no-mocks, real-state discipline as the
``env_snapshot`` fixture (not ``monkeypatch``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("django")

from scitex_live_paper._django import _server as server_module  # noqa: E402


# ──────────────────────────────────────────────────────────────────
# Fixtures (no monkeypatch — pure stdlib + try/finally restoration)
# ──────────────────────────────────────────────────────────────────


@pytest.fixture
def env_snapshot() -> Iterator[None]:
    """Snapshot ``os.environ``, yield, restore on teardown.

    Real process state — the tests below mutate the actual environment
    just like a user invocation would; this fixture is responsible for
    putting it back after the test.
    """
    snapshot = dict(os.environ)
    try:
        yield
    finally:
        # Drop keys the test added.
        for key in list(os.environ):
            if key not in snapshot:
                del os.environ[key]
        # Restore mutated values.
        for key, value in snapshot.items():
            os.environ[key] = value


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    """Real on-disk empty bundle directory (no claims required for serve())."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    return bundle


class _LauncherSpy:
    """Real callable that records its invocations.

    Stands in for the SDK ``run_standalone`` launcher via module-attribute
    swap — a real Python function, not a mock.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))


def _swap_launcher(spy: _LauncherSpy) -> tuple[object, object]:
    """Swap the SDK sentinels for test doubles; return pair to restore."""
    previous_run = server_module.run_standalone
    previous_hosts = server_module.hosts_to_allow
    server_module.run_standalone = spy  # type: ignore[method-assign]
    server_module.hosts_to_allow = lambda host: []  # type: ignore[method-assign]
    return previous_run, previous_hosts


def _restore_launcher(previous: tuple[object, object]) -> None:
    server_module.run_standalone, server_module.hosts_to_allow = previous  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────
# Bad-bundle paths — pre-launcher, no SDK needed
# ──────────────────────────────────────────────────────────────────


def test_serve_raises_filenotfounderror_for_missing_path(tmp_path):
    # Arrange
    missing = tmp_path / "does-not-exist"
    # Act
    # Assert
    with pytest.raises(FileNotFoundError, match="bundle path is not a directory"):
        server_module.serve(missing)


def test_serve_raises_filenotfounderror_for_file_path(tmp_path):
    # Arrange
    a_file = tmp_path / "manuscript.pdf"
    # Act
    a_file.write_text("not-a-dir", encoding="utf-8")
    # Assert
    with pytest.raises(FileNotFoundError, match="bundle path is not a directory"):
        server_module.serve(a_file)


def test_serve_refuses_without_sdk(bundle_dir, env_snapshot):
    # Arrange — SDK sentinels absent (broken/partial install)
    previous = _swap_launcher(_LauncherSpy())
    server_module.run_standalone = None
    server_module.hosts_to_allow = None
    try:
        # Act
        # Assert — loud refusal naming the extra
        with pytest.raises(ImportError, match="scitex-live-paper\\[server\\]"):
            server_module.serve(bundle_dir)
    finally:
        _restore_launcher(previous)


def test_serve_refusal_leaves_env_untouched(bundle_dir, env_snapshot):
    # Arrange — SDK sentinels absent (broken/partial install)
    previous = _swap_launcher(_LauncherSpy())
    server_module.run_standalone = None
    server_module.hosts_to_allow = None
    try:
        # Act — refusal fires before the env pin
        try:
            server_module.serve(bundle_dir)
        except ImportError:
            pass
        # Assert — no bundle pin leaked into the environment
        assert "SCITEX_LIVE_PAPER_BUNDLE" not in os.environ
    finally:
        _restore_launcher(previous)


# ──────────────────────────────────────────────────────────────────
# Bundle env pin — real env state, launcher swapped
# ──────────────────────────────────────────────────────────────────


def test_serve_pins_bundle_env_to_resolved_path(bundle_dir, env_snapshot):
    # arrange
    os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
    previous = _swap_launcher(_LauncherSpy())
    try:
        # act
        server_module.serve(bundle_dir)
        # assert — env carries the *resolved* absolute path
        assert os.environ["SCITEX_LIVE_PAPER_BUNDLE"] == str(bundle_dir.resolve())
    finally:
        _restore_launcher(previous)


# ──────────────────────────────────────────────────────────────────
# SDK launcher delegation — real spy via module-attribute swap
# ──────────────────────────────────────────────────────────────────


def test_serve_delegates_to_sdk_launcher_once(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir)
        # assert
        assert len(spy.calls) == 1
    finally:
        _restore_launcher(previous)


def test_serve_passes_app_module(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir, host="0.0.0.0", port=9100)
        # assert
        (_args, kwargs) = spy.calls[0]
        assert kwargs["app_module"] == "scitex_live_paper._django"
    finally:
        _restore_launcher(previous)


def test_serve_passes_explicit_host(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir, host="0.0.0.0", port=9100)
        # assert
        (_args, kwargs) = spy.calls[0]
        assert kwargs["host"] == "0.0.0.0"
    finally:
        _restore_launcher(previous)


def test_serve_passes_explicit_port(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir, host="0.0.0.0", port=9100)
        # assert
        (_args, kwargs) = spy.calls[0]
        assert kwargs["port"] == 9100
    finally:
        _restore_launcher(previous)


def test_serve_default_host_is_loopback(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir)
        # assert
        (_args, kwargs) = spy.calls[0]
        assert kwargs["host"] == "127.0.0.1"
    finally:
        _restore_launcher(previous)


def test_serve_default_port(bundle_dir, env_snapshot):
    # arrange
    spy = _LauncherSpy()
    previous = _swap_launcher(spy)
    try:
        # act
        server_module.serve(bundle_dir)
        # assert
        (_args, kwargs) = spy.calls[0]
        assert kwargs["port"] == 8765
    finally:
        _restore_launcher(previous)


# ──────────────────────────────────────────────────────────────────
# Path-input flexibility — str + Path + relative components
# ──────────────────────────────────────────────────────────────────


def test_serve_resolves_relative_path_components__assert_pinned_str_path_raw_resol(bundle_dir, env_snapshot):
    # Arrange
    raw = f"{bundle_dir}/."
    previous = _swap_launcher(_LauncherSpy())
    try:
        # Act
        server_module.serve(raw)
        pinned = os.environ["SCITEX_LIVE_PAPER_BUNDLE"]
        # Assert
        assert pinned == str(Path(raw).resolve())
    finally:
        _restore_launcher(previous)


def test_serve_resolves_relative_path_components__assert_not_pinned_endswith(bundle_dir, env_snapshot):
    # Arrange
    raw = f"{bundle_dir}/."
    previous = _swap_launcher(_LauncherSpy())
    try:
        # Act
        server_module.serve(raw)
        pinned = os.environ["SCITEX_LIVE_PAPER_BUNDLE"]
        # Assert
        assert not pinned.endswith("/.")
    finally:
        _restore_launcher(previous)


def test_serve_accepts_pathlib_path(bundle_dir, env_snapshot):
    # arrange
    previous = _swap_launcher(_LauncherSpy())
    try:
        # act
        server_module.serve(Path(bundle_dir))
        # assert
        assert os.environ["SCITEX_LIVE_PAPER_BUNDLE"] == str(bundle_dir.resolve())
    finally:
        _restore_launcher(previous)


def test_serve_resolves_str_input_same_as_path_input(bundle_dir, env_snapshot):
    # arrange
    previous = _swap_launcher(_LauncherSpy())
    try:
        # act
        server_module.serve(str(bundle_dir))
        # assert
        assert os.environ["SCITEX_LIVE_PAPER_BUNDLE"] == str(bundle_dir.resolve())
    finally:
        _restore_launcher(previous)
