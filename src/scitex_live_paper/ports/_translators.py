"""Thin translator layer for consumer payloads (prompt-10 item 6).

Consumers (scitex-writer, scitex-agentic-journal) inject information in
THEIR format; the leaf never imports them. This module is the intake
normalizer: it accepts tolerant consumer shapes and returns the
canonical live-paper action — a comment for ``api/comments``, or a
port call for ``api/port/<port>/<target>``.

Accepted input (mapping; keys are case-sensitive):

- Comment (→ ``api/comments`` POST body)::

      {"body": "...", "target": {"claim_id": "..."}}
      {"text": "...", "target": {"page": 3, "bbox": [x0, y0, x1, y1]},
       "author": "...", "kind": "..."}

  ``body`` also accepts the aliases ``text`` / ``content``.
  Target accepts ``claim_id`` | ``page``+``bbox`` | ``quote`` (same
  shapes as :func:`handlers.comments.validate_comment`).

- Port call (→ ``api/port/...``)::

      {"port": "figure", "target": "fig-demo-1", "options": {...}}
      {"figure_id": "fig-demo-1"}      # alias for the figure port
      {"ref": "snippet-id"}            # alias for the snippet port
      {"claim_id": "..."}              # alias for the claim-graph port

Returns ``(action, None)`` where ``action`` is
``{"kind": "comment", "comment": {...}}`` or
``{"kind": "port", "port": ..., "target": ..., "options": {...}}``;
or ``(None, error_message)`` for anything unrecognizable. Pure
function — no Django, no I/O — so hosts and tests call it directly.
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["translate_consumer_payload"]

_COMMENT_BODY_KEYS = ("body", "text", "content")
_PORT_ALIASES = {
    "figure_id": "figure",
    "fig_id": "figure",
    "figure": "figure",
    "ref": "snippet",
    "snippet": "snippet",
}


def translate_consumer_payload(
    payload: Any,
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Normalize one consumer payload into a canonical live-paper action."""
    if not isinstance(payload, Mapping):
        return None, "payload must be a JSON object"
    target = payload.get("target")

    # Explicit port call: {"port": "figure", "target": ..., "options": {...}}.
    port = payload.get("port")
    if isinstance(port, str) and port:
        if port not in ("figure", "snippet", "claim-graph"):
            return None, f"unknown port {port!r}"
        if not isinstance(target, str) or not target.strip():
            return None, "'target' must be a non-empty string for port calls"
        options = payload.get("options", {})
        if not isinstance(options, Mapping):
            return None, "'options' must be a JSON object when present"
        return (
            {
                "kind": "port",
                "port": port,
                "target": target.strip(),
                "options": dict(options),
            },
            None,
        )

    # Port aliases: {"figure_id": ...} / {"ref": ...} / {"claim_id": ...}.
    for alias, aliased_port in _PORT_ALIASES.items():
        if isinstance(payload.get(alias), str) and payload[alias].strip():
            return (
                {
                    "kind": "port",
                    "port": aliased_port,
                    "target": payload[alias].strip(),
                    "options": {},
                },
                None,
            )
    if isinstance(payload.get("claim_id"), str) and payload["claim_id"].strip():
        # A bare claim reference with no body is a claim-graph lookup,
        # NOT a comment — commenting needs words.
        if not any(
            isinstance(payload.get(k), str) and payload[k].strip()
            for k in _COMMENT_BODY_KEYS
        ):
            return (
                {
                    "kind": "port",
                    "port": "claim-graph",
                    "target": payload["claim_id"].strip(),
                    "options": {},
                },
                None,
            )

    # Comment: needs a body plus a target anchor.
    body: str | None = None
    for key in _COMMENT_BODY_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            body = value.strip()
            break
    if body is None:
        return None, "unrecognizable payload: need a comment body or a port/alias target"
    if not isinstance(target, Mapping):
        return None, "'target' must be a JSON object for comments"
    comment: dict[str, Any] = {"body": body, "target": dict(target)}
    for key in ("author", "kind"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            comment[key] = value.strip()
    return ({"kind": "comment", "comment": comment}, None)
