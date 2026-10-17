# Live Paper ports/events contract (binding)

**Status:** implemented in the slice-B leaf PR — `ports/` package,
`api/port/...` dispatch, `port-events.js` DOM bus, bundled
`FigzFigureAdapter` default.
**Rule:** the core NEVER imports a renderer. Renderers are injected.

## 1. Core (neutral)

| Piece | Lives today | Role |
|---|---|---|
| Manuscript model | `bundle.Bundle` / `Claim` (`bundle.py`) | read-only mirror of the `scitex-clew` schema + `scitex-writer` layout |
| Render context | `BundleContext` / `BundleSource` / `PaperState` / `RendererOptions` (`_types.py`) | per-render / per-request data the core reads |
| Mount | `mount(resolver=...)` (`_django/_mount.py`) | host injects per-request resolution; exception→status table |
| Dispatcher | `api_dispatch` + `HANDLERS` (`_django/`) | core endpoints stay core; port-backed endpoints delegate ( §4 ) |
| Static emitters | `_renderer/` (`viewer`/`claims`/`dag`/`index`) | the BUNDLED DEFAULT adapters, injected — not imported by core |

Core dependencies stay: stdlib + Django (app layer) + Jinja2 (static
emit). No matplotlib / plotly / HTML-fragment builder in core.

## 2. Ports (injection points)

Three ports. Each is a **Python `Protocol`** (sync, JSON-plain
in/out) plus a **JS fetch shape** against `api_dispatch`:

- **figure-port** — `render_figure(bundle, figure_id, options) -> FigureFragment`.
  Re-renders one live figure from its data/code blob. Demo beat:
  data edit → event → figure refresh.
- **snippet-port** — `render_snippet(bundle, ref) -> HtmlFragment`.
  HTML/code snippets for hover evidence.
- **claim-graph-port** — `render_claim_graph(bundle, claim_id, depth) -> GraphFragment`.
  Claim-subgraph (nodes/edges as data + a renderer-chosen visual).

Port I/O is JSON-serialisable mappings only (`{"html": ...}` /
`{"svg": ...}` / `{"error": ...}`); a port NEVER returns a Django
response. The dispatcher wraps. Unknown port target → JSON 404, same
as unknown endpoints today.

## 3. Events (bus)

One envelope, two sides:

- **Python side** — `emit(kind, payload)` / `subscribe(kind, fn)` on
  `ports.EventBus`. Kinds: `evidence-request`,
  `evidence-response`, `figure-refresh`, `bundle-reloaded`. Pure
  in-process fan-out; no threads.
- **DOM side** — `CustomEvent("live-paper:<kind>", {detail})` on
  `#live-paper-root` (see `port-events.js`). Hover/click actions on
  overlay regions dispatch `live-paper:evidence-request`;
  the bus forwards it to the matching `api/port/<port>/<target>`
  endpoint and renders the returned fragment in the popup. Triggers
  are DOM events bound to port calls — no renderer code in core JS.

## 4. Evidence-popup surface contract

Overlay regions (PDF claim anchors, DAG nodes, sidebar rows) carry
`data-lp-port` + `data-lp-target` attributes. Core positions the
popup and draws the chrome; the FRAGMENT inside comes from the port.
Popup contract: `{title, html, provenance: [{label, href}]}` —
provenance links (figure→data/code) are mandatory, per the demo beat.

## 5. Delivery form — DECISION

**Hybrid: runtime registry (mechanism) + entry-point group
(distribution).** Core ships `ports.Registry` (map port-name →
adapter); `serve` injects the bundled default (`FigzFigureAdapter`).
Third parties publish under the `scitex.livepaper.renderers`
entry-point group (`ports.discover`); hosts can also pass adapters
directly (resolver-built `BundleContext(renderers=...)`).
Rationale: pip-native versioning + lazy imports keep core light;
direct-passing keeps tests and the standalone server free of
packaging ceremony.

## 6. Consumers (injectors, never forks)

- **Writer PDF-view embed** — another injector: Writer passes its
  bundle + renderer set, core untouched. Writer side stays consumer.
- **Agentic Journal** — consumes submission HTML view +
  ReReviewBadge popups as injected evidence via ports.
- **Hub mount** — hub acts on THIS contract when published; mount +
  shell slot + integration cutover audit stay hub-side.
