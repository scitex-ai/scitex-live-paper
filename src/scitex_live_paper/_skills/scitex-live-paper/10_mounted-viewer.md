---
description: |
  [TOPIC] Mounted viewer and evidence ports
  [DETAILS] Source-backed LivePaper mounted viewer and evidence ports.
tags: [scitex-live-paper-mounted-viewer]
---

# Mounted viewer and evidence ports

The host supplies `mount(resolver=...)`. The resolver authorizes the current
request and returns a `BundleContext` for its allowed bundle directory; API
requests need the same authorization as the page. Use a canonical API prefix
ending in `/api/` (for example `/apps/live-paper/api/`). A full app page uses
`RendererOptions(embed_mode=False)`; an iframe can explicitly request embed
mode. The full viewer owns one canonical SDK header with its project picker.

From 0.2.18 the browser preserves explicit `project`/`working_dir` selectors
on same-origin API and PDF requests, preserving each tab's bundle selection.
These selectors never grant access. The host must still check project access
and containment, including symlinked resources, on every request.

Claim anchors use PDF-space page/bbox data. Figure evidence resolves through
the figure port; snippets/claim graphs need adapters supplied by the consumer.
Anchored comments use claim, page-region or quote targets and persist in
`live-paper-comments.json` beside the bundle. The archive action persists an
event-log sidecar. Test these writes with an isolated bundle copy, preserving
existing manuscripts, comments and provenance.

Verify actual PDF pages, overlays, header placement, and an anchored-comment
round trip in the deployed browser. Unit tests and provider availability do
not establish that Writer or Journal has adopted this viewer. Re-verify controls
may report fallback results when Clew is unavailable; do not call that a real
scientific verification.
