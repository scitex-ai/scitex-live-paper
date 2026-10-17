"""In-process port-to-adapter registry (the injection mechanism).

One :class:`Registry` per serve/render call — never global state, so
the standalone server, the test suite, and a multi-paper hub mount
cannot leak adapters into each other. Duplicate registration FAILS
LOUD (``KeyError``): two adapters fighting over one port name is a
packaging bug, not a tie to break silently.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .protocols import PORT_NAMES


class PortNotFound(KeyError):
    """No adapter registered for this (port, name) pair."""


class Registry:
    """Map ``(port, name)`` to adapter. ``name`` defaults to ``"default"``."""

    def __init__(self) -> None:
        self._adapters: Dict[Tuple[str, str], Any] = {}

    def register(self, port: str, adapter: Any, *, name: str = "default") -> None:
        """Bind one adapter. Unknown port or duplicate name raises ``KeyError``."""
        if port not in PORT_NAMES:
            raise KeyError(
                f"unknown port {port!r}; expected one of {list(PORT_NAMES)}"
            )
        key = (port, name)
        if key in self._adapters:
            raise KeyError(f"duplicate adapter for port {port!r} name {name!r}")
        self._adapters[key] = adapter

    def resolve(self, port: str, *, name: str = "default") -> Any:
        """Return the adapter. Missing raises :class:`PortNotFound` (a ``KeyError``)."""
        try:
            return self._adapters[(port, name)]
        except KeyError:
            raise PortNotFound(
                f"no adapter for port {port!r} name {name!r}"
            ) from None

    @property
    def ports(self) -> Tuple[str, ...]:
        """Port names with at least one adapter registered."""
        return tuple(sorted({port for port, _ in self._adapters}))
