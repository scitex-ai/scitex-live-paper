/* GENERATED from viewer.js: npm run build:frontend. Do not edit. */

// src/scitex_live_paper/_django/static/live_paper/js/_utils.js
function normalizeBase(base) {
  if (!base.endsWith("/")) base += "/";
  return base;
}
function withBundleContext(url, pageHref = globalThis.location?.href) {
  if (!pageHref) return url;
  const page = new URL(pageHref);
  const target = new URL(url, page);
  if (target.origin !== page.origin) return url;
  for (const key of ["project", "working_dir"]) {
    if (!target.searchParams.has(key) && page.searchParams.has(key)) {
      target.searchParams.set(key, page.searchParams.get(key));
    }
  }
  return target.href;
}
async function fetchJson(url) {
  const res = await fetch(withBundleContext(url));
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch (_err) {
    throw new Error("HTTP " + res.status + ": " + text.slice(0, 200));
  }
}
async function fetchOrNull(url) {
  try {
    const res = await fetch(withBundleContext(url));
    if (!res.ok) return null;
    return await res.json();
  } catch (_err) {
    return null;
  }
}
function hideLoading(rootEl) {
  const scope = rootEl || document;
  const loading = scope.querySelector ? scope.querySelector("#live-paper-loading") : document.getElementById("live-paper-loading");
  if (loading) loading.hidden = true;
}
function setStatus(payload) {
  hideLoading();
  const header = document.getElementById("live-paper-bundle-header");
  const diagnostics = document.getElementById(
    "live-paper-bundle-diagnostics"
  );
  const pre = document.getElementById("live-paper-bundle-info");
  if (pre) {
    pre.textContent = JSON.stringify(payload, null, 2);
  }
  if (diagnostics) diagnostics.hidden = false;
  if (!header) return;
  header.hidden = false;
  header.textContent = "";
  if (payload && payload.error) {
    header.className = "lp-bundle-header lp-bundle-error";
    header.textContent = "Couldn't load bundle info: " + payload.error;
    return;
  }
  header.className = "lp-bundle-header";
  const ps = payload && payload.paper_state || {};
  const title = document.createElement("strong");
  title.className = "lp-bundle-title";
  title.textContent = ps.header_label || ps.stage || "Live paper";
  header.appendChild(title);
  const meta = document.createElement("span");
  meta.className = "lp-bundle-meta";
  const parts = [];
  if (ps.journal) parts.push(ps.journal);
  if (ps.doi) parts.push(ps.doi);
  if (payload && payload.manuscript) parts.push(payload.manuscript);
  if (payload && payload.claim_count != null)
    parts.push(payload.claim_count + " claims");
  meta.textContent = parts.join(" \xB7 ");
  header.appendChild(meta);
}
function ensurePdfContainer(rootEl) {
  let host = document.getElementById("live-paper-pdf");
  if (!host) {
    host = document.createElement("div");
    host.id = "live-paper-pdf";
    host.className = "live-paper-pdf";
    rootEl.appendChild(host);
  }
  return host;
}
function ensureClaimsSidebar(rootEl) {
  let host = document.getElementById("live-paper-claims");
  if (!host) {
    host = document.createElement("aside");
    host.id = "live-paper-claims";
    host.className = "live-paper-claims";
    rootEl.appendChild(host);
  }
  return host;
}
function renderError(message) {
  const container = document.getElementById("live-paper-bundle-info");
  if (container) {
    container.textContent = JSON.stringify({ error: message }, null, 2);
  }
}
function cssEscape(value) {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return String(value).replace(/(["\\])/g, "\\$1");
}

// src/scitex_live_paper/_django/static/live_paper/js/pdf-provider.js
function createRichPdfViewer(options) {
  const { container, createPdfViewer, ports = {}, rendererOptions = {} } = options;
  if (typeof createPdfViewer !== "function") throw new TypeError("SDK PDF factory required");
  if (typeof ports.documents?.resolve !== "function") throw new TypeError("Document port required");
  let current = null;
  let overlays = [];
  let comments = [];
  let sequence = 0;
  let disposed = false;
  const pages = /* @__PURE__ */ new Map();
  const layers = /* @__PURE__ */ new Map();
  let popup = null;
  const emit = (event) => ports.events?.emit?.({ documentId: current?.id ?? null, ...event });
  const allow = (action, target) => {
    const canonical = target?.overlayId ? overlays.find((item) => item.id === target.overlayId) : null;
    return Boolean(current && !current.readonly && !disposed && !target?.readonly && !canonical?.readonly && ports.policy?.canMutate?.({ document: current, action, target }) !== false);
  };
  const hooks = rendererOptions.hooks ?? {};
  const renderer = createPdfViewer({
    ...rendererOptions,
    container,
    hooks: {
      ...hooks,
      onPageRender(page, viewport, surface) {
        if (!surface?.element || typeof surface.pdfToViewportRect !== "function") throw new Error("SDK PDF page surface unavailable; update to a provider-capable SDK build");
        pages.set(page, surface);
        paint(page);
        hooks.onPageRender?.(page, viewport, surface);
      },
      onPenInput(input) {
        if (!allow("mark-create", input)) {
          emit({ type: "mutation-refused", action: "mark-create" });
          return;
        }
        if (ports.mutations?.createMark) {
          const document2 = current;
          Promise.resolve().then(() => ports.mutations.createMark(document2, input)).catch((error) => emit({ type: "mutation-error", action: "mark-create", documentId: document2.id, error }));
        } else hooks.onPenInput?.(input);
        emit({ type: "pen-input", input });
      },
      onRegionSelect(region) {
        if (!allow("region-select", region)) return;
        hooks.onRegionSelect?.(region);
        emit({ type: "region-select", region });
      }
    }
  });
  function setOverlays(values) {
    overlays = Array.isArray(values) ? [...values] : [];
    repaint();
  }
  function setComments(values) {
    comments = Array.isArray(values) ? [...values] : [];
    repaint();
  }
  function repaint() {
    for (const page of pages.keys()) paint(page);
  }
  function rectStyle(element, surface, bbox) {
    const [x0, y0, x1, y1] = surface.pdfToViewportRect(bbox);
    Object.assign(element.style, { position: "absolute", left: `${Math.min(x0, x1)}px`, top: `${Math.min(y0, y1)}px`, width: `${Math.abs(x1 - x0)}px`, height: `${Math.abs(y1 - y0)}px`, pointerEvents: "auto" });
  }
  function paint(page) {
    const surface = pages.get(page);
    if (!surface?.element.isConnected || disposed) return;
    layers.get(page)?.remove();
    const layer = document.createElement("div");
    layer.className = "lp-rich-overlays";
    Object.assign(layer.style, { position: "absolute", inset: "0", pointerEvents: "none", zIndex: "4" });
    surface.element.append(layer);
    layers.set(page, layer);
    for (const overlay of overlays.filter((item) => item.page === page && validBox(item.bbox))) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "lp-rich-overlay";
      button.dataset.overlayId = overlay.id;
      button.dataset.status = overlay.status ?? "";
      button.setAttribute("aria-label", overlay.label || `Overlay ${overlay.id}`);
      button.title = overlay.label || overlay.id;
      rectStyle(button, surface, overlay.bbox);
      const count = comments.filter((comment) => comment.target?.overlayId === overlay.id).length;
      if (count) {
        const badge = document.createElement("span");
        badge.className = "lp-rich-comment-count";
        badge.textContent = `\u270E${count}`;
        button.append(badge);
      }
      button.addEventListener("click", () => selectTarget({ overlayId: overlay.id, page, bbox: overlay.bbox, readonly: overlay.readonly }, button, overlay));
      layer.append(button);
    }
    for (const comment of comments.filter((item) => !item.target?.overlayId && item.target?.page === page && validBox(item.target.bbox))) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "lp-rich-comment-marker";
      button.textContent = "\u270E";
      button.setAttribute("aria-label", `Comment: ${comment.body || ""}`);
      rectStyle(button, surface, comment.target.bbox);
      button.style.width = "24px";
      button.style.height = "24px";
      button.addEventListener("click", () => selectTarget(comment.target, button));
      layer.append(button);
    }
  }
  function selectTarget(target, anchor, overlay = null) {
    if (disposed || !current) return;
    popup?.remove();
    emit({ type: "overlay-select", target, overlay });
    const panel = document.createElement("section");
    panel.className = "lp-rich-comments";
    if (!options.commentsContainer) Object.assign(panel.style, { position: "fixed", right: "24px", bottom: "24px", zIndex: "100" });
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "PDF comments");
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "Close comments";
    close.addEventListener("click", () => {
      panel.remove();
      anchor?.focus();
    });
    panel.append(close);
    for (const comment of comments.filter((item) => sameTarget(item.target, target))) {
      const row = document.createElement("p");
      row.className = "lp-rich-comment";
      row.textContent = [comment.author, comment.body].filter(Boolean).join(": ");
      panel.append(row);
    }
    if (ports.comments?.create) {
      const form = document.createElement("form");
      const input = document.createElement("textarea");
      input.setAttribute("aria-label", "New PDF comment");
      input.required = true;
      const submit = document.createElement("button");
      submit.type = "submit";
      submit.textContent = "Add comment";
      const status = document.createElement("p");
      status.setAttribute("role", "status");
      if (!allow("comment-create", target)) {
        input.disabled = true;
        submit.disabled = true;
        status.textContent = "Comments are read-only for this target.";
      }
      form.append(input, submit, status);
      panel.append(form);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        submit.disabled = true;
        status.textContent = "Saving comment\u2026";
        try {
          await createComment(target, input.value);
          if (!panel.isConnected) return;
          status.textContent = "Comment saved.";
          input.value = "";
          selectTarget(target, anchor, overlay);
        } catch (error) {
          if (panel.isConnected) status.textContent = error.message || "Comment could not be saved.";
        } finally {
          if (panel.isConnected) submit.disabled = !allow("comment-create", target);
        }
      });
    }
    (options.commentsContainer || container).append(panel);
    popup = panel;
    emit({ type: "comments-open", target });
  }
  async function createComment(target, body) {
    if (!allow("comment-create", target)) throw new Error("Comment mutation refused by document policy");
    if (!ports.comments?.create) throw new Error("Comment mutation port unavailable");
    if (!body?.trim()) throw new Error("Comment text required");
    const document2 = current;
    const token = sequence;
    try {
      const comment = await ports.comments.create(document2, target, body.trim());
      if (!comment?.id) throw new Error("Comment port returned no saved comment identity");
      if (disposed || token !== sequence) return comment;
      comments = [...comments.filter((item) => item.id !== comment.id), comment];
      repaint();
      emit({ type: "comment-created", comment });
      return comment;
    } catch (error) {
      emit({ type: "mutation-error", action: "comment-create", documentId: document2.id, error });
      throw error;
    }
  }
  async function refresh() {
    if (!current || disposed) return;
    const token = sequence;
    const document2 = current;
    const values = await Promise.allSettled([ports.overlays?.list?.(document2) ?? overlays, ports.comments?.list?.(document2) ?? comments]);
    if (disposed || token !== sequence) return;
    if (values[0].status === "fulfilled") overlays = [...values[0].value || []];
    else emit({ type: "port-error", port: "overlays", error: values[0].reason });
    if (values[1].status === "fulfilled") comments = [...values[1].value || []];
    else emit({ type: "port-error", port: "comments", error: values[1].reason });
    repaint();
  }
  async function load(key) {
    if (disposed) throw new Error("PDF provider has been destroyed");
    const token = ++sequence;
    popup?.remove();
    popup = null;
    current = null;
    for (const layer of layers.values()) layer.remove();
    layers.clear();
    pages.clear();
    const document2 = await ports.documents.resolve(key);
    if (!document2?.id || !document2.src) throw new Error("Document port must return id and src");
    if (disposed || token !== sequence) return false;
    current = document2;
    pages.clear();
    overlays = [];
    comments = [];
    await refresh();
    if (disposed || token !== sequence) return false;
    await renderer.load(document2.src);
    if (disposed || token !== sequence) return false;
    emit({ type: "document-loaded" });
    return true;
  }
  function destroy() {
    if (disposed) return;
    disposed = true;
    sequence++;
    popup?.remove();
    for (const layer of layers.values()) layer.remove();
    layers.clear();
    pages.clear();
    renderer.destroy();
  }
  return { renderer, load, refresh, setOverlays, setComments, selectTarget, createComment, destroy };
}
function validBox(box) {
  return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite);
}
function sameTarget(left, right) {
  if (left?.overlayId || right?.overlayId) return Boolean(left?.overlayId && left.overlayId === right?.overlayId);
  return left?.page === right?.page && JSON.stringify(left?.bbox) === JSON.stringify(right?.bbox);
}

// src/scitex_live_paper/_django/static/live_paper/js/claim-overlays.js
function pickAnchor(claim) {
  return claim?.anchor ?? claim?.extras?.anchor ?? null;
}

// src/scitex_live_paper/_django/static/live_paper/js/comments.js
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== void 0 && text !== null) node.textContent = text;
  return node;
}
async function fetchComments(apiBase) {
  try {
    const res = await fetch(withBundleContext(apiBase + "comments"), {
      headers: { Accept: "application/json" }
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) return [];
    return Array.isArray(body.comments) ? body.comments : [];
  } catch (err) {
    console.warn("[live-paper] comments fetch failed:", err);
    return [];
  }
}
async function postComment(apiBase, { body, target, author, kind }) {
  const comment = { body, target };
  if (author) comment.author = author;
  if (kind) comment.kind = kind;
  const token = document.querySelector('meta[name="live-paper-csrf-token"]')?.content;
  if (!token || token === "NOTPROVIDED") throw new Error("LivePaper CSRF token missing; reload the viewer");
  const res = await fetch(withBundleContext(apiBase + "comments"), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json", "X-CSRFToken": token },
    body: JSON.stringify({ comment })
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || !payload.comment) {
    throw new Error(payload.error || `comment post failed: ${res.status}`);
  }
  return payload.comment;
}
async function renderCommentSection(containerEl, claimId, apiBase) {
  containerEl.innerHTML = "";
  const section = el("div", "lp-comments");
  section.appendChild(el("p", "lp-comments-loading", "Loading comments\u2026"));
  containerEl.appendChild(section);
  let comments = [];
  try {
    comments = (await fetchComments(apiBase)).filter(
      (c) => c?.target?.claim_id === claimId
    );
  } catch (err) {
    section.innerHTML = "";
    section.appendChild(el("p", "lp-comments-empty", "Comments unavailable."));
    return section;
  }
  section.innerHTML = "";
  section.appendChild(el("h3", "lp-comments-title", `Comments (${comments.length})`));
  if (comments.length === 0) {
    section.appendChild(
      el("p", "lp-comments-empty", "No comments yet \u2014 add the first below.")
    );
  } else {
    const list = el("ul", "lp-comments-list");
    for (const c of comments) {
      const item = el("li", "lp-comments-item");
      const head = el("div", "lp-comments-head");
      head.appendChild(el("span", "lp-comment-author", c.author || "anonymous"));
      if (c.created_at) head.appendChild(el("span", "lp-comment-ts", String(c.created_at).slice(0, 16).replace("T", " ")));
      item.appendChild(head);
      item.appendChild(el("p", "lp-comment-body", c.body || ""));
      list.appendChild(item);
    }
    section.appendChild(list);
  }
  const form = el("form", "lp-comments-form");
  const input = el("textarea", "lp-comments-input");
  input.rows = 2;
  input.placeholder = "Add a comment on this claim\u2026";
  input.setAttribute("aria-label", "New comment");
  const row = el("div", "lp-comments-form-row");
  const author = el("input", "lp-comments-author");
  author.placeholder = "name (optional)";
  author.setAttribute("aria-label", "Author name");
  const submit = el("button", "lp-comments-submit", "Comment");
  submit.type = "submit";
  row.appendChild(author);
  row.appendChild(submit);
  form.appendChild(input);
  form.appendChild(row);
  const error = el("p", "lp-comments-error");
  error.hidden = true;
  form.appendChild(error);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    const text = input.value.trim();
    if (!text) return;
    submit.disabled = true;
    try {
      await postComment(apiBase, {
        body: text,
        target: { claim_id: claimId },
        author: author.value.trim() || void 0
      });
      await renderCommentSection(containerEl, claimId, apiBase);
    } catch (err) {
      error.textContent = String(err && err.message || err);
      error.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });
  section.appendChild(form);
  return section;
}

// src/scitex_live_paper/_django/static/live_paper/js/pdf-viewer.js
function toOverlay(claim) {
  const anchor = pickAnchor(claim);
  if (!anchor || !Number.isInteger(anchor.page) || !Array.isArray(anchor.bbox)) return null;
  return {
    id: claim.claim_id,
    page: anchor.page,
    bbox: anchor.bbox,
    label: claim.claim_value || claim.claim_id,
    status: claim.status,
    readonly: claim.readonly === true || claim.extras?.locked === true,
    target: { figureId: claim.figure_id ?? claim.extras?.figure_id ?? null }
  };
}
function toComment(comment) {
  const { claim_id, ...region } = comment.target || {};
  return {
    id: comment.id,
    body: comment.body,
    author: comment.author,
    target: claim_id ? { overlayId: claim_id } : region
  };
}
var PDFViewer = class {
  constructor(options) {
    this.container = options.container;
    this.apiBase = options.apiBase;
    this.claims = [];
    this.comments = [];
    this.container.classList.add("pdf-viewer-host");
    this.provider = createRichPdfViewer({
      container: this.container,
      createPdfViewer: options.createPdfViewer,
      rendererOptions: {
        pdfjs: options.pdfjs,
        workerSrc: options.workerSrc,
        textLayer: true,
        linkLayer: true
      },
      ports: {
        documents: { resolve: (docType) => ({
          id: String(docType || "manuscript"),
          src: withBundleContext(this.apiBase + "pdf?doc_type=" + encodeURIComponent(docType || "manuscript") + "&t=" + Date.now())
        }) },
        overlays: { list: () => this.claims.map(toOverlay).filter(Boolean) },
        comments: {
          list: () => this.comments.map(toComment),
          create: async (_document, target, body) => {
            const nativeTarget = target.overlayId ? { claim_id: target.overlayId } : { page: target.page, bbox: target.bbox };
            const comment = await postComment(this.apiBase, { body, target: nativeTarget });
            this.comments.push(comment);
            return toComment(comment);
          }
        },
        events: { emit: (event) => {
          if (event.type === "overlay-select" && event.overlay) {
            this.container.dispatchEvent(new CustomEvent("live-paper:claim", { bubbles: true, detail: { id: event.overlay.id } }));
            if (event.overlay.target?.figureId) this.container.dispatchEvent(new CustomEvent("live-paper:evidence-request", { bubbles: true, detail: { port: "figure", target: event.overlay.target.figureId } }));
          }
          this.container.dispatchEvent(new CustomEvent("live-paper:pdf", { bubbles: true, detail: event }));
        } }
      }
    });
    this.provider.renderer.setInteractive(false);
  }
  setClaims(claims) {
    this.claims = claims || [];
    this.provider.setOverlays(this.claims.map(toOverlay).filter(Boolean));
  }
  setComments(comments) {
    this.comments = comments || [];
    this.provider.setComments(this.comments.map(toComment));
  }
  async load(docType = "manuscript") {
    try {
      await this.provider.load(docType);
      await this.provider.renderer.fitWidth();
      return true;
    } catch (error) {
      console.warn("[pdf-viewer] load failed:", error);
      this.renderPlaceholder("No PDF available.");
      return false;
    }
  }
  clear() {
    this.container.replaceChildren();
  }
  renderPlaceholder(message = "No PDF available.") {
    this.clear();
    const placeholder = document.createElement("p");
    placeholder.className = "pdf-placeholder";
    placeholder.textContent = message;
    this.container.append(placeholder);
  }
  render() {
    return this.provider.renderer.setScale(this.provider.renderer.getScale());
  }
  setZoom(delta) {
    return this.provider.renderer.setScale(Math.max(0.4, Math.min(3, this.provider.renderer.getScale() + delta)));
  }
  setFitWidth() {
    return this.provider.renderer.fitWidth();
  }
  get zoomPercent() {
    return Math.round(this.provider.renderer.getScale() * 100);
  }
  destroy() {
    this.provider.destroy();
  }
};

// src/scitex_live_paper/_django/static/live_paper/js/claim-details.js
function el2(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== void 0 && text !== null) node.textContent = text;
  return node;
}
function renderClaimDetail(sidebarEl, claim, apiBase) {
  closeClaimDetail(sidebarEl);
  const pane = el2("div", "lp-claim-detail");
  pane.setAttribute("role", "dialog");
  pane.setAttribute("aria-label", "Claim detail");
  const header = el2("div", "lp-claim-detail-header");
  header.appendChild(el2("code", "lp-claim-detail-id", claim.claim_id || "(no id)"));
  const close = el2("button", "lp-claim-detail-close", "Close");
  close.type = "button";
  close.addEventListener("click", () => closeClaimDetail(sidebarEl));
  header.appendChild(close);
  pane.appendChild(header);
  pane.appendChild(el2(
    "p",
    "lp-claim-detail-value",
    claim.claim_value || claim.file_path || "(no value)"
  ));
  const status = el2(
    "p",
    "lp-claim-detail-status",
    "status: " + (claim.status || "registered")
  );
  status.dataset.status = claim.status || "registered";
  pane.appendChild(status);
  const prov = el2("ul", "lp-claim-detail-provenance");
  const rows = [
    ["source", claim.source_file],
    ["hash", claim.source_hash],
    ["session", claim.source_session],
    ["location", claim.file_path && claim.line_number != null ? claim.file_path + ":" + claim.line_number : claim.file_path]
  ];
  for (const [label, value] of rows) {
    if (!value) continue;
    const item = el2("li");
    item.appendChild(el2("span", "lp-claim-detail-prov-label", label + ": "));
    item.appendChild(el2("code", null, String(value)));
    prov.appendChild(item);
  }
  if (claim.extras && claim.extras.figure_id) {
    const item = el2("li");
    item.appendChild(el2("span", "lp-claim-detail-prov-label", "figure: "));
    item.appendChild(el2("code", null, String(claim.extras.figure_id)));
    prov.appendChild(item);
  }
  pane.appendChild(prov);
  const dagBox = el2("div", "lp-claim-dag");
  dagBox.appendChild(el2("p", "lp-claim-dag-loading", "Loading DAG\u2026"));
  pane.appendChild(dagBox);
  renderDagPane(dagBox, claim.claim_id, apiBase);
  try {
    const commentsBox = el2("div", "lp-claim-comments-slot");
    pane.appendChild(commentsBox);
    void renderCommentSection(commentsBox, claim.claim_id, apiBase);
  } catch (err) {
    console.warn("[live-paper] comments section failed:", err);
  }
  sidebarEl.appendChild(pane);
  return pane;
}
function closeClaimDetail(sidebarEl) {
  const open = sidebarEl.querySelector(":scope > .lp-claim-detail");
  if (open) open.remove();
}
async function renderDagPane(dagBox, claimId, apiBase) {
  let body = {};
  try {
    const res = await fetch(withBundleContext(apiBase + "dag"), { headers: { Accept: "application/json" } });
    body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || "dag request failed: " + res.status);
  } catch (err) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el2(
      "p",
      "lp-claim-dag-empty",
      "DAG unavailable (" + String(err && err.message || err) + ")."
    ));
    return;
  }
  if (!body.mermaid) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el2("p", "lp-claim-dag-empty", "DAG unavailable (empty)."));
    return;
  }
  if (!window.mermaid) {
    dagBox.innerHTML = "";
    const pre = el2("pre", "lp-claim-dag-source", body.mermaid);
    dagBox.appendChild(pre);
    return;
  }
  try {
    if (typeof window.mermaid.initialize === "function") {
      window.mermaid.initialize({ startOnLoad: false });
    }
    const { svg } = await window.mermaid.render("lp-dag-" + String(claimId || "x"), body.mermaid);
    dagBox.innerHTML = "";
    const wrap = el2("div", "lp-claim-dag-svg");
    wrap.innerHTML = svg;
    dagBox.appendChild(wrap);
  } catch (err) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el2(
      "p",
      "lp-claim-dag-empty",
      "DAG render failed (" + String(err && err.message || err) + ")."
    ));
  }
}

// src/scitex_live_paper/_django/static/live_paper/js/reverify-all.js
function renderReverifyAllButton(apiBase, pinnedCommit) {
  const wrap = document.createElement("div");
  wrap.className = "lp-claims-toolbar";
  const btn = document.createElement("button");
  btn.className = "lp-claims-reverify-all";
  btn.type = "button";
  btn.textContent = "Re-verify all";
  btn.addEventListener("click", function() {
    void reverifyAllClaims(btn, pinnedCommit, apiBase);
  });
  wrap.appendChild(btn);
  return wrap;
}
async function reverifyAllClaims(btn, pinnedCommit, apiBase) {
  btn.disabled = true;
  const originalLabel = btn.textContent;
  btn.textContent = "Verifying\u2026";
  document.querySelectorAll(".lp-claim").forEach(function(row) {
    row.dataset.status = "verifying";
    const badge = row.querySelector(".lp-claim-status");
    if (badge) {
      badge.dataset.status = "verifying";
      badge.textContent = "verifying";
    }
    const perBtn = row.querySelector(".lp-claim-reverify");
    if (perBtn) perBtn.disabled = true;
  });
  try {
    const body = {};
    if (pinnedCommit) body.pinned_commit = pinnedCommit;
    const res = await fetch(withBundleContext(apiBase + "claims/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const payload = await res.json();
    if (res.status !== 200 || !payload || !Array.isArray(payload.results)) {
      console.error("[live-paper] re-verify-all unexpected response", res.status, payload);
      _markAllClaimRowsAsError();
      return;
    }
    for (const result of payload.results) {
      _applyResultToRow(result);
    }
  } catch (err) {
    console.error("[live-paper] re-verify-all network error", err);
    _markAllClaimRowsAsError();
  } finally {
    btn.disabled = false;
    btn.textContent = originalLabel;
    document.querySelectorAll(".lp-claim-reverify").forEach(function(b) {
      b.disabled = false;
      b.textContent = "Re-verify";
    });
  }
}
function _applyResultToRow(result) {
  if (!result || !result.claim_id) return;
  const selector = '.lp-claim[data-claim-id="' + cssEscape(result.claim_id) + '"]';
  const row = document.querySelector(selector);
  if (!row) return;
  let nextStatus;
  if (result.ok === true) {
    nextStatus = result.status || "verified";
  } else if (result.fallback === true) {
    nextStatus = result.status || "stale";
    console.info(
      "[live-paper] re-verify-all fallback for %s: %s",
      result.claim_id,
      result.reason
    );
  } else {
    nextStatus = result.status || "error";
    console.warn("[live-paper] re-verify-all per-claim failure", result);
  }
  row.dataset.status = nextStatus;
  const badge = row.querySelector(".lp-claim-status");
  if (badge) {
    badge.dataset.status = nextStatus;
    badge.textContent = nextStatus;
    const note = result.reason || result.error || "";
    if (note) badge.title = String(note).slice(0, 240);
    else badge.removeAttribute("title");
  }
}
function _markAllClaimRowsAsError() {
  document.querySelectorAll(".lp-claim").forEach(function(row) {
    row.dataset.status = "error";
    const badge = row.querySelector(".lp-claim-status");
    if (badge) {
      badge.dataset.status = "error";
      badge.textContent = "error";
    }
  });
}

// src/scitex_live_paper/_django/static/live_paper/js/claims-sidebar.js
function renderClaimsSidebar(rootEl, claimsPayload, apiBase) {
  if (!claimsPayload || !Array.isArray(claimsPayload.claims)) return;
  const sidebar = ensureClaimsSidebar(rootEl);
  sidebar.innerHTML = "";
  const header = document.createElement("div");
  header.className = "lp-claims-header";
  header.textContent = claimsPayload.claim_count + " claim" + (claimsPayload.claim_count === 1 ? "" : "s");
  sidebar.appendChild(header);
  const reVerifyEnabled = !!claimsPayload.re_verify_enabled;
  const pinnedCommit = claimsPayload.pinned_commit || null;
  if (reVerifyEnabled) {
    sidebar.appendChild(renderReverifyAllButton(apiBase, pinnedCommit));
  }
  const list = document.createElement("ul");
  list.className = "lp-claims-list";
  for (const claim of claimsPayload.claims) {
    list.appendChild(renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit));
  }
  sidebar.appendChild(list);
}
function renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit) {
  const li = document.createElement("li");
  li.className = "lp-claim";
  li.dataset.claimId = claim.claim_id;
  li.dataset.status = claim.status || "registered";
  li.classList.add("lp-claim-selectable");
  li.addEventListener("click", function(event) {
    if (event.target.closest("button")) return;
    const sidebar = li.closest(".live-paper-claims");
    if (sidebar) renderClaimDetail(sidebar, claim, apiBase);
  });
  const idSpan = document.createElement("span");
  idSpan.className = "lp-claim-id";
  idSpan.textContent = claim.claim_id;
  li.appendChild(idSpan);
  const valueSpan = document.createElement("span");
  valueSpan.className = "lp-claim-value";
  valueSpan.textContent = claim.claim_value || claim.file_path || "(no value)";
  li.appendChild(valueSpan);
  const statusBadge = document.createElement("span");
  statusBadge.className = "lp-claim-status";
  statusBadge.dataset.status = claim.status || "registered";
  statusBadge.textContent = claim.status || "registered";
  li.appendChild(statusBadge);
  if (reVerifyEnabled) {
    const btn = document.createElement("button");
    btn.className = "lp-claim-reverify";
    btn.type = "button";
    btn.textContent = "Re-verify";
    btn.dataset.claimId = claim.claim_id;
    btn.addEventListener("click", function() {
      void reverifyClaim(li, claim.claim_id, pinnedCommit, apiBase);
    });
    li.appendChild(btn);
  }
  return li;
}
async function reverifyClaim(rowEl, claimId, pinnedCommit, apiBase) {
  const statusBadge = rowEl.querySelector(".lp-claim-status");
  const btn = rowEl.querySelector(".lp-claim-reverify");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Verifying\u2026";
  }
  if (statusBadge) {
    statusBadge.dataset.status = "verifying";
    statusBadge.textContent = "verifying";
  }
  try {
    const body = { claim_id: claimId };
    if (pinnedCommit) body.pinned_commit = pinnedCommit;
    const res = await fetch(withBundleContext(apiBase + "claim/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const payload = await res.json();
    let nextStatus;
    let statusNote = "";
    if (res.status === 200 && payload.ok === true) {
      nextStatus = payload.status || "verified";
    } else if (res.status === 200 && payload.fallback === true) {
      nextStatus = payload.status || "stale";
      statusNote = payload.reason || "";
      console.info("[live-paper] re-verify fallback:", payload.reason);
    } else {
      nextStatus = "error";
      statusNote = payload.reason || payload.error || "HTTP " + res.status;
      console.error("[live-paper] re-verify failed", res.status, payload);
    }
    rowEl.dataset.status = nextStatus;
    if (statusBadge) {
      statusBadge.dataset.status = nextStatus;
      statusBadge.textContent = nextStatus;
      if (statusNote) statusBadge.title = String(statusNote).slice(0, 240);
      else statusBadge.removeAttribute("title");
    }
  } catch (err) {
    console.error("[live-paper] re-verify network error", err);
    if (statusBadge) {
      statusBadge.dataset.status = "error";
      statusBadge.textContent = "error";
      statusBadge.title = String(err && err.message || err).slice(0, 240);
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Re-verify";
    }
  }
}

// src/scitex_live_paper/_django/static/live_paper/js/re-review-badge.js
function renderReReviewBadge(rootEl, bundleInfoPayload) {
  if (!bundleInfoPayload || !bundleInfoPayload.re_review_badge) return;
  const badge = bundleInfoPayload.re_review_badge;
  if (!badge.status) return;
  const host = ensureReReviewBadgeHost(rootEl);
  host.innerHTML = "";
  const chip = document.createElement("div");
  chip.className = "lp-re-review-badge";
  chip.dataset.status = badge.status;
  const label = document.createElement("span");
  label.className = "lp-re-review-badge-label";
  label.textContent = "Re-review: " + badge.status;
  chip.appendChild(label);
  if (badge.reviewer) {
    const reviewer = document.createElement("span");
    reviewer.className = "lp-re-review-badge-reviewer";
    reviewer.textContent = " \xB7 by " + badge.reviewer;
    chip.appendChild(reviewer);
  }
  if (badge.last_reviewed_at) {
    const ts = document.createElement("span");
    ts.className = "lp-re-review-badge-ts";
    ts.textContent = " \xB7 " + badge.last_reviewed_at;
    chip.appendChild(ts);
  }
  if (badge.notes) {
    const notes = document.createElement("p");
    notes.className = "lp-re-review-badge-notes";
    notes.textContent = badge.notes;
    chip.appendChild(notes);
  }
  if (badge.log_url) {
    const link = document.createElement("a");
    link.className = "lp-re-review-badge-log";
    link.href = badge.log_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "view re-review log \u2192";
    chip.appendChild(link);
  }
  host.appendChild(chip);
}
function ensureReReviewBadgeHost(rootEl) {
  let host = document.getElementById("live-paper-re-review");
  if (!host) {
    host = document.createElement("section");
    host.id = "live-paper-re-review";
    host.className = "live-paper-re-review";
    rootEl.insertBefore(host, rootEl.firstChild);
  }
  return host;
}

// src/scitex_live_paper/_django/static/live_paper/js/port-events.js
function bindPortEvents(rootEl, apiBase) {
  rootEl.addEventListener("click", (event) => {
    const hit = event.target.closest("[data-lp-port]");
    if (!hit || !rootEl.contains(hit)) return;
    const port = hit.getAttribute("data-lp-port");
    const target = hit.getAttribute("data-lp-target");
    if (!port || !target) return;
    rootEl.dispatchEvent(
      new CustomEvent("live-paper:evidence-request", {
        bubbles: true,
        detail: { port, target }
      })
    );
  });
  rootEl.addEventListener("live-paper:evidence-request", (event) => {
    const { port, target } = event.detail || {};
    if (!port || !target) return;
    const url = apiBase + "port/" + encodeURIComponent(port) + "/" + encodeURIComponent(target);
    fetch(withBundleContext(url), { headers: { Accept: "application/json" } }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.error || "port request failed: " + response.status);
      }
      rootEl.dispatchEvent(
        new CustomEvent("live-paper:evidence-response", {
          bubbles: true,
          detail: { port, target, fragment: body }
        })
      );
      renderEvidencePopup(rootEl, body);
    }).catch((err) => {
      renderEvidencePopup(rootEl, {
        title: port + ":" + target,
        html: '<p class="lp-evidence-error">Evidence unavailable.</p>',
        provenance: [],
        _error: String(err)
      });
    });
  });
}
function renderEvidencePopup(rootEl, fragment) {
  closeEvidencePopup(rootEl);
  const popup = document.createElement("div");
  popup.className = "lp-evidence-popup";
  popup.setAttribute("role", "dialog");
  const title = document.createElement("div");
  title.className = "lp-evidence-title";
  title.textContent = fragment.title || "evidence";
  popup.appendChild(title);
  const body = document.createElement("div");
  body.className = "lp-evidence-body";
  body.innerHTML = fragment.html || "";
  popup.appendChild(body);
  const provenance = Array.isArray(fragment.provenance) ? fragment.provenance : [];
  if (provenance.length > 0) {
    const list = document.createElement("ul");
    list.className = "lp-evidence-provenance";
    for (const link of provenance) {
      const item = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = link.href || "#";
      anchor.textContent = link.label || link.href || "(link)";
      item.appendChild(anchor);
      list.appendChild(item);
    }
    popup.appendChild(list);
  } else {
    const note = document.createElement("p");
    note.className = "lp-evidence-no-provenance";
    note.textContent = fragment._error || "No provenance links.";
    popup.appendChild(note);
  }
  const close = document.createElement("button");
  close.className = "lp-evidence-close";
  close.type = "button";
  close.textContent = "Close";
  close.addEventListener("click", () => closeEvidencePopup(rootEl));
  popup.appendChild(close);
  rootEl.appendChild(popup);
  return popup;
}
function closeEvidencePopup(rootEl) {
  const open = rootEl.querySelector(":scope > .lp-evidence-popup");
  if (open) open.remove();
}

// src/scitex_live_paper/_django/static/live_paper/js/event-log.js
function createEventLog() {
  return [];
}
function recordEvent(log, kind, payload) {
  const entry = {
    ts: (/* @__PURE__ */ new Date()).toISOString(),
    kind,
    payload: payload || {}
  };
  log.push(entry);
  return entry;
}
function exportSidecar(log, meta) {
  return {
    schema: "scitex-live-paper.event-log/v1",
    exported_at: (/* @__PURE__ */ new Date()).toISOString(),
    bundle: meta && meta.bundle || null,
    events: Array.isArray(log) ? log.slice() : []
  };
}
function downloadSidecar(log, meta, filename) {
  const sidecar = exportSidecar(log, meta);
  const blob = new Blob([JSON.stringify(sidecar, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "live-paper-events.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1e3);
  return sidecar;
}
async function persistSidecar(log, meta, options) {
  const apiBase = options && options.apiBase || "/api/";
  const sidecar = exportSidecar(log, meta);
  const response = await fetch(withBundleContext(apiBase + "event-log"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sidecar)
  });
  if (!response.ok) {
    throw new Error(
      "persistSidecar failed: HTTP " + response.status
    );
  }
  const receipt = await response.json();
  return { sidecar, receipt };
}
function bindEventLog(rootEl, log, meta) {
  const kinds = [
    "live-paper:claim",
    "live-paper:evidence-request",
    "live-paper:evidence-response"
  ];
  const handler = (event) => {
    recordEvent(log, event.type, event.detail || {});
  };
  for (const kind of kinds) {
    rootEl.addEventListener(kind, handler);
  }
  return () => {
    for (const kind of kinds) {
      rootEl.removeEventListener(kind, handler);
    }
  };
}

// src/scitex_live_paper/_django/static/live_paper/js/archive.js
function renderArchiveButton(rootEl, apiBase) {
  const host = rootEl.querySelector(".live-paper-header") || rootEl;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "lp-archive-button";
  btn.textContent = "Archive event log";
  btn.addEventListener("click", () => {
    void archiveEventLog(btn, rootEl, apiBase);
  });
  const status = document.createElement("span");
  status.className = "lp-archive-status";
  status.setAttribute("aria-live", "polite");
  host.appendChild(btn);
  host.appendChild(status);
  return btn;
}
async function archiveEventLog(btn, rootEl, apiBase) {
  const status = rootEl.querySelector(".lp-archive-status") || btn.parentElement.querySelector(".lp-archive-status");
  const log = rootEl._livePaperEventLog || [];
  const meta = { bundle: rootEl._livePaperBundle || null };
  const count = Array.isArray(log) ? log.length : 0;
  btn.disabled = true;
  try {
    const { receipt } = await persistSidecar(log, meta, { apiBase });
    if (status) {
      status.textContent = "Archived " + count + " events (server: " + receipt.filename + ")";
    }
  } catch (err) {
    try {
      downloadSidecar(log, meta);
    } catch (dlErr) {
      if (status) {
        status.textContent = "Archive failed: " + String(err);
      }
      btn.disabled = false;
      return;
    }
    if (status) {
      status.textContent = "Saved " + count + " events (download \u2014 server persist failed: " + String(err) + ")";
    }
  }
  btn.disabled = false;
}

// src/scitex_live_paper/_django/static/live_paper/js/empty-state.js
function isMissingPaper(reason) {
  return /no paper selected|bundle not found|bundle path|not pinned/i.test(
    String(reason || "")
  );
}
function renderEmptyState(rootEl, reason) {
  const host = rootEl.querySelector(".live-paper-status") || rootEl;
  const panel = document.createElement("section");
  panel.className = "lp-empty-state";
  const title = document.createElement("h2");
  title.textContent = "No paper selected";
  const detail = document.createElement("p");
  detail.className = "lp-empty-reason";
  detail.textContent = String(reason || "No bundle is attached to this view.");
  const help = document.createElement("p");
  help.className = "lp-empty-help";
  help.textContent = "Open a paper from your workspace file browser, or append '?working_dir=/absolute/path/to/bundle' to this URL.";
  panel.appendChild(title);
  panel.appendChild(detail);
  panel.appendChild(help);
  host.appendChild(panel);
  return panel;
}

// src/scitex_live_paper/_django/static/live_paper/js/viewer.js
var pdfjsUrl = new URL("../pdfjs/pdf.min.mjs", import.meta.url).href;
var pdfjsWorkerUrl = new URL(
  "../pdfjs/pdf.worker.min.mjs",
  import.meta.url
).href;
var root = document.getElementById("live-paper-root");
if (!root) {
  console.error("[live-paper] root element missing");
} else {
  boot(root);
}
async function boot(rootEl) {
  const apiBase = normalizeBase(rootEl.getAttribute("data-api-base") || "/api/");
  movePickerIntoHeaderSlot(rootEl);
  const emptyReason = rootEl.getAttribute("data-empty-reason") || "";
  if (emptyReason) {
    hideLoading(rootEl);
    renderEmptyState(rootEl, emptyReason);
    return;
  }
  bindPortEvents(rootEl, apiBase);
  const eventLog = createEventLog();
  bindEventLog(rootEl, eventLog);
  rootEl._livePaperEventLog = eventLog;
  try {
    renderArchiveButton(rootEl, apiBase);
  } catch (err) {
    console.warn("[live-paper] archive button render failed", err);
  }
  let pdfjs;
  let createPdfViewer;
  try {
    const factoryUrl = rootEl.dataset.pdfFactory;
    if (!factoryUrl) throw new Error("SDK PDF factory URL missing");
    ({ createPdfViewer } = await import(factoryUrl));
    pdfjs = await import(pdfjsUrl);
    pdfjs.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl;
  } catch (err) {
    console.error("[live-paper] PDF.js failed to load", err);
    renderError("PDF.js bundle not available at " + pdfjsUrl);
    return;
  }
  let bundleInfo = null;
  let claimsPayload = null;
  try {
    const ping = await fetchJson(apiBase + "ping");
    if (!ping || ping.ok !== true) {
      throw new Error("ping returned non-ok: " + JSON.stringify(ping));
    }
    const dash = await fetchOrNull(apiBase + "dashboard");
    if (dash && dash.bundle && dash.claims) {
      bundleInfo = dash.bundle;
      claimsPayload = dash.claims;
    } else {
      bundleInfo = await fetchJson(apiBase + "bundle-info");
      claimsPayload = await fetchJson(apiBase + "claims");
    }
    setStatus(bundleInfo);
    renderReReviewBadge(rootEl, bundleInfo);
    rootEl._livePaperBundle = bundleInfo;
  } catch (err) {
    console.error("[live-paper] boot RPCs failed", err);
    if (isMissingPaper(String(err && err.message || err))) {
      hideLoading(rootEl);
      renderEmptyState(rootEl, String(err && err.message || err));
    } else {
      setStatus({ error: String(err) });
    }
  }
  if (claimsPayload) {
    try {
      renderClaimsSidebar(rootEl, claimsPayload, apiBase);
    } catch (err) {
      console.warn("[live-paper] claims sidebar render failed", err);
    }
  }
  rootEl.addEventListener("live-paper:claim", (event) => {
    const id = event && event.detail ? event.detail.id : null;
    const claims = claimsPayload && Array.isArray(claimsPayload.claims) ? claimsPayload.claims : [];
    const claim = claims.find((c) => c && c.claim_id === id);
    if (!claim) return;
    try {
      renderClaimDetail(ensureClaimsSidebar(rootEl), claim, apiBase);
    } catch (err) {
      console.warn("[live-paper] anchor detail render failed", err);
    }
  });
  const pdfContainer = ensurePdfContainer(rootEl);
  const viewer = new PDFViewer({
    container: pdfContainer,
    pdfjs,
    createPdfViewer,
    workerSrc: pdfjsWorkerUrl,
    apiBase
  });
  if (claimsPayload && Array.isArray(claimsPayload.claims)) {
    viewer.setClaims(claimsPayload.claims);
  }
  try {
    viewer.setComments(await fetchComments(apiBase));
  } catch (err) {
    console.warn("[live-paper] comments boot fetch failed", err);
  }
  await viewer.load();
}
function movePickerIntoHeaderSlot(rootEl) {
  const headerRoot = rootEl.previousElementSibling;
  if (!headerRoot?.matches("[data-stx-app-header]")) return;
  const picker = headerRoot.querySelector("[data-stx-project-picker]");
  if (!picker) return;
  const move = () => {
    const slot = headerRoot.querySelector(".stx-app-header__slot--project-selector");
    if (picker && slot && picker.parentElement !== slot) {
      slot.appendChild(picker);
      return true;
    }
    return Boolean(picker && slot);
  };
  if (move()) return;
  const observer = new MutationObserver(() => {
    if (move()) observer.disconnect();
  });
  observer.observe(headerRoot, { childList: true, subtree: true });
}
window.LivePaperPDFViewer = PDFViewer;
export {
  movePickerIntoHeaderSlot
};
