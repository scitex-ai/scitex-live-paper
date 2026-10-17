"""Entry-point discovery for the distribution half of §5.

Core ships the mechanism (:class:`Registry`); third-party renderer
packages publish under the ``scitex.livepaper.renderers`` group and
:func:`discover` loads them lazily (stdlib ``importlib.metadata``
only — no packaging dependency in core). Each entry point's loaded
object must expose ``port`` (one of the §2 names) and the adapter
itself; optional ``name`` keys multiple adapters per port.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, List, Tuple


#: Distribution group for third-party renderer adapters.
ENTRY_POINT_GROUP = "scitex.livepaper.renderers"


def discover(group: str = ENTRY_POINT_GROUP) -> List[Tuple[str, str, Any]]:
    """Load every entry point in ``group`` into ``[(port, name, adapter)]``.

    Entry-point contract: the loaded object exposes ``port`` (a §2
    port name) and ``adapter`` (the port implementation); ``name``
    is optional (default ``"default"``). Malformed entries raise
    ``ValueError`` — a broken install must shout, not vanish.
    """
    found: List[Tuple[str, str, Any]] = []
    for point in entry_points(group=group):
        loaded = point.load()
        try:
            port = loaded.port  # type: ignore[attr-defined]
            adapter = loaded.adapter  # type: ignore[attr-defined]
        except AttributeError as exc:
            raise ValueError(
                f"entry point {point.name!r} in group {group!r} must expose "
                f"`port` + `adapter`, got {type(loaded).__name__}"
            ) from exc
        name = getattr(loaded, "name", "default")
        found.append((port, name, adapter))
    return found
