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

The authorized dispatcher also serves `paper.html`, `graph.html?claim_id=…`,
`review.json`, `review.txt` and installed-only assets. A host may set
`BundleContext.evidence_report` to a neutral report snapshot and
`resource_root` to an already authorized absolute directory. Otherwise the
report is `evidence-report.json` inside the bundle, and text is rooted at the
bundle directory. The report's `project_root` is never storage authority.
Absolute text paths must stay inside the authorized root; traversal, symlinks
and special files are refused. Every page/resource retains host selectors and
passes through the same resolver. GETs never invoke an evidence provider or
modify the snapshot/manuscript. Missing reports are not silently synthesized.

The Django settings `SCITEX_LIVE_PAPER_MAX_REPORT_BYTES` and
`SCITEX_LIVE_PAPER_MAX_TEXT_BYTES` default to 16 MiB per report and 4 MiB of
manuscript text per request. Responses are private/no-store; pages permit only
same-origin scripts. Verify graph interactions and cross-project refusals in
the actual deployed browser before treating a host integration as accepted.

Claim anchors use PDF-space page/bbox data. Figure evidence resolves through
the figure port; snippets/claim graphs need adapters supplied by the consumer.
Anchored comments use claim, page-region or quote targets and persist in
`live-paper-comments.json` beside the bundle. The archive action persists an
event-log sidecar. Test these writes with an isolated bundle copy, preserving
existing manuscripts, comments and provenance.

Verify actual PDF pages, overlays, header placement, and an anchored-comment
round trip in the deployed browser. Unit tests and provider availability do
not establish that Writer or Journal has adopted this viewer. Re-verify controls
may report fallback (`unassessed`) results when no evidence provider is installed; do not call that a real
scientific verification.
