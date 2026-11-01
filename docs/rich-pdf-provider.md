# Rich PDF provider

LivePaper owns rich PDF overlay and comment orchestration. The SDK owns page
rasterization, text/link layers, pen input and coordinate transforms. The provider
does not resolve application routes, fetch data, import consumer applications, or
persist notes itself. All consumers, including the native LivePaper page, supply
adapters to the same public factory.

The public browser module is `live_paper/js/pdf-provider.js` (use Django
`app_static`). For bundled consumers, the private npm file package exported by
`scitex_live_paper.get_frontend_package_dir()` provides
`@scitex/live-paper/pdf-provider` and `@scitex/live-paper/pdf-provider.css`.
The helper verifies the `scitex-live-paper.rich-pdf/v1` package/asset contract and
fails clearly for an older wheel without these assets. The contract requires
LivePaper>=0.2.20 and SDK>=0.3.17; LivePaper<=0.2.19 does not provide it.
A source checkout or preview wheel does not establish public availability.
Verify the required distributions before installing bundled consumers.
No npm publication is required. Build from the actual provider-capable wheel,
use its returned directory as a normal npm file dependency or `npm pack` input,
and retain the generated lockfile. The package exports remain within that wheel.

```js
import { createPdfViewer } from '@scitex/sdk/ui/pdf-viewer';
import { createRichPdfViewer } from '@scitex/live-paper/pdf-provider';
import '@scitex/live-paper/pdf-provider.css';
const viewer = createRichPdfViewer({container, createPdfViewer, ports});
await viewer.load(documentKey);
```

`ports.documents.resolve(key)` returns `{id, src, readonly?}`; `src` is the SDK
PDF source. `overlays.list(document)` returns `{id,page,bbox,label?,status?,readonly?,target?}`
records. `comments.list(document)` returns `{id,body,author?,target}` records;
`comments.create(document,target,body)` must resolve the saved comment, including
its identity, or reject. Targets are `{overlayId}` or `{page,bbox}`. Pages start
at 1; all bboxes are `[x0,y0,x1,y1]` in bottom-left PDF units. The provider uses
the SDK public page surface conversions, preserving rotation, crop and scale.
`target` on an overlay is opaque consumer metadata, returned in selection events.

`events.emit(event)` receives document-loaded, overlay-select, comments-open,
comment-created, region-select, pen-input, port-error and mutation-error/refused
events, tagged with document identity. Optional `mutations.createMark(document,input)`
receives SDK pen input. If absent, the configured SDK `onPenInput` hook remains
the mutation callback. `policy.canMutate({document,action,target})` can refuse
mutations; document/overlay/target read-only flags are checked before any callback.
The canonical overlay is checked even when a caller omits the target's read-only
flag. These browser checks do not replace server authorization or provenance locks.

`load`, `refresh`, `setOverlays`, `setComments`, `createComment`, `selectTarget`,
`destroy` are public. `renderer` exposes the unchanged SDK primitive for zoom,
fit width, controlled marks and pen mode. Feed snapshots are copied, comment
creates are not optimistic, errors retain the draft, and document replacement
closes stale popups. `destroy` tears down rich UI and the SDK renderer.

The native adapter is `pdf-viewer.js`: it translates bundle claims/comments,
resolves native PDF URLs, and bridges selection to the native evidence event bus.
It enables SDK text/link layers and supplies its already-loaded PDF.js runtime.
`viewer-entry.js` bundles the native adapter's local import graph, so the
content-hashed template entry cannot load stale unversioned helper modules.
Rebuild with `npm ci && npm run build:frontend`.

`tests/scitex_live_paper/check_rich_pdf_browser.py --sdk-root <source-root>
--chromium <binary>` uses a disposable two-page PDF and actual PDF.js. It covers
region/count rendering, comment create and refusal, read-only/policy guards,
failed-save draft retention, reload cleanup, native claim events and translated
comment requests. Its HTTP port fixtures are synthetic, not proof of a deployed
host's credentials, authorization, persistence or available documents.

Native browser comment POSTs require the `live-paper-csrf-token` DOM token from
the full/embed shell and send it as `X-CSRFToken` with same-origin credentials.
The comment dispatch explicitly applies Django CSRF protection, including when
the host uses HttpOnly/session-backed tokens. Missing tokens and foreign origins
are refused before the sidecar handler. This does not alter other legacy RPCs.

A clean native-provider build uses the tracked root package.json/lock and
`npm ci && npm run build:frontend` from this checkout, followed by the normal
Python wheel build. It requires no sibling checkout or untracked staging: the
native adapter bundles its local module graph and receives the SDK factory at
runtime via its public versioned asset URL.

Bundle loading distinguishes missing resources (`BundleMissingError`, a
`BundleError` subclass) from malformed existing content (`BundleError`). Hosts
can map expected absence to a bundle-selection empty state/404; malformed JSON
or schema failures remain errors. A project directory alone is not a valid
LivePaper bundle: the leaf loader requires a manuscript plus claims.json.

A trusted Django host resolver can bind `request.live_paper_view_selection`
to the SDK public `ProjectSelection`. Native full/embed rendering passes its
canonical pair as `view_scope`/`view_project` and root data attributes; it never
uses a raw query value as the current-project alias. This request-local view
is separate from the globally remembered navigation selection and remains
available for a missing-bundle empty state.
