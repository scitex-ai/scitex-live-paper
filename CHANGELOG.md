# Changelog

All notable changes to `scitex-live-paper` are documented in this file.

The format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
SemVer applies *across releases*; pre-1.0 minor bumps may include
breaking changes for consumers that pin only on `==<major>` but
will not break **the documented public surface** without a note here.

The documented public surface is everything importable from
`scitex_live_paper` (the top-level package), the CLI
(`render` / `serve` / `info` / `validate`), and the Django mount
URL patterns / `bundle-info` JSON shape. Internal modules
(`_django` internals, `_renderer` internals, `_types` internals)
may change without a changelog entry.

## [Unreleased]

- Evidence report contract 1.3.0 (additive): `project_root` is deprecated and providers
  should omit it; optional `project_name` (a name, never a path) and `external` on
  `location` / `source`; paths, including those inside `details`, are project-relative,
  and paths outside the root stay absolute. 1.2.x reports are still accepted.
- Review packet 1.4.0 carries `project_name` and `location.external` / `source.external`;
  `project_root` is null when the report omits it.
- `render --evidence-root` now also roots the manuscript text, so a report without
  `project_root` still renders `paper.html` (`render_evidence_pages(text_root=...)`).
- Read an optional `self-proof.json` reproduction receipt from a bundle (`Bundle.self_proof`;
  review packet 1.3.0 `self_proof`) and show it as one line under the claim summary in the PDF
  reader and the evidence view; a FAIL verdict is shown as a warning with the first failure.
- Compare a stated value with its source value after normalising types and the stated
  precision (476 and "476" match); a supported claim never shows "differs".
- Show multi-value claims as the manuscript states them (51/51), never as a dict, in the
  paper text, the evidence panel, the graph page and the claims list.
- Render common inline LaTeX in the reader view (arrows, %, thin spaces, dashes, emphasis,
  bold, refs as links; environments, labels and bookmarks hidden); the source toggle still
  shows the original text.
- Draw a wide minimal evidence graph left-to-right in the evidence panel instead of a thin strip.

## [0.5.4] - 2026-11-22

- Show revision-bound PDF highlights, claim graphs, and local previews of recorded files.
- Expose per-claim HTTP evidence and deterministic Python previews for archives and IDX windows.
- Provide a raw PDF download and a review summary linked to the versioned review packet.

## [0.5.3] - 2026-11-20

- Use the released Rich PDF provider for the native synchronized claims feed. Preserve Writer’s existing frontend exports.
- Include the shared paper workflow architecture and hosted documentation updates.

## [0.5.2] - 2026-11-20

### Added

- Serve `paper.html`, per-claim `graph.html`, `review.json`, `review.txt` and
  their installed assets through the same authorized Django mount as the viewer.
  Hosts may bind a neutral evidence snapshot and an authorized resource root;
  standalone bundles may supply `evidence-report.json`. Every link retains host
  selectors. Reads refuse traversal, symlinks, non-regular and oversized files;
  report metadata never selects a filesystem root. Viewer shells link to the
  manuscript when a report is present. These GETs never rerun a provider.

### Fixed

- Require SDK 0.3.25 for the corrected explicit standalone project picker and
  registered host API identity behavior.
- Include the renderer templates/assets, Django templates/plugin manifest,
  vendored Mermaid and PDF.js resources in both sdist and wheel. Source-tree
  availability no longer conceals missing resources in installed packages.
  CI builds real archives and compares every owned non-Python resource byte.
- Pin release promotion to the already qualified immutable workflow revision
  that uses ordinary expected-head merges and retains its CI gate.
- Enable HTML escaping for the actual `.html.j2` renderer templates, including
  report metadata. Draw standalone graphs with Mermaid's strict security mode;
  mounted pages use private responses and a restrictive content security policy.

## [0.5.1] - 2026-11-20

### Fixed

- Display a registered manuscript claim's stated value in place of its
  `\vclaim{...}` macro, with the highlight confined to that value. Single-value
  wrappers display as numbers in both the manuscript and its evidence panel.
  Unsupported claims retain their stated value and verdict; unregistered text
  remains unassessed.

### Added

- **Review-packet JSON Schema.** `evidence/review-packet.schema.json`
  (`$id` `https://scitex.ai/schemas/scitex-live-paper/review-packet/1.2.0`,
  draft 2020-12, self-contained) publishes the `scitex-live-paper.review-packet`
  contract that was defined only in code. Shipped in the wheel next to
  `evidence-report.schema.json`; tests validate real reference-provider
  packets (built, rendered `review.json`, no embedded graphs) against it.
  `jsonschema` joins the `test` extra.

## [0.5.0]

### Added

- **Navigate the paper through its claims (`paper.html`).** Selecting a
  registered claim's mark (click, tap, or Enter) opens an in-page
  **evidence panel** instead of leaving the paper: state and reason, stated
  vs source value, source and locator, provider verdict, where the evidence
  broke, and the claim's **minimal evidence graph drawn inline** (the graph
  page's own mermaid source, top-down; failing nodes keep the dash-dot
  outline and `⚠ KIND` line). Selecting a graph node (click, Enter, Space,
  or the node list beside it) shows its file, hash, run, and failure mark.
  The panel steps to the previous/next claim (reading order) or the next
  claim needing inspection (inspection order), opens the source node's
  details, and links to the full graph page.
- **Claims navigator** on `paper.html`, needs inspection first: scrolls to
  the claim, highlights it (black outline, not a hue), and opens its panel.
- **Deep links and history**: `paper.html#claim-<id>` opens that claim's
  panel on load; every claim opened is a history entry, so back/forward
  step through them. The graph pages' "Show in paper" link uses it.
- Accessibility: a non-modal `role="dialog"` panel, focus moves into it and
  returns to the claim on Esc/close, keyboard-operable graph nodes plus an
  equivalent node list, state never by colour alone, 44px touch targets,
  bottom-sheet layout on narrow screens, reduced-motion respected.
- Static-site friendly: classic scripts (`assets/paper-panel.js`,
  `assets/paper.js`, `assets/paper.css`) and the claims data embedded in the
  page, so it works from `file://`; without JavaScript every mark still
  links to its graph page and every navigator entry to its mark.
- **Evidence contract 1.2.0**: optional `source.value`, the value the
  provider read at the locator (backwards compatible: 1.0/1.1 reports stay
  valid). Review packet 1.2.0 adds `source.value` + `source.value_reported`;
  the panel and graph page show stated vs source value and say in words when
  they differ; `review.txt` prints both.
- CI: a `browser (chromium, py3.12)` leg runs the Playwright navigation tests
  with `LP_REQUIRE_BROWSER=1` (a missing browser fails instead of skipping)
  and uploads screenshots. Locally the tests skip cleanly without Playwright
  or Chromium; `LP_SCREENSHOT_DIR` saves screenshots.

### Changed

- The `render` / `export-review` CLI is unchanged (no new options);
  `paper.html` gains the panel and navigator automatically when evidence is
  given. The embedded data comes from
  `scitex_live_paper._renderer.paper.claims_data` (internal module).

## [0.4.0]

### Added

- **Evidence contract 1.1.0: where the evidence broke.** A provider may
  mark graph nodes with an optional `failure: {kind, detail}`
  (`changed` / `missing` / `mismatched`, any other token shown verbatim).
  Backwards compatible: every 1.0.0 report is a valid 1.1.0 report. The
  claim graph page draws failing nodes with a dash-dot vermillion outline
  and a `⚠ KIND` label (never colour alone), lists them above the graph,
  and the node overlay says "Evidence broke here". The review packet
  (now 1.1.0) adds `failing_nodes` per claim; `review.txt` prints
  `evidence broke at:` lines and tags failing nodes in edge lists.

### Changed

- Docs (`dev-quickstart.md` bundle-ownership table,
  `dev/ports-events-contract.md`, `dev/api-consistency.md`,
  `demo/README.md`) name the bundle producer neutrally instead of a
  specific provider package.

## [0.3.0]

### Added

- **Evidence-provider contract** (`scitex_live_paper.evidence`,
  `docs/evidence-provider-contract.md`). An evidence report
  (`scitex-live-paper.evidence-report` v1.0.0, JSON Schema shipped as
  `evidence/evidence-report.schema.json`) gives each **registered** claim one
  of four neutral states: supported, not supported, registered but not
  checkable, or no evidence graph. Each claim also gets a plain-language
  reason, its source and locator, and its minimal evidence graph
  (nodes/edges). Providers connect through the existing ports seam
  (`scitex.livepaper.renderers` entry point, new port `evidence`,
  `EvidencePort`) or through a report file. Text that is not a registered
  claim is never marked.
- Reviewer view: `paper.html` marks each registered claim in the manuscript
  with a colour-blind-safe highlight. States also differ by underline style
  and symbol. Hovering a mark shows its reason, and clicking opens the
  claim's minimal-graph page (`claim-graph-*.html`). `claims.html` now opens
  with a **Needs inspection** list (not supported, then not checkable, then
  no evidence graph), followed by the supported claims.
- Machine adapter: `review.json` / `review.txt` in the site, the
  `export-review` CLI command, and the MCP tools `live_paper_evidence_review`
  and `live_paper_evidence_claim`. All serve the same review packet
  (`scitex-live-paper.review-packet` v1.0.0), and the human pages are rendered
  from it, so the two cannot disagree.
- `render --evidence-report / --evidence-provider / --evidence-root`.

### Changed

- live-paper is provider-neutral. It no longer imports any evidence provider
  and has no extra for one. The Django re-verify endpoints
  (`api/claim/verify`, `api/claims/verify`) now ask the configured evidence
  provider (`SCITEX_LIVE_PAPER_EVIDENCE_PROVIDER`,
  `SCITEX_LIVE_PAPER_EVIDENCE_ROOT`) and return its evidence state as
  `status`. With no provider installed they degrade to `unassessed`
  (fallback).

### Removed

- The provider-specific optional extra.

## [0.2.21]

### Fixed

- Declare the canonical SDK base dependency for static AppHeader assets instead
  of installing the retired `scitex-ui` distribution. Django remains optional;
  the server extra uses the same qualified SDK>=0.3.22 runtime minimum.
- Synchronize the Python, frontend package and Django manifest release versions.
  The frontend rich-PDF protocol and existing SDK>=0.3.17 peer contract are unchanged.

## [0.2.20]

### Added

- Public rich-PDF document, overlay, comment, mutation, policy and event ports,
  with typed frontend exports and a wheel-contained package discovery helper.
- Native viewer adapter using the SDK renderer for raster, selectable text and
  links. Consumers supply their own authorized application adapters.
- Reproducible frontend builds from the installed SDK package; server and
  frontend integrations require SDK>=0.3.17.

### Fixed

- Enforce CSRF for native comment creation using the page DOM token, including
  HttpOnly-cookie and session-backed CSRF configurations.
- Return explicit missing-bundle404 responses and a clear native empty state;
  malformed existing bundle content remains an error.
- Keep full/embed authorized request-local project views consistent without
  treating a raw query alias as header selection or remembering read navigation.

- Remove the leaf header-border override and use automatic shared asset versions for the header and viewer stylesheet.

- Pin the shared AppHeader script URL to the picker-adoption asset revision so
  an ordinary reload fetches the corrected header startup behavior.

## [0.2.19] - 2026-11-01

### Added

- Bundle source-backed renderer, host-mount, evidence-port and environment skills in the wheel and expose them through the existing MCP skill tools.
- Verify installed skill discovery and retrieval, with the canonical skill audit and real demo render commands.

## [0.2.18] - 2026-11-01

### Fixed

- Preserve explicit project and working-directory selectors on same-origin viewer RPC, PDF, comments, port and archive requests, keeping a bundle link independent of another tab's project selection.

## [0.2.17] - 2026-11-01

### Fixed

- Place the Django project picker in its own canonical SDK header slot instead of searching inside the viewer main.
- Limit header observation to the owning header and skip absent pickers, avoiding unrelated host DOM subscriptions.
- Keep MNIST generator help usable without optional plotting dependencies; align existing regression tests with source filenames and the shared test-quality audit.


## [0.2.16] - 2026-10-24

### Added

- Anchored-comments provider (`GET/POST /api/comments`, sidecar
  persist, overlay markers, badges, detail-pane section) and the
  consumer translator layer (`ports.translate_consumer_payload`).

### Fixed

- Overlay paints before text/annotation layers; MNIST figure axis
  follows the data.

## [0.2.15] - 2026-10-24

### Fixed

- Harness-proof the MNIST generator test: drop ambient `PYTHONPATH`
  for the generator subprocess (agent/harness venvs shadow PIL ABI).

## [0.2.14] - 2026-10-24

### Added

- Static export mounts the canonical SDK AppHeader (header-parity):
  `[data-stx-app-header]` + vendored SDK CSS/JS; new `--project-label`;
  custom header duplicates retired.
- `example-project-mnist` seed bundle: computed MNIST demo for the
  shared example project (writer / live-paper / agentic-journal).

## [0.2.13] - 2026-10-22

### Fixed

- Empty state hides the stale "Loading bundle info…" line (was stuck
  above the guidance); help-text quote closed.

## [0.2.12] - 2026-10-22

### Fixed

- Static M1 viewer: PDF.js URL is module-relative (`./pdfjs/…`, resolved
  against `assets/viewer.js`) — the bare `assets/…` specifier never
  resolved, so the vendored viewer stayed blank over http. Quickstart
  notes the file:// module-script restriction.

## [0.2.11] - 2026-10-22

### Fixed

- Re-verify failure reason surfaces as a hover tooltip on the status
  pill (was console-only), in both single and bulk paths (beta-5).

## [0.2.10] - 2026-10-22

### Added

- PDF anchor click opens the claim detail pane (beta-4): provenance
  + live DAG, the same pane sidebar rows open.

## [0.2.9] - 2026-10-22

### Added

- Claim-anchor overlays paint on the PDF (beta-2): `pickAnchor()` reads
  `claim.anchor` with `claim.extras.anchor` fallback; same for the
  `figure_id` port attrs. Accepted-fixture anchors moved to page 1
  (single-page placeholder PDF).
- Evidence popup bounded by the viewport with scroll + port SVGs
  constrained to the popup box (beta-3).

## [0.2.8] - 2026-10-22

### Added

- Anchored-comments provider (prompt-10 provider item): `GET/POST
  /api/comments` with `live-paper-comments.json` sidecar persist;
  overlay region markers, per-claim count badges, and a list + add
  form in the claim detail pane (`comments.js`).
- Consumer translator layer (`ports.translate_consumer_payload`):
  thin intake normalizing writer/journal-style payloads (comment
  bodies, port aliases, claim refs) into canonical comment / port
  actions. Pure function, pinned by contract tests.
- Static export mounts the canonical SDK AppHeader (operator
  header-parity rule): the four `.j2` pages render
  `[data-stx-app-header]` with the SDK CSS/JS vendored into
  `assets/` (mounts over `http(s)`; `file://` keeps a static
  fallback title line). New `--project-label` on `render` feeds the
  header's project slot. Custom `<header class="live-paper-header">`
  duplicates retired from templates + CSS. Pins in
  `tests/scitex_live_paper/_renderer/test_sdk_header_parity.py`.
- `example-project-mnist` seed bundle
  (`examples/example-project-mnist/`): computed MNIST demo —
  logistic-regression + kNN test accuracies with claim anchors over
  the accuracy figure, DAG, provenance — for the shared example
  project (writer / live-paper / agentic-journal). Regenerate with
  `examples/make_example_project_mnist.py`. Pins in
  `tests/examples/test_example_project_mnist.py`; quickstart
  documents the Hub `?working_dir=` serving path.
- Leaf API-consistency rules (`docs/dev/api-consistency.md`, R1–R7
  across Python/CLI/MCP/Skills/Web) with §6 MCP↔Python parity pins
  (`tests/scitex_live_paper/test__mcp_server.py`) and docs-sync pins
  (`tests/custom/test_goal_docs_sync.py`).
- Viewer boot chrome (beta-1): rendered bundle header (stage, journal,
  DOI, manuscript, claim count) replaces the raw JSON dump; diagnostics
  collapsed; stale loading label cleared.

### Fixed

- Overlay paints before the text/annotation layers in the PDF viewer:
  a slow figure-page text layer can no longer starve claim anchors
  and comment markers (found live on the MNIST figure page).
- MNIST accuracy figure: axis floor follows the data (was fixed 0.9
  with values below it) and value labels sit above the bars.
- Docs drift: README M3 shipped at `/apps/live-paper/`, `[server]`
  extra + `scitex.livepaper.renderers` group documented;
  quickstart/runbook/demo fixture paths moved to
  `tests/scitex_live_paper/fixtures/`; `_django/` skeleton landed.
- PS-140 cross-package gate: added `scitex_sdk.app`; PS-204 clean.

## [0.2.7] - 2026-10-20

### Added

- Project selector in the canonical AppHeader (stats pattern):
  server-rendered SDK picker (?project= deep link carries current),
  moved into the header slot at boot.

## [0.2.6] - 2026-10-20

### Fixed

- No accent separator under the global header (operator rule):
  neutralise the AppHeader bottom border on the leaf surface.

## [0.2.5] - 2026-10-20

### Fixed

- AppHeader spacing: include the SDK app-header.css so the title
  and version badge render with proper styling instead of jammed
  together (CCT follow-up).

## [0.2.4] - 2026-10-20

### Changed

- Viewer uses the canonical SDK AppHeader (stats pattern) instead of
  its own h1/subtitle block; the shell supplies the official SciTeX
  tab mark (CCT4925).

## [0.2.3] - 2026-10-20

### Changed

- Viewer uses the canonical SDK AppHeader (stats pattern) instead of
  its own h1/subtitle block; leaf AppConfig version shown as badge.

## [0.2.2] - 2026-10-20

### Fixed

- Friendly empty state when no paper is selected: the viewer page
  renders the shell (HTTP 200) with guidance (open from the file
  browser, or `?working_dir=`) instead of a bare-text 404. The API
  keeps the machine-readable 404; access-denied stays 403.

## [0.2.1] - 2026-10-20

### Fixed

- Hub plugin discovery: declare the `scitex.apps` entry point
  (`live-paper = scitex_live_paper._django.apps:LivePaperConfig`)
  so the Hub's generic mount finds the leaf (`mount_route` resolves
  `apps/live-paper/`, login-gated per manifest). Without it
  `loaded_plugin_configs()` never saw the package and the mount
  silently did nothing.

## [0.2.0] - 2026-10-20

Independent GUI app on scitex-sdk: the viewer runs inside the shared
SDK workspace shell and ships as a standalone package that also
provides the `/apps/live-paper/` Hub plugin mount.

### Added

- PDF base layer + event overlay (CCT 3000, binding): claim-anchor
  regions painted over PDF.js pages from anchor bboxes
  (`claim-overlays.js`, zoom-safe repaint); hover/click evidence
  popups over PDF regions via the port bus (`port-events.js`);
  print/export strips the overlay (`@media print`), archive keeps
  PDF + event-log sidecar for replay.
- Archive session persist: POST `api/event-log` validates the
  `scitex-live-paper.event-log/v1` sidecar and stores it verbatim
  as `live-paper-events.json` in the bundle directory; the viewer
  Archive button persists server-side with a client-download
  fallback, so the archive action always produces a sidecar.
- scitex-sdk shell migration: the Django surface runs on
  `scitex-sdk` (`ScitexAppConfig`, shared `standalone_shell`,
  `run_standalone` launcher); new `[server]` extra
  (`django` + `scitex-sdk[gui]>=0.3.7`); `serve`, settings, and
  guards hardened (DEBUG defaults false, ALLOWED_HOSTS switch,
  loud missing-dependency errors, no silent fallbacks).

### Changed

- Hub mount path finalized as `/apps/live-paper/` (manifest, URL
  docs, and mount notes updated from `/viewer-v2/`); host deep-link
  contract is resolver-based via `mount(resolver=...)` — no leaf
  URL-shape change.

## [0.1.1] - 2026-10-19

### Added

- Tile manifest `category` + `accent_color` per hub tile schema (#68).
- Serve-defaults wiring (contract §5): standalone `serve` injects the
  bundled figure-port default with no host code. New
  `LivePaperServeContextMiddleware` (standalone `settings.py` only —
  hub/hosts untouched) attaches the env-pinned `BundleContext` when a
  request has none; `handle_port` registers `FigzFigureAdapter`
  on demand and never overrides an explicit host adapter.

- `api/dag` endpoint + sidebar claim detail/DAG pane (slice C/D):
  the viewer sidebar now opens a per-claim detail pane (status,
  provenance, anchor) with the bundle DAG rendered from the new
  endpoint via the vendored mermaid bundle (offline-safe, MIT).
  Missing `dag.mmd` → JSON 404 and the pane says so.

- Ports/events injection lane (CCT 2998, binding): neutral core with
  external renderers. New `scitex_live_paper.ports` package
  (`protocols` figure/snippet/claim-graph, `Registry`,
  `EventBus`/`Event`, fragment envelopes with mandatory provenance,
  entry-point `discover`, bundled `FigzFigureAdapter` default);
  `api/port/<port>/<target>` dispatch with JSON-404 semantics;
  `port-events.js` DOM bus (`live-paper:*` custom events + popup
  renderer); contract doc at `docs/dev/ports-events-contract.md`.
  Hosts inject via resolver-built `BundleContext(renderers=...)`;
  the core never imports a renderer.

- Monday looks-only viewer mock (`docs/demo/monday-mock.html`): a
  single-file, zero-dependency static page for the Monday demo — styled
  paper sheet, three claim anchors in the clew palette with pure-CSS
  hover popups, inline-SVG provenance mini-graphs, and the claims
  sidebar, all hand-baked from `tests/fixtures/bundle-accepted/`.
  Looks-only, not product UI; the workspace tile stays Coming Soon.

- Support for clew's `unsourced` claim status (clew 0.8.1,
  `claims.json` schema 1.4 / unified 1.6). `unsourced` is accepted by
  `validate` as a resting claim status, and renders in the **amber
  `suspect` colour** — one amber "questionable" bucket rather than a
  row of its own.
  The fold is a **colour-layer alias**, not a status rewrite: the
  status string stays `unsourced` everywhere it is read or displayed,
  so the sidebar still tells you *which* of the two amber states a
  claim is in. This is deliberately unlike legacy `partial`, which
  **is** normalized to `suspect` at ingest — `partial` was a rename
  with no surviving concept, whereas `unsourced` is a distinct state.
  The live re-verify endpoint likewise passes `unsourced` through
  verbatim, so it cannot disagree with the rendered sidebar.
  Colours come from clew's **fine** per-claim `color` palette, not the
  coarse `display_color` / `display_group` fields — the coarse palette
  buckets `mismatch`+`missing` into "failed" and `registered` into
  "suspect", which would silently revert the v1.3 palette below.
  clew's per-claim `grounded` (bool | null) is absorbed by
  `Claim.extras`, so the schema bump needs no typed-field change.

### Fixed

- M2 re-verify handlers (`api/claim/verify` + `api/claims/verify`) now
  call clew's real `verify_claim(claim_id_or_location)` signature — a
  single positional arg — instead of the non-existent
  `verify_claim(claim_id=, against=, bundle_root=)` kwargs that 500'd
  against a real `scitex-clew` install. The response now reads the
  nested `result["claim"]["status"]` / `["verified_at"]` (clew's real
  shape) instead of absent top-level keys, and maps clew's flat
  `not_found` result to `ok: false`. `pinned_commit` is now metadata
  only (echoed as `verified_against`): clew is git-agnostic, so the
  host/deployment owns checking out the commit and pointing clew's DB
  via `SCITEX_CLEW_DB_PATH` before serving — these handlers never
  mutate the working tree.
- Claim-status colour palette (static `claims.css` + SPA `viewer.css`)
  aligned to clew's canonical claim vocabulary — palette v1.3
  (clew 0.7.0): `verified`→green, `suspect`→amber, `mismatch`→red,
  `missing`→its own dark red (`#a40e26`, distinct from mismatch),
  `registered`/`not_found`→grey. Previously the palettes keyed on
  statuses clew never emits (`stale`/`failed`/`contradicted` as claim
  statuses), so failed verifications rendered uncoloured. Legacy
  `partial` (pre-0.7.0 exports / older installed clews) is normalized
  to `suspect` at bundle ingest and in the re-verify envelope,
  mirroring clew's own read-time behaviour. The M4 `ReReviewBadge`
  vocabulary (`verified`/`concerns`/`contradicted`/`stale`) is
  separate and unchanged.

## [0.1.0] — 2026-06-13

The first formal release. Encompasses M1 (read-only static-site
renderer), M2 (live re-verify backend + SPA UI), M3 (Django mount
helper + multi-tenant `mount(resolver=...)`), M4 prep (`ReReviewBadge`
transport contract for `scitex-agentic-journal`), and the operator
CLI (`render` / `serve` / `info` / `validate`).

100% test coverage across every Python source file
(593 tests, no mocks per the ecosystem doctrine).

### Added — M1 (read-only static-site renderer, PRs #14-#22)

- Bundle loader (`scitex_live_paper.bundle.load(path) -> Bundle`)
  with lenient `Claim.extras` passthrough so a `scitex-clew` schema
  bump doesn't require a release here.
- Per-surface renderers under `scitex_live_paper._renderer`:
  index landing page, PDF.js viewer page, claims sidebar page,
  Mermaid DAG navigator. All assets vendored (no CDN).
- `scitex-live-paper render <bundle> --out <site>` CLI: emits a
  self-contained static site that opens from `file://`.
- M3-prep `_django/` app skeleton mirroring `scitex_writer._django`
  (SPA shell + `<path:endpoint>` `api_dispatch` + standalone
  bootstrap).
- Dispatcher loud-return contract: handlers must return a `Mapping`
  or `HttpResponse`; non-conformant returns surface a JSON 500
  with the handler name + actual type rather than a bare TypeError.

### Added — Reusable component design (PRs #23-#27)

- `BundleSource` (frozen) — three constructors
  (`from_directory`, `from_bundle`, `from_resolver`) so hosts that
  already have a bundle in memory or a DB-backed lookup don't have
  to write to disk.
- `BundleContext` (frozen) — per-render / per-request context
  the renderer reads (source + paper_state + api_base + options +
  re_review_badge).
- `PaperState` (frozen) — render-time lifecycle metadata. Five
  stages (`draft` / `preprint` / `in_review` / `accepted` /
  `published`). Drives header label + verification-badge visibility
  + re-verify enablement.
- `RendererOptions` (frozen) — display-time knobs (title,
  embed_mode, theme, extra).
- `state.yaml` bundle convention: optional file at the bundle root
  drives `Bundle.paper_state`. Absent → `PaperState(stage="preprint")`
  default. Loader coerces unquoted YAML timestamps back to ISO strings.
- `?embed=1` SPA shell variant: chrome-less iframe-friendly page
  for hub project view / writer preview / scholar mount.
- `scitex_live_paper.mount(resolver=...)` Django helper: builds URL
  patterns that inject a per-request `BundleContext` via the host's
  resolver callable. Single dispatcher works under both standalone
  (env-pinned) and hub-mounted (multi-tenant) deployments.

### Added — M2 live re-verify (PRs #31-#34)

- `POST /api/claim/verify` — per-claim re-verify endpoint. Calls
  `scitex_clew.verify_claim()` against `bundle.paper_state.pinned_commit`;
  degrades gracefully when `scitex-clew` is not installed
  (`fallback: true` per-result envelope).
- `POST /api/claims/verify` — bulk re-verify. Per-claim failures
  fold into the per-result envelope; one bad claim doesn't 500 the
  sweep. Clew probed once up-front and shared across the sweep.
- `GET /api/claims` — full claim list + `re_verify_enabled` flag
  for the SPA sidebar.
- SPA UI: claims sidebar with per-status colour palette mirroring
  scitex-clew's `VerificationStatus` (green / amber / red / grey)
  + per-claim Re-verify button gated on `re_verify_enabled` +
  sticky "Re-verify all" button.
- `viewer.js` module split: 5 focused vanilla ES modules
  (`viewer.js` orchestrator + `pdf-viewer.js` +
  `claims-sidebar.js` + `reverify-all.js` + `_utils.js`).
- `[clew]` optional dependency extra: `pip install scitex-live-paper[clew]`
  installs `scitex-clew` so the M2 path stops falling back.

### Added — Writer PDF viewer dogfood (PRs #28-#30)

- Vanilla ES-module port of `scitex_writer/_django/frontend/src/pdf-viewer.ts`
  into `scitex_live_paper/_django/static/live_paper/js/`. Same
  class surface (PDFViewer with `load` / `render` / `clear` /
  `setZoom` / `setFitWidth` / `renderPlaceholder` / `zoomPercent`),
  same vendored PDF.js bundle, same `?doc_type=` parameter. Writer
  can adopt this with zero API churn.
- Text layer + Annotation layer + native Ctrl-F find: closes the
  three features writer's pdf-viewer.ts explicitly deferred.
  Native browser Ctrl-F walks the text-layer spans automatically;
  PDF-internal links open in a new tab via
  `externalLinkTarget: 2`.
- `GET /api/pdf` — serves the bundle's manuscript PDF bytes via
  Django `FileResponse`. Adapts writer's `compile.py:handle_pdf`
  pattern.

### Added — M4 prep (PR #38)

- `ReReviewBadge` (frozen) — paper-level re-review verdict pushed
  in by `scitex-agentic-journal`. Four-status palette
  (`verified` / `concerns` / `contradicted` / `stale`). Distinct
  from M2 per-claim verification chips.
- `BundleContext.re_review_badge` optional field — hosts inject
  per request via `mount(resolver=...)`.
- `api/bundle-info` surfaces the badge as a top-level
  `re_review_badge` field; SPA `re-review-badge.js` module renders
  it above the claims sidebar with the same colour palette as the
  M2 chips. Absent → SPA hides the badge entirely.
- `docs/dev/m4-re-review-badge-contract.md` — contract document
  for the agentic-journal side.

### Added — Operator CLI (PRs #39-#40)

- `scitex-live-paper info <bundle>` — one-screen pre-flight summary
  (manuscript / schema / claim count + status palette / DAG present
  / full PaperState block). `--json` flag for machine-parseable
  output stable across runs.
- `scitex-live-paper validate <bundle>` — pre-flight audit.
  Checks for duplicate claim_ids, unknown statuses, non-hex
  source_hashes, accepted/published stages without `pinned_commit`.
  Exits 0 on clean, non-zero issue count otherwise (POSIX cap 125).

### Added — Documentation (PRs #18, #28, #35)

- `docs/dev-quickstart.md` — installable-from-scratch dev loop.
- `docs/research/writer-pdf-viewer-findings.md` — discovery doc on
  the writer PDF viewer architecture + scitex.ai deployment.
- `docs/dev/m2-reverify-runbook.md` — operator-facing trace for
  the M2 live re-verify path.
- `docs/dev/m4-re-review-badge-contract.md` — agentic-journal
  contract for the M4 paper-level re-review badge.

### Coverage — 100% (PRs #36-#37)

- Every Python source file in `src/scitex_live_paper/` at 100%
  coverage.
- Two `# pragma: no cover` lines with named justification.

### Schema ownership boundary (unchanged across the release)

This package is a **thin consumer**:

- `Claim` model + `VerificationStatus` + DAG: owned by
  [`scitex-clew`](https://github.com/ywatanabe1989/scitex-clew).
- Bundle layout / `\vclaim` macros / `figz`-`pltz` blobs: owned by
  [`scitex-writer`](https://github.com/ywatanabe1989/scitex-writer).
- Re-review verdicts: owned by `scitex-agentic-journal` (M4
  contract documented; not yet shipped on their side).
- Auth / hub mount: owned by
  [`scitex-hub`](https://github.com/ywatanabe1989/scitex-hub).

If a feature requires a new claim field, open the upstream issue
against `scitex-clew` — never invent fields here.

## [0.1.0-alpha] — 2026-06-12

Initial scaffold (README + minimum package skeleton + 5-milestone
roadmap). Detailed history of the scaffold lives in the git log;
this entry marks the pre-release that PR #1-#13 + the first round
of M1 work (PRs #14-#22) built on.
