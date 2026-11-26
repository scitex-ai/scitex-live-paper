"""Reader-facing text for claim values, and how a stated value relates to its source.

Two display rules shared by every page (paper text, evidence panel, graph
page, claims list):

* :func:`display_value` renders a stated value the way a manuscript states
  it. A multi-value claim (for example ``{"n": 51, "N": 51}``) shows the
  claim's own stated text when that text carries every value, otherwise a
  count pair as ``51/51`` and anything else as ``key = value`` pairs. It
  never returns a Python or JSON repr.
* :func:`compare_values` says whether the source value matches the stated
  value after normalising types (the number ``476`` and the string
  ``"476"`` are the same value) and the stated precision (``0.99`` states
  ``0.9907`` to two decimals). When they still differ, a ``supported``
  verdict means the evidence provider accepted the value within its own
  tolerance; the renderer reports that instead of contradicting the
  provider.

Display only: nothing here changes a claim's state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

__all__ = ["compare_values", "display_value", "value_presentation"]

#: Key pairs (case-sensitive) that state a count out of a total: ``a/b``.
_FRACTION_KEYS = (
    ("n", "N"),
    ("k", "n"),
    ("numerator", "denominator"),
    ("count", "total"),
)


def _unwrap(value: Any) -> Any:
    if isinstance(value, Mapping) and set(value) == {"value"}:
        return value["value"]
    return value


def _scalar_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    if isinstance(value, (str, int, float)):
        return str(value)
    return display_value(value) or ""


def display_value(value: Any, stated_text: str | None = None) -> str | None:
    """The stated *value* as reader text; ``None`` when there is no value."""
    value = _unwrap(value)
    if value is None:
        return None
    if isinstance(value, Mapping):
        if not value:
            return None
        parts = [_scalar_text(v) for v in value.values()]
        if stated_text and all(p and p in stated_text for p in parts):
            return stated_text.strip()
        for top, bottom in _FRACTION_KEYS:
            if set(value) == {top, bottom}:
                return f"{_scalar_text(value[top])}/{_scalar_text(value[bottom])}"
        return ", ".join(f"{k} = {_scalar_text(v)}" for k, v in value.items())
    if isinstance(value, Sequence) and not isinstance(value, str):
        return ", ".join(_scalar_text(v) for v in value)
    return _scalar_text(value)


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        text = repr(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
    else:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _relation(stated: Any, source: Any) -> str:
    """``equal``, ``rounded`` (equal at the stated precision) or ``differs``."""
    stated, source = _unwrap(stated), _unwrap(source)
    if isinstance(stated, Mapping) or isinstance(source, Mapping):
        if not (isinstance(stated, Mapping) and isinstance(source, Mapping)):
            return "differs"
        if set(stated) != set(source):
            return "differs"
        parts = [_relation(stated[k], source[k]) for k in stated]
        return _worst(parts)
    if isinstance(stated, list) or isinstance(source, list):
        if not (isinstance(stated, list) and isinstance(source, list)):
            return "differs"
        if len(stated) != len(source):
            return "differs"
        return _worst([_relation(a, b) for a, b in zip(stated, source)])
    if isinstance(stated, bool) or isinstance(source, bool):
        return "equal" if stated is source else "differs"
    a, b = _decimal(stated), _decimal(source)
    if a is not None and b is not None:
        if a == b:
            return "equal"
        places = -a.as_tuple().exponent if a.as_tuple().exponent < 0 else 0
        quantum = Decimal(1).scaleb(-places)
        return "rounded" if b.quantize(quantum) == a.quantize(quantum) else "differs"
    if isinstance(stated, str) and isinstance(source, str):
        return "equal" if stated.strip() == source.strip() else "differs"
    return "equal" if stated == source else "differs"


def _worst(parts: list[str]) -> str:
    for rel in ("differs", "rounded"):
        if rel in parts:
            return rel
    return "equal"


def compare_values(
    stated: Any, source: Any, *, state: str | None = None
) -> dict[str, str]:
    """How the *source* value relates to the *stated* one, for display.

    Returns ``{"relation", "symbol", "text"}`` where relation is one of
    ``equal``, ``rounded``, ``provider_tolerance`` or ``differs``.
    """
    rel = _relation(stated, source)
    if rel == "differs" and state == "supported":
        rel = "provider_tolerance"
    return {
        "relation": rel,
        "symbol": {"equal": "=", "rounded": "≈", "provider_tolerance": "≈"}.get(
            rel, "≠"
        ),
        "text": {
            "equal": "matches the stated value",
            "rounded": "matches the stated value at its stated precision",
            "provider_tolerance": "accepted by the evidence provider within its tolerance",
            "differs": "differs from the stated value",
        }[rel],
    }


def value_presentation(entry: Mapping[str, Any]) -> dict[str, Any]:
    """``stated_display`` and ``value_check`` for one packet entry."""
    src = entry.get("source") or {}
    stated = entry.get("stated_value")
    check = None
    if src.get("value_reported") and stated is not None:
        check = compare_values(stated, src.get("value"), state=entry.get("state"))
    return {
        "stated_display": display_value(stated, entry.get("stated_text")),
        "value_check": check,
    }
