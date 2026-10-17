"""In-process event bus (Python side of the contract §3 envelope).

Kinds: ``evidence-request``, ``evidence-response``,
``figure-refresh``, ``bundle-reloaded``. The DOM side mirrors these
as ``CustomEvent("live-paper:<kind>", {detail})`` on
``#live-paper-root``.

Fail loud: a subscriber that raises propagates through :meth:`emit`
(the bus never swallows adapter errors), and :meth:`emit` returns
the subscriber count so dispatchers can 404 unhandled
``evidence-request``s instead of rendering empty popups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping


@dataclass(frozen=True)
class Event:
    """One bus message. ``payload`` is JSON-plain."""

    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)


EventHandler = Callable[[Event], None]


class EventBus:
    """Synchronous fan-out. One bus per serve/render — never global."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, kind: str, fn: EventHandler) -> Callable[[], None]:
        """Add a subscriber; returns an ``unsubscribe()`` callable."""
        self._subscribers.setdefault(kind, []).append(fn)

        def unsubscribe() -> None:
            self._subscribers[kind].remove(fn)

        return unsubscribe

    def emit(self, kind: str, payload: Mapping[str, Any] | None = None) -> int:
        """Fan out to every subscriber, in order. Returns the count reached."""
        event = Event(kind=kind, payload=dict(payload or {}))
        subscribers = list(self._subscribers.get(kind, []))
        for fn in subscribers:
            fn(event)
        return len(subscribers)
