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
  if (!header || !payload?.error) return;
  header.hidden = false;
  header.className = "lp-bundle-header lp-bundle-error";
  header.textContent = "Couldn't load manuscript information: " + payload.error;
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
  host.hidden = false;
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

// src/scitex_live_paper/_django/static/live_paper/js/share.js
function bindShare(root2) {
  const share = root2.querySelector(".lp-share");
  const page = new URL(location.href);
  const project = root2.dataset.viewProject || page.searchParams.get("project");
  if (page.searchParams.has("working_dir") && !root2.dataset.viewProject) return;
  const button = share.querySelector("button");
  const status = share.querySelector('[role="status"]');
  const input = share.querySelector("input");
  share.hidden = false;
  button.addEventListener("click", async () => {
    const link = new URL(page.pathname, page.origin);
    if (project) link.searchParams.set("project", project);
    link.searchParams.set("shared", "1");
    const panel = root2.querySelector("#lp-selection-panel:not([hidden])");
    const claim = panel?.closest("#live-paper-claims").dataset.pinnedClaim;
    if (claim) link.searchParams.set("claim", claim);
    input.hidden = true;
    try {
      await navigator.clipboard.writeText(link.href);
      status.textContent = claim ? "Claim link copied." : "Paper link copied.";
    } catch {
      input.value = link.href;
      input.hidden = false;
      input.focus();
      input.select();
      status.textContent = "Copy the selected link.";
    }
  });
  return status;
}
function openSharedClaim(root2, claims, status) {
  const params = new URL(location.href).searchParams;
  const claim = params.get("claim");
  if (params.get("shared") !== "1" || !claim) return;
  if (!claims.some((entry) => entry.claim_id === claim)) {
    if (status) status.textContent = "This claim is unavailable in the current paper.";
    return;
  }
  const anchor = root2.querySelector('[data-overlay-id="' + CSS.escape(claim) + '"]');
  if (anchor) {
    anchor.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    anchor.click();
  } else {
    root2.dispatchEvent(new CustomEvent("live-paper:claim", { bubbles: true, detail: { id: claim } }));
  }
  const toggle = root2.querySelector(".lp-reader-evidence-toggle");
  if (getComputedStyle(toggle).display !== "none" && toggle.getAttribute("aria-expanded") === "false") {
    toggle.click();
  }
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
  let selectedOverlayId = null;
  const feed = createFeed(options.feedContainer, chooseFeedEntry, ports.feed?.renderEntry);
  const emit = (event) => ports.events?.emit?.({ documentId: current?.id ?? null, ...event });
  const allow = (action, target) => {
    const canonical = target?.overlayId ? overlays.find((item) => item.id === target.overlayId) : null;
    return Boolean(current && !current.readonly && !disposed && !target?.readonly && !canonical?.readonly && ports.policy?.canMutate?.({ document: current, action, target }) !== false);
  };
  const preview = ports.preview && createOverlayPreview(container, ports.preview);
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
  function rectStyle(element2, surface, bbox) {
    const [x0, y0, x1, y1] = surface.pdfToViewportRect(bbox);
    Object.assign(element2.style, { position: "absolute", left: `${Math.min(x0, x1)}px`, top: `${Math.min(y0, y1)}px`, width: `${Math.abs(x1 - x0)}px`, height: `${Math.abs(y1 - y0)}px`, pointerEvents: "auto" });
  }
  function paint(page) {
    const surface = pages.get(page);
    if (!surface?.element.isConnected || disposed) return;
    const previousLayer = layers.get(page);
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
      if (overlay.appearance) button.dataset.appearance = overlay.appearance;
      if (overlay.id === selectedOverlayId) button.setAttribute("aria-current", "true");
      button.setAttribute("aria-label", overlay.label || `Overlay ${overlay.id}`);
      if (preview) {
        button.setAttribute("aria-haspopup", "dialog");
        button.setAttribute("aria-expanded", "false");
      } else button.title = overlay.label || overlay.id;
      rectStyle(button, surface, overlay.bbox);
      const count = comments.filter((comment) => comment.target?.overlayId === overlay.id).length;
      if (count) {
        const badge = document.createElement("span");
        badge.className = "lp-rich-comment-count";
        badge.textContent = `\u270E${count}`;
        button.append(badge);
      }
      const target = { overlayId: overlay.id, page, bbox: overlay.bbox, readonly: overlay.readonly };
      button.addEventListener("click", () => {
        if (preview) {
          selectOverlay(overlay.id);
          feed?.selectOverlay(overlay.id);
          preview.show(button, overlay, true);
          emit({ type: "overlay-select", target, overlay });
        } else selectTarget(target, button, overlay);
      });
      for (const type of ["pointerenter", "focus"]) {
        button.addEventListener(type, (event) => {
          if (event.pointerType === "touch") return;
          preview?.show(button, overlay);
          emit({ type: "overlay-preview", overlay });
        });
      }
      for (const type of ["pointerleave", "blur"]) {
        button.addEventListener(type, () => preview?.leave(button));
      }
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
    preview?.reanchor(previousLayer, layer);
    previousLayer?.remove();
  }
  function selectOverlay(overlayId) {
    selectedOverlayId = overlayId ?? null;
    for (const layer of layers.values()) {
      for (const element2 of layer.querySelectorAll("[data-overlay-id]")) {
        if (element2.dataset.overlayId === selectedOverlayId) {
          element2.setAttribute("aria-current", "true");
        } else {
          element2.removeAttribute("aria-current");
        }
      }
    }
  }
  function chooseFeedEntry(entry) {
    preview?.close();
    const overlay = overlays.find((item) => item.id === entry.overlayId);
    selectOverlay(overlay?.id);
    if (overlay && ports.feed?.navigate) {
      ports.feed.navigate(overlay);
    } else {
      const anchor = [...layers.get(overlay?.page)?.children ?? []].find((element2) => element2.dataset.overlayId === entry.overlayId);
      anchor?.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
    emit({ type: "feed-select", entry, overlay: overlay ?? null });
  }
  function selectTarget(target, anchor, overlay = null) {
    if (disposed || !current) return;
    popup?.remove();
    selectOverlay(target.overlayId);
    feed?.selectOverlay(target.overlayId);
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
    const requests = [
      Promise.resolve().then(() => ports.overlays?.list?.(document2) ?? overlays),
      Promise.resolve().then(() => ports.comments?.list?.(document2) ?? comments),
      Promise.resolve().then(() => feed && ports.feed?.list?.(document2))
    ];
    const values = await Promise.allSettled(requests);
    if (disposed || token !== sequence) return;
    if (values[0].status === "fulfilled") overlays = [...values[0].value || []];
    else emit({ type: "port-error", port: "overlays", error: values[0].reason });
    if (values[1].status === "fulfilled") comments = [...values[1].value || []];
    else emit({ type: "port-error", port: "comments", error: values[1].reason });
    if (values[2].status === "rejected") {
      emit({ type: "port-error", port: "feed", error: values[2].reason });
    } else if (values[2].value != null) {
      feed?.setEntries(values[2].value);
    }
    repaint();
  }
  async function load(key) {
    if (disposed) throw new Error("PDF provider has been destroyed");
    const token = ++sequence;
    preview?.close();
    popup?.remove();
    popup = null;
    current = null;
    selectedOverlayId = null;
    feed?.reset();
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
    preview?.close();
    feed?.destroy();
    for (const layer of layers.values()) layer.remove();
    layers.clear();
    pages.clear();
    renderer.destroy();
  }
  return {
    renderer,
    load,
    refresh,
    setOverlays,
    setComments,
    setFeedFilter: (filter) => feed?.setFilter(filter),
    selectOverlay,
    selectTarget,
    createComment,
    destroy
  };
}
function createOverlayPreview(container, port) {
  let active = null;
  let timer;
  let restoringFocus = false;
  function close(restore = false) {
    clearTimeout(timer);
    if (!active) return;
    const { anchor, panel, listeners } = active;
    active = null;
    listeners.abort();
    anchor.setAttribute("aria-expanded", "false");
    panel.remove();
    if (restore && anchor.isConnected) {
      restoringFocus = true;
      anchor.focus({ preventScroll: true });
      restoringFocus = false;
    }
  }
  function leave(anchor) {
    clearTimeout(timer);
    if (!active || active.anchor !== anchor || active.pinned) return;
    timer = setTimeout(() => close(), 180);
  }
  function show(anchor, overlay, pin = false) {
    if (restoringFocus) return;
    clearTimeout(timer);
    if (active?.anchor === anchor) {
      if (pin) {
        active.pinned = true;
        active.panel.focus({ preventScroll: true });
      }
      return;
    }
    if (active?.pinned && !pin) return;
    close();
    const panel = document.createElement("section");
    panel.className = "lp-rich-preview";
    panel.setAttribute("popover", "manual");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", overlay.label || "PDF evidence");
    panel.tabIndex = -1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lp-rich-preview-close";
    button.setAttribute("aria-label", "Close evidence preview");
    button.textContent = "\xD7";
    button.addEventListener("click", () => close(true));
    const content = document.createElement("div");
    panel.append(button, content);
    container.append(panel);
    panel.showPopover?.();
    const listeners = new AbortController();
    const { signal } = listeners;
    active = { anchor, panel, listeners, pinned: pin, place };
    anchor.setAttribute("aria-expanded", "true");
    function place() {
      const rect = active?.anchor.getBoundingClientRect();
      if (!rect) return;
      const margin = 8;
      const horizontal = rect.right + panel.offsetWidth + margin <= innerWidth ? rect.right + margin : rect.left - panel.offsetWidth - margin;
      const hasSideRoom = horizontal >= margin && rect.width < innerWidth / 2;
      const left = hasSideRoom ? horizontal : rect.left;
      const top = hasSideRoom ? rect.top : rect.bottom + margin;
      panel.style.left = Math.max(margin, Math.min(left, innerWidth - panel.offsetWidth - margin)) + "px";
      panel.style.top = Math.max(margin, Math.min(top, innerHeight - panel.offsetHeight - margin)) + "px";
    }
    const resize = new ResizeObserver(place);
    resize.observe(panel);
    signal.addEventListener("abort", () => resize.disconnect(), { once: true });
    panel.addEventListener("pointerenter", () => clearTimeout(timer));
    panel.addEventListener("pointerleave", () => leave(active?.anchor));
    panel.addEventListener("focusin", () => clearTimeout(timer));
    panel.addEventListener("focusout", (event) => {
      if (!panel.contains(event.relatedTarget) && event.relatedTarget !== active?.anchor) leave(active?.anchor);
    });
    document.addEventListener("scroll", place, { capture: true, signal });
    window.addEventListener("resize", place, { signal });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close(active.pinned || panel.contains(document.activeElement));
      }
    }, { signal });
    document.addEventListener("pointerdown", (event) => {
      if (!active?.anchor.contains(event.target) && !panel.contains(event.target)) close();
    }, { signal });
    port.render(content, overlay, signal);
    place();
    if (pin) panel.focus({ preventScroll: true });
  }
  function reanchor(previousLayer, newLayer) {
    if (!active || !previousLayer?.contains(active.anchor)) return;
    const { anchor } = active;
    const replacement = [...newLayer.children].find(
      (element2) => element2.dataset.overlayId === anchor.dataset.overlayId
    );
    if (!replacement) {
      close();
      return;
    }
    active.anchor = replacement;
    replacement.setAttribute("aria-expanded", "true");
    if (document.activeElement === anchor) replacement.focus({ preventScroll: true });
    active.place();
  }
  return { show, leave, close, reanchor };
}
function validBox(box) {
  return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite);
}
function sameTarget(left, right) {
  if (left?.overlayId || right?.overlayId) return Boolean(left?.overlayId && left.overlayId === right?.overlayId);
  return left?.page === right?.page && JSON.stringify(left?.bbox) === JSON.stringify(right?.bbox);
}
function createFeed(container, choose, renderEntry) {
  if (!container) return null;
  const list = container.ownerDocument.createElement("ul");
  list.className = "scitex-rich-pdf-feed";
  container.append(list);
  let rows = [];
  let selected = null;
  let filter = null;
  function updateVisibility() {
    for (const row of rows) row.element.hidden = filter ? !filter(row.entry) : false;
  }
  function select(row, scroll = false) {
    selected?.button.removeAttribute("aria-current");
    selected = row ?? null;
    selected?.button.setAttribute("aria-current", "true");
    if (scroll && selected && !selected.element.hidden) selected.element.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
  function setEntries(entries) {
    const selectedId = selected?.entry.id;
    select(null);
    rows = entries.map((entry) => {
      const element2 = list.ownerDocument.createElement("li");
      const button = list.ownerDocument.createElement("button");
      button.type = "button";
      button.textContent = entry.label;
      const row = { entry, element: element2, button };
      button.addEventListener("click", () => {
        select(row);
        choose(entry);
      });
      element2.append(button);
      const content = renderEntry?.(entry);
      if (content) element2.append(content);
      return row;
    });
    updateVisibility();
    list.replaceChildren(...rows.map((row) => row.element));
    select(rows.find((row) => row.entry.id === selectedId));
  }
  return {
    setEntries,
    setFilter(nextFilter) {
      filter = nextFilter;
      updateVisibility();
    },
    selectOverlay(overlayId) {
      if (overlayId != null) select(rows.find((row) => row.entry.overlayId === overlayId), true);
    },
    reset() {
      setEntries([]);
    },
    destroy() {
      list.remove();
    }
  };
}
function createPdfNavigation({ container, pdfjs, onDocument }) {
  const controls = document.createElement("div");
  controls.className = "rpdf-nav-controls";
  const content = document.createElement("div");
  content.className = "rpdf-nav-content";
  container.classList.add("rpdf-navigation");
  container.hidden = false;
  const titlebar = document.createElement("div");
  titlebar.className = "rpdf-nav-titlebar";
  const title = document.createElement("span");
  title.textContent = "Pages & bookmarks";
  const toggle = control("", () => setOpen(container.hasAttribute("data-collapsed")));
  toggle.className = "rpdf-nav-toggle";
  content.id = container.id + "-content";
  toggle.setAttribute("aria-controls", content.id);
  titlebar.append(title, toggle);
  container.replaceChildren(titlebar, controls, content);
  const pagePanel = document.createElement("div");
  const bookmarkPanel = document.createElement("div");
  content.append(pagePanel, bookmarkPanel);
  const pageTab = control("Pages", () => select("pages"));
  const bookmarkTab = control("Bookmarks", () => select("bookmarks"));
  controls.append(pageTab, bookmarkTab);
  let generation = 0;
  let observer;
  let ready = false;
  let destination;
  const surfaces = /* @__PURE__ */ new Map();
  const events = new AbortController();
  function control(label, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
  }
  function select(view) {
    const pages = view === "pages";
    pagePanel.hidden = !pages;
    bookmarkPanel.hidden = pages;
    pageTab.setAttribute("aria-pressed", String(pages));
    bookmarkTab.setAttribute("aria-pressed", String(!pages));
    content.scrollTop = 0;
  }
  function setOpen(open) {
    container.toggleAttribute("data-collapsed", !open);
    title.hidden = controls.hidden = content.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "\u2039" : "\u203A";
    toggle.title = open ? "Minimize PDF navigation" : "Expand PDF navigation";
    toggle.setAttribute("aria-label", toggle.title);
  }
  container.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || container.hasAttribute("data-collapsed")) return;
    setOpen(false);
    toggle.focus();
    event.stopPropagation();
  }, { signal: events.signal });
  select("pages");
  setOpen(true);
  function choose(target) {
    destination = target;
    jump();
  }
  function jump() {
    if (!destination) return;
    const surface = surfaces.get(destination.page);
    if (!surface?.element.isConnected) return;
    const scrollRoot = surface.element.ownerDocument.scrollingElement;
    const scroller = closestScrollContainer(surface.element) || scrollRoot;
    if (destination.bbox && scroller) {
      const [, y0, , y1] = surface.pdfToViewportRect(destination.bbox);
      const y = Math.min(y0, y1);
      const inset = Math.max(12, (scroller.clientHeight - Math.abs(y1 - y0)) / 2);
      const scrollerTop = scroller === scrollRoot ? 0 : scroller.getBoundingClientRect().top;
      scroller.scrollTo({
        top: scroller.scrollTop + surface.element.getBoundingClientRect().top - scrollerTop + y - inset,
        behavior: "instant"
      });
    } else if (scroller) {
      const [, offset] = Number.isFinite(destination.top) ? surface.pdfToViewportPoint(destination.left ?? 0, destination.top) : [0, 0];
      const top = scroller.scrollTop + surface.element.getBoundingClientRect().top - (scroller === scrollRoot ? 0 : scroller.getBoundingClientRect().top);
      scroller.scrollTo({ top: top + offset - 12 });
    } else {
      surface.element.scrollIntoView({ block: "start" });
    }
    if (ready) destination = null;
  }
  function renderPages(pdf, current) {
    const list = document.createElement("ol");
    list.className = "rpdf-nav-pages";
    observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        const page = Number(entry.target.dataset.page);
        void renderThumbnail(pdf, page, entry.target, () => current === generation).catch(() => {
        });
      }
    }, { root: content, rootMargin: "100px 0px" });
    for (let page = 1; page <= pdf.numPages; page += 1) {
      const row = document.createElement("li");
      const button = control("Page " + page, () => choose({ page }));
      const canvas = document.createElement("canvas");
      canvas.width = 112;
      canvas.height = 146;
      canvas.dataset.page = String(page);
      canvas.setAttribute("aria-hidden", "true");
      button.prepend(canvas);
      row.append(button);
      list.append(row);
      observer.observe(canvas);
    }
    pagePanel.replaceChildren(list);
  }
  async function documentReady(pdf, current) {
    if (current !== generation) return;
    renderPages(pdf, current);
    const items = await pdf.getOutline();
    const list = await renderPdfOutline(pdf, items ?? [], choose);
    if (current !== generation) return;
    bookmarkPanel.replaceChildren(list);
    if (!list.childElementCount) bookmarkPanel.textContent = "This PDF has no bookmarks.";
  }
  const runtime = {
    ...pdfjs,
    getDocument(...args) {
      const task = pdfjs.getDocument(...args);
      const current = ++generation;
      ready = false;
      destination = null;
      surfaces.clear();
      observer?.disconnect();
      pagePanel.textContent = "Loading pages\u2026";
      bookmarkPanel.textContent = "Loading bookmarks\u2026";
      task.promise.then((pdf) => {
        void documentReady(pdf, current).catch(() => {
          if (current === generation) bookmarkPanel.textContent = "Bookmarks unavailable.";
        });
        if (current === generation && onDocument) onDocument(pdf);
      }, () => {
        if (current !== generation) return;
        pagePanel.textContent = "Pages unavailable.";
        bookmarkPanel.textContent = "Bookmarks unavailable.";
      });
      return task;
    }
  };
  return {
    runtime,
    goTo: choose,
    pageRendered(page, surface) {
      surfaces.set(page, surface);
      if (destination?.page === page) jump();
    },
    finishRender() {
      ready = true;
      jump();
    },
    destroy() {
      generation += 1;
      events.abort();
      observer?.disconnect();
      surfaces.clear();
      container.replaceChildren();
      container.hidden = true;
    }
  };
}
function closestScrollContainer(element2) {
  for (let parent = element2.parentElement; parent; parent = parent.parentElement) {
    if (["auto", "scroll"].includes(getComputedStyle(parent).overflowY)) return parent;
  }
  return null;
}
async function renderThumbnail(pdf, number2, canvas, isCurrent) {
  const page = await pdf.getPage(number2);
  if (!isCurrent() || !canvas.isConnected) return;
  const view = page.getViewport({ scale: 1 });
  const viewport = page.getViewport({ scale: Math.min(112 / view.width, 146 / view.height) });
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
}
async function renderPdfOutline(pdf, items, choose) {
  const list = document.createElement("ul");
  list.className = "rpdf-nav-bookmarks";
  for (const item of items) {
    const dest = typeof item.dest === "string" ? await pdf.getDestination(item.dest) : item.dest;
    const row = document.createElement("li");
    const target = await pdfOutlineTarget(pdf, dest);
    const title = document.createElement(target ? "button" : "span");
    title.textContent = item.title;
    if (target) {
      title.type = "button";
      title.addEventListener("click", () => choose(target));
    }
    row.append(title);
    if (item.items?.length) row.append(await renderPdfOutline(pdf, item.items, choose));
    list.append(row);
  }
  return list;
}
async function pdfOutlineTarget(pdf, dest) {
  if (!Array.isArray(dest)) return null;
  const [ref, mode, left, top] = dest;
  try {
    const index = Number.isInteger(ref) ? ref : ref ? await pdf.getPageIndex(ref) : -1;
    if (index < 0 || index >= pdf.numPages) return null;
    return {
      page: index + 1,
      left: mode?.name === "XYZ" ? left : null,
      top: mode?.name === "XYZ" ? top : mode?.name === "FitH" ? left : null
    };
  } catch {
    return null;
  }
}

// src/scitex_live_paper/_django/static/live_paper/js/claim-overlays.js
function pickAnchor(claim) {
  return claim?.anchor ?? claim?.extras?.anchor ?? null;
}

// src/scitex_live_paper/_django/static/live_paper/js/bibliography-highlights.js
function createBibliographyHighlights(citations = {}, onSelect) {
  const pages = /* @__PURE__ */ new Map();
  let references = /* @__PURE__ */ new Map();
  let activeDocument;
  function select(key, goToReference) {
    onSelect?.(key, Object.hasOwn(citations, key) ? citations[key] : { status: "unknown" }, goToReference);
  }
  function mark(node, key) {
    node.dataset.citationKey = key;
    node.dataset.status = Object.hasOwn(citations, key) ? citations[key].status : "unknown";
    node.title = key + " \xB7 " + node.dataset.status;
  }
  return {
    documentLoaded(pdf) {
      activeDocument = pdf;
      pages.clear();
      references = /* @__PURE__ */ new Map();
      void pdf.getDestinations().then(async (destinations) => {
        const resolved = /* @__PURE__ */ new Map();
        for (const [name, dest] of Object.entries(destinations ?? {})) {
          if (!name.startsWith("cite.") || !Array.isArray(dest)) continue;
          const [ref, mode, left, top] = dest;
          if (mode?.name !== "XYZ" || !Number.isFinite(left) || !Number.isFinite(top)) continue;
          const index = Number.isInteger(ref) ? ref : await pdf.getPageIndex(ref).catch(() => -1);
          if (index < 0 || index >= pdf.numPages) continue;
          const page = resolved.get(index + 1) ?? [];
          page.push({ left, top, key: name.slice(5) });
          resolved.set(index + 1, page);
        }
        if (pdf !== activeDocument) return;
        references = resolved;
        for (const [page, surface] of pages) markReferences(surface, references.get(page), mark, select);
      }).catch((error) => console.warn("[pdf-viewer] bibliography destinations unavailable", error));
    },
    pageRendered(page, surface) {
      pages.set(page, surface);
      markReferences(surface, references.get(page), mark, select);
      const pdf = activeDocument;
      if (!surface.element.querySelector('[data-stx-pdf-layer="links"]') || !pdf) return;
      void pdf.getPage(page).then((proxy) => proxy.getAnnotations({ intent: "display" })).then((annotations) => {
        if (pdf === activeDocument && pages.get(page) === surface) {
          markCitationLinks(surface, annotations, mark, select);
        }
      }).catch((error) => console.warn("[pdf-viewer] citation links unavailable", error));
    }
  };
}
function markReferences(surface, references, mark, select) {
  if (!references?.length) return;
  const origin = surface.element.getBoundingClientRect();
  const spans = [...surface.element.querySelectorAll('[data-stx-pdf-layer="text"] span')].filter((span) => !span.childElementCount && span.textContent.trim()).map((span) => ({ span, bounds: span.getBoundingClientRect() }));
  for (const reference of references) {
    const [x, y] = surface.pdfToViewportPoint(reference.left, reference.top);
    const start = spans.find(
      ({ bounds }) => Math.abs(bounds.left - origin.x - x) < bounds.height * 0.7 && Math.abs(bounds.top - origin.y - y) < bounds.height * 0.65
    );
    if (!start) continue;
    for (const { span, bounds } of spans) {
      if (bounds.left >= start.bounds.left - 1 && Math.abs(bounds.top - start.bounds.top) < start.bounds.height * 0.45) {
        span.classList.add("lp-bibliography-highlight");
        mark(span, reference.key);
        if (span === start.span) {
          span.setAttribute("role", "button");
          span.setAttribute("aria-label", "Inspect reference " + reference.key + " (" + span.dataset.status + ")");
          span.tabIndex = 0;
          span.onkeydown = (event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            select(reference.key);
          };
        }
        span.onclick = () => {
          if (window.getSelection()?.isCollapsed !== false) select(reference.key);
        };
      }
    }
  }
}
function markCitationLinks(surface, annotations, mark, select) {
  const links = [...surface.element.querySelectorAll('[data-stx-pdf-layer="links"] > a')];
  for (const annotation of annotations) {
    let inspect = function(event) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      select(key, () => {
        link.removeEventListener("click", inspect, true);
        link.click();
        link.addEventListener("click", inspect, true);
      });
    };
    if (annotation.subtype !== "Link" || typeof annotation.dest !== "string" || !annotation.dest.startsWith("cite.") || !Array.isArray(annotation.rect)) continue;
    const [x0, y0, x1, y1] = surface.pdfToViewportRect(annotation.rect);
    const rect = [Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)];
    const link = links.find((item) => !item.dataset.citationKey && ["left", "top", "width", "height"].every((prop, index) => Math.abs(parseFloat(item.style[prop]) - rect[index]) < 0.5));
    if (!link) continue;
    const key = annotation.dest.slice(5);
    mark(link, key);
    link.setAttribute("aria-label", "Inspect citation " + key + " (" + link.dataset.status + ")");
    link.addEventListener("click", inspect, true);
  }
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
  const input = el("textarea", "stx-textarea lp-comments-input");
  input.rows = 2;
  input.placeholder = "Add a comment on this claim\u2026";
  input.setAttribute("aria-label", "New comment");
  const row = el("div", "lp-comments-form-row");
  const author = el("input", "stx-input lp-comments-author");
  author.placeholder = "name (optional)";
  author.setAttribute("aria-label", "Author name");
  const submit = el("button", "stx-button stx-button--primary", "Comment");
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

// src/scitex_live_paper/_django/static/live_paper/js/statistics-preview.js
var MISSING = "\u2014";
function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== void 0) node.textContent = text;
  return node;
}
function number(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return MISSING;
  return value !== 0 && Math.abs(value) < 1e-3 ? value.toExponential(3) : Number(value.toPrecision(5)).toString();
}
function effect(row) {
  if (typeof row.effect_size !== "number") return MISSING;
  const result = [row.effect_size_metric, number(row.effect_size)].filter(Boolean).join(" ");
  const interval = Array.isArray(row.effect_ci) ? row.effect_ci.map(number).join(" \u2013 ") : "";
  return interval ? result + " [" + interval + "]" : result;
}
function resultTable(rows) {
  const wrap = element("div");
  wrap.className = "lp-stats-table-scroll";
  const table = element("table");
  const header = table.createTHead().insertRow();
  const hasInterval = rows.some((row) => Array.isArray(row?.ci));
  const headers = ["Test", "Role", "Statistic", "df", "p", "Effect size"];
  if (hasInterval) headers.push("Confidence interval");
  for (const label of headers) {
    const heading = element("th", label);
    heading.scope = "col";
    header.append(heading);
  }
  const body = table.createTBody();
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const values = [
      row.method || row.label || row.test_method || row.test || MISSING,
      typeof row.role === "string" && row.role ? row.role[0].toUpperCase() + row.role.slice(1) : MISSING,
      number(row.statistic),
      Array.isArray(row.df) ? row.df.map(number).join(", ") : number(row.df),
      number(row.p_value ?? row.pvalue),
      effect(row)
    ];
    if (hasInterval) values.push(Array.isArray(row.ci) ? row.ci.map(number).join(" \u2013 ") : MISSING);
    const tr = body.insertRow();
    for (const value of values) tr.insertCell().textContent = value;
  }
  wrap.append(table);
  return wrap;
}
function appendApa(node, segments, plain) {
  if (!Array.isArray(segments) || !segments.length) {
    node.textContent = plain;
    return;
  }
  for (const segment of segments) {
    if (typeof segment?.text !== "string") continue;
    const tag = { sym: "i", sup: "sup", sub: "sub" }[segment.kind];
    node.append(tag ? element(tag, segment.text) : segment.text);
  }
}
function detailedResult(row, open) {
  const rows = row.apa_table ?? row.apa?.table;
  if (!Array.isArray(rows) || !rows.length) return null;
  const detail = element("details");
  detail.open = open;
  detail.append(element("summary", row.method || row.label || row.test_method || row.test));
  const table = element("table");
  const body = table.createTBody();
  for (const row2 of rows) {
    if (typeof row2?.label_plain !== "string" || typeof row2.value_plain !== "string") continue;
    const tr = body.insertRow();
    const label = element("th");
    label.scope = "row";
    const value = element("td");
    appendApa(label, row2.label, row2.label_plain);
    appendApa(value, row2.value, row2.value_plain);
    tr.append(label, value);
  }
  detail.append(table);
  return detail;
}
function renderStatistics(panel, data, loadPlot) {
  if (!data || typeof data !== "object") return;
  const card = element("section");
  card.className = "lp-stats-card";
  card.setAttribute("aria-label", "SciTeX Stats");
  card.append(element("h3", "SciTeX Stats"));
  if (data.missing_effect_sizes?.length) {
    const incomplete = element("p", "Incomplete report \xB7 effect size required for " + data.missing_effect_sizes.join(", "));
    incomplete.setAttribute("role", "status");
    card.append(incomplete);
  }
  const comparisons = Object.values(data.comparisons || {});
  for (const study of comparisons) {
    if (!study || !Array.isArray(study.results) || !study.results.length) continue;
    const group = element("section");
    if (study.title) group.append(element("h4", study.title));
    if (study.note) group.append(element("p", study.note));
    const first = study.results[0] || {};
    const alpha = study.alpha ?? first.alpha;
    const power = study.power ?? first.power;
    const beta = study.beta ?? first.beta;
    const thresholds = ["\u03B1 " + number(alpha), "\u03B2 " + (Number.isFinite(beta) ? number(beta) : "not estimated")];
    if (Number.isFinite(power)) thresholds.push("Power " + number(power));
    group.append(element("p", thresholds.join(" \xB7 ")), resultTable(study.results));
    for (const row of study.results) {
      const line = row?.apa_plain ?? row?.apa?.plain;
      if (typeof line === "string" && line) {
        const report = element("p");
        appendApa(report, row.apa_segments ?? row.apa?.segments, line);
        report.className = "lp-stats-reported-line";
        group.append(report);
      }
    }
    for (const [index, row] of study.results.entries()) {
      if (!row || typeof row !== "object") continue;
      const details = detailedResult(row, index === 0);
      if (details) group.append(details);
    }
    const check = study.assumptions;
    if (Number.isFinite(check?.min_expected)) {
      group.append(element(
        "p",
        "Expected counts \xB7 minimum " + number(check.min_expected) + " \xB7 " + check.cells_below + " of " + check.cells + " below " + number(check.threshold)
      ));
    } else if (Number.isFinite(first.expected_min)) {
      group.append(element("p", "Minimum expected count \xB7 " + number(first.expected_min)));
    }
    const checks = study.checks;
    if (Array.isArray(checks?.normality?.samples)) {
      for (const sample of checks.normality.samples) {
        if (!sample || !Number.isFinite(sample.p)) continue;
        group.append(element(
          "p",
          "Shapiro\u2013Wilk \xB7 " + sample.sample + " \xB7 W " + number(sample.W) + " \xB7 p " + number(sample.p)
        ));
      }
    }
    const variance = checks?.equal_variance?.brown_forsythe;
    if (Number.isFinite(variance?.p)) {
      group.append(element("p", "Brown\u2013Forsythe \xB7 F " + number(variance.statistic) + " \xB7 p " + number(variance.p)));
    }
    if (study.agreement) group.append(element("p", study.agreement));
    if (typeof study.visual === "string" && loadPlot) {
      const plot = element("figure");
      loadPlot(study.visual, plot, study.title, study.visual_sha256);
      group.append(plot);
    }
    card.append(group);
  }
  panel.append(card);
}

// src/scitex_live_paper/_renderer/assets/graph-controls.js
var zoomScopes = /* @__PURE__ */ new WeakMap();
var zoomKeys = { __proto__: null, "+": "in", "=": "in", "-": "out", "0": "reset" };
function bindScopedZoom(surface, zoom, signal) {
  if (!surface || signal?.aborted) return;
  const doc = surface.ownerDocument;
  let scope = zoomScopes.get(doc);
  if (!scope) {
    const listeners = new AbortController();
    scope = { handlers: /* @__PURE__ */ new WeakMap(), count: 0, listeners };
    zoomScopes.set(doc, scope);
    let pointer;
    const listenerOptions = { capture: true, signal: listeners.signal };
    const track = (event) => {
      pointer = { x: event.clientX, y: event.clientY };
    };
    doc.addEventListener("pointermove", track, listenerOptions);
    doc.addEventListener("pointerdown", track, listenerOptions);
    doc.addEventListener("pointerout", (event) => {
      if (event.relatedTarget === null) pointer = null;
    }, listenerOptions);
    doc.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || !(event.ctrlKey || event.metaKey) || event.altKey || event.isComposing) return;
      const action = zoomKeys[event.key];
      if (!action) return;
      let target = pointer === void 0 ? doc.activeElement : pointer && doc.elementFromPoint(pointer.x, pointer.y);
      for (; target; target = target.parentElement) {
        const handler = scope.handlers.get(target);
        if (!handler) continue;
        if (handler(action, pointer) !== false) event.preventDefault();
        return;
      }
    }, listenerOptions);
  }
  scope.handlers.set(surface, zoom);
  scope.count += 1;
  signal?.addEventListener("abort", () => {
    scope.handlers.delete(surface);
    scope.count -= 1;
    if (scope.count === 0) {
      scope.listeners.abort();
      zoomScopes.delete(doc);
    }
  }, { once: true });
}
function graphControls(viewport, signal) {
  const controls = document.createElement("div");
  controls.className = "lp-graph-controls";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "Evidence graph controls");
  viewport.tabIndex = 0;
  viewport.setAttribute("role", "region");
  viewport.setAttribute("aria-label", "Evidence graph viewport");
  let zoom = 1;
  const step = 0.25;
  const minimum = 0.5;
  const maximum = 4;
  function button(label, text, action) {
    const control = document.createElement("button");
    control.type = "button";
    control.className = "stx-button";
    control.setAttribute("aria-label", label);
    control.title = label;
    control.textContent = text;
    control.addEventListener("click", action);
    return control;
  }
  const out = button("Zoom out of evidence graph", "\u2212", () => resize(zoom - step));
  const inside = button("Zoom in on evidence graph", "+", () => resize(zoom + step));
  const reset = button("Reset evidence graph zoom", "Reset zoom", () => resize(1, true));
  const percent = document.createElement("output");
  controls.append(out, inside, reset, percent, downloadMenu(viewport));
  function updatePan() {
    viewport.toggleAttribute(
      "data-can-pan",
      viewport.scrollWidth > viewport.clientWidth || viewport.scrollHeight > viewport.clientHeight
    );
  }
  function resize(next, resetPosition = false, point) {
    const previous = zoom;
    zoom = Math.max(minimum, Math.min(maximum, next));
    const bounds = point && viewport.getBoundingClientRect();
    const centerX = bounds ? point.x - bounds.left : viewport.clientWidth / 2;
    const centerY = bounds ? point.y - bounds.top : viewport.clientHeight / 2;
    const x = (viewport.scrollLeft + centerX) * zoom / previous - centerX;
    const y = (viewport.scrollTop + centerY) * zoom / previous - centerY;
    viewport.style.setProperty("--lp-graph-zoom", String(zoom));
    viewport.scrollTo({
      left: resetPosition ? 0 : x,
      top: resetPosition ? 0 : y,
      behavior: "instant"
    });
    out.disabled = zoom <= minimum;
    inside.disabled = zoom >= maximum;
    percent.textContent = Math.round(zoom * 100) + "%";
    updatePan();
  }
  function shortcut(action, point) {
    if (action === "reset") resize(1, true);
    else resize(zoom + (action === "in" ? step : -step), false, point);
  }
  bindScopedZoom(viewport, shortcut, signal);
  bindScopedZoom(controls, (action) => shortcut(action), signal);
  resize(1);
  const observer = new ResizeObserver(updatePan);
  observer.observe(viewport);
  signal?.addEventListener("abort", () => observer.disconnect(), { once: true });
  let drag;
  viewport.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" || event.button !== 0 || !viewport.hasAttribute("data-can-pan") || event.target.closest('[role="button"], a')) return;
    drag = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      left: viewport.scrollLeft,
      top: viewport.scrollTop
    };
    viewport.focus({ preventScroll: true });
    viewport.setPointerCapture(event.pointerId);
    viewport.setAttribute("data-panning", "");
    event.preventDefault();
  });
  viewport.addEventListener("pointermove", (event) => {
    if (event.pointerId !== drag?.id) return;
    viewport.scrollTo({
      left: drag.left + drag.x - event.clientX,
      top: drag.top + drag.y - event.clientY,
      behavior: "instant"
    });
  });
  viewport.addEventListener("lostpointercapture", () => {
    drag = null;
    viewport.removeAttribute("data-panning");
  });
  return controls;
}
function downloadMenu(viewport) {
  const menu = document.createElement("details");
  const title = document.createElement("summary");
  title.textContent = "Download graph";
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  menu.append(title);
  for (const format of ["svg", "png"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "stx-button";
    button.textContent = format.toUpperCase();
    button.addEventListener("click", async () => {
      button.disabled = true;
      status.textContent = "";
      try {
        const svg = viewport.querySelector("svg");
        let blob;
        if (format === "svg") {
          blob = new Blob([graphSvg(svg)], { type: "image/svg+xml;charset=utf-8" });
        } else {
          const canvas = await graphCanvas(svg);
          blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        }
        if (!blob) throw new Error("Empty graph image");
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "evidence-graph." + format;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 3e4);
        menu.open = false;
        title.focus({ preventScroll: true });
      } catch {
        status.textContent = "Graph download failed. Try again.";
      } finally {
        button.disabled = false;
      }
    });
    menu.append(button);
  }
  menu.append(status);
  return menu;
}
function graphSize(svg) {
  const view = svg?.viewBox.baseVal;
  if (!view?.width || !view.height) throw new Error("Evidence graph is not ready.");
  return view;
}
function graphSvg(svg, scale = 1) {
  const view = graphSize(svg);
  const copy = svg.cloneNode(true);
  copy.removeAttribute("style");
  copy.setAttribute("width", Math.max(1, Math.ceil(view.width * scale)));
  copy.setAttribute("height", Math.max(1, Math.ceil(view.height * scale)));
  return new XMLSerializer().serializeToString(copy);
}
async function graphCanvas(svg) {
  const view = graphSize(svg);
  const scale = Math.min(2, 3800 / Math.max(view.width, view.height));
  const image = new Image();
  image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(graphSvg(svg, scale));
  await image.decode();
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Unable to render the evidence graph.");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0);
  return canvas;
}

// src/scitex_live_paper/_django/static/live_paper/js/claim-details.js
var graphSequence = 0;
var detailRequests = /* @__PURE__ */ new WeakMap();
function el2(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== void 0 && text !== null) node.textContent = text;
  return node;
}
function renderClaimDetail(sidebarEl, claim, apiBase, { refresh = false, goToPdf } = {}) {
  const selection = sidebarEl.querySelector("#lp-selection-panel");
  sidebarEl.querySelector("#lp-selection-tab").click();
  const active = selection.querySelector(".lp-claim-detail");
  if (!refresh && active?.dataset.claimId === claim.claim_id) return active;
  removeClaimDetail(sidebarEl);
  const pane = el2("div", "lp-claim-detail");
  pane.dataset.claimId = claim.claim_id;
  pane.setAttribute("role", "region");
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
  const relation = claim.extras?.evidence_relation ?? claim.extras?.metadata?.evidence_relation;
  if (relation === "author_interpretation") {
    pane.append(el2("p", "lp-claim-detail-status", "Author interpretation"));
  }
  const status = el2(
    "p",
    "lp-claim-detail-status",
    "status: " + (claim.status || "registered")
  );
  status.dataset.status = claim.status || "registered";
  pane.appendChild(status);
  if (goToPdf) {
    const jump = el2("button", "stx-button", "Show in PDF");
    jump.type = "button";
    jump.addEventListener("click", goToPdf);
    pane.append(jump);
  }
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
  const controller = new AbortController();
  detailRequests.set(pane, controller);
  pane.ownerDocument.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !event.defaultPrevented) closeClaimDetail(sidebarEl);
  }, { signal: controller.signal });
  renderEvidenceDetails(pane, claim, apiBase, controller.signal);
  try {
    const commentsBox = el2("div", "lp-claim-comments-slot");
    pane.appendChild(commentsBox);
    void renderCommentSection(commentsBox, claim.claim_id, apiBase);
  } catch (err) {
    console.warn("[live-paper] comments section failed:", err);
  }
  selection.append(pane);
  sidebarEl.scrollTop = 0;
  return pane;
}
function renderCitationDetail(sidebar, key, citation, apiBase, goToReference) {
  delete sidebar.dataset.pinnedClaim;
  removeClaimDetail(sidebar);
  sidebar.querySelector("#lp-selection-tab").click();
  const pane = el2("div", "lp-claim-detail");
  pane.setAttribute("role", "region");
  pane.setAttribute("aria-label", "Citation evidence");
  pane.append(el2("h3", "lp-evidence-preview-title", key));
  const badge = el2("p", "lp-citation-status", "Clew status \xB7 " + citation.status);
  badge.dataset.status = citation.status;
  pane.append(badge);
  if (citation.reason) pane.append(el2("p", "", citation.reason));
  if (citation.resolver_source) pane.append(el2("p", "", "Scholar provider \xB7 " + citation.resolver_source));
  if (citation.provenance) pane.append(el2("p", "", citation.provenance));
  if (citation.doi) pane.append(el2("p", "", "DOI \xB7 " + citation.doi));
  if (citation.link) {
    try {
      const url = new URL(citation.link);
      if (url.protocol === "https:" || url.protocol === "http:") {
        const source = el2("a", "stx-button", "Open source");
        source.href = url.href;
        source.target = "_blank";
        source.rel = "noopener noreferrer";
        pane.append(source);
      }
    } catch {
    }
  }
  if (goToReference) {
    const jump = el2("button", "stx-button", "Go to bibliography entry");
    jump.type = "button";
    jump.addEventListener("click", goToReference);
    pane.append(jump);
  }
  if (citation.claim_id) {
    const controller = new AbortController();
    detailRequests.set(pane, controller);
    renderEvidenceDetails(pane, { claim_id: citation.claim_id }, apiBase, controller.signal, true);
  } else {
    pane.append(el2("p", "lp-claim-dag-empty", "No Clew retrieval graph is recorded for this citation."));
  }
  const close = el2("button", "stx-button", "Close");
  close.type = "button";
  close.addEventListener("click", () => closeClaimDetail(sidebar));
  pane.append(close);
  sidebar.querySelector("#lp-selection-panel").append(pane);
  sidebar.scrollTop = 0;
}
function removeClaimDetail(sidebarEl) {
  const open = sidebarEl.querySelector("#lp-selection-panel > .lp-claim-detail");
  if (open) {
    detailRequests.get(open)?.abort();
    open.remove();
  }
}
function closeClaimDetail(sidebarEl) {
  delete sidebarEl.dataset.pinnedClaim;
  removeClaimDetail(sidebarEl);
  sidebarEl.querySelector("#lp-all-claims-tab").click();
}
function renderEvidencePreview(panel, claim, apiBase, signal) {
  panel.append(el2("h2", "lp-evidence-preview-title", claim.claim_value ?? claim.claim_id));
  renderEvidenceDetails(panel, claim, apiBase, signal);
}
function renderEvidenceDetails(panel, claim, apiBase, signal, requireClaim = false) {
  const graph = el2("div", "lp-claim-dag");
  graph.append(el2("p", "lp-claim-dag-loading", "Loading evidence graph\u2026"));
  panel.append(graph);
  const preview = el2("div", "lp-source-preview");
  preview.setAttribute("aria-live", "polite");
  preview.hidden = true;
  panel.append(preview);
  const requests = /* @__PURE__ */ new WeakMap();
  let references = [];
  const statistics = claim.claim_type === "statistic" && el2("div", "lp-statistics-selection");
  if (statistics) panel.insertBefore(statistics, graph);
  renderDagPane(graph, claim.claim_id, apiBase, {
    signal,
    selectReference: (reference) => load(reference),
    onReferences(nodes) {
      references = nodes || [];
      if (statistics) {
        const source = references.find((node) => node.label === claim.source_file);
        if (source) load(source, { destination: statistics });
      }
    },
    requireClaim
  });
  function previewUrl(reference, member) {
    const url = new URL("../preview.json", new URL(apiBase, location.href));
    url.searchParams.set("claim_id", claim.claim_id);
    url.searchParams.set("node_id", reference.node_id);
    if (member !== void 0) url.searchParams.set("member", member);
    return withBundleContext(url.href);
  }
  function loadPlot(file, name, target, title, checksum, requestSignal) {
    if (typeof file !== "string" || !/^[\w.-]+\.(png|jpe?g)$/i.test(name)) return;
    const path = file.slice(0, file.lastIndexOf("/") + 1) + name;
    const reference = references.find((item) => item.label === path);
    if (!reference) return;
    fetch(previewUrl(reference), { signal: requestSignal }).then(async (response) => {
      if (!response.ok) return;
      const image = await response.json();
      if (image.kind !== "image" || requestSignal.aborted) return;
      const recorded = image.hash?.replace(/^sha256:/i, "").toLowerCase();
      if (typeof checksum === "string" && (!recorded || !checksum.startsWith(recorded))) return;
      renderSourceContent(target, { ...image, file: title || name });
    }).catch(() => {
    });
  }
  function load(reference, { member, destination = preview } = {}) {
    requests.get(destination)?.abort();
    const current = new AbortController();
    requests.set(destination, current);
    const requestSignal = AbortSignal.any([signal, current.signal]);
    destination.hidden = false;
    destination.replaceChildren(el2("p", null, "Loading evidence\u2026"));
    fetch(previewUrl(reference, member), {
      signal: requestSignal,
      headers: { Accept: "application/json" }
    }).then(async (response) => {
      const result = await response.json();
      if (current.signal.aborted || signal.aborted) return;
      if (!response.ok) {
        destination.replaceChildren(
          el2("code", null, reference.script_file || reference.label),
          el2("p", null, result.error || "File preview unavailable.")
        );
        appendSourceLinks(destination, result.links, { current: true });
        return;
      }
      if (result.kind === "statistics") {
        destination.replaceChildren();
        renderStatistics(
          destination,
          result.statistics,
          (name, target, title, checksum) => {
            if (!result.member) loadPlot(result.file, name, target, title, checksum, requestSignal);
          }
        );
        appendSourceLinks(destination, result.links);
        if (result.member) {
          destination.append(previewButton("Archive contents", () => load(reference)));
        }
        return;
      }
      destination.replaceChildren(
        el2("code", null, result.file),
        el2("span", "lp-source-preview-status", result.truncated ? "Matches recorded hash \xB7 excerpt" : "Matches recorded hash")
      );
      appendSourceLinks(destination, result.links);
      if (result.member) {
        const back = previewButton("Archive contents", () => load(reference));
        destination.append(el2("p", null, result.member), back);
      }
      renderSourceContent(destination, result, (options) => load(reference, { ...options, destination }));
    }).catch((error) => {
      if (!current.signal.aborted && !signal.aborted) {
        destination.replaceChildren(
          el2("code", null, reference.script_file || reference.label),
          el2("p", null, error.message || "File preview unavailable.")
        );
      }
    });
  }
}
function appendSourceLinks(preview, links, { current = false } = {}) {
  const actions = el2("div", "lp-source-actions");
  const choices = [
    [links?.file, current ? "Open current file" : "Open file"],
    [links?.folder, "Open containing folder"]
  ];
  for (const [url, label] of choices) {
    if (typeof url !== "string" || !url.startsWith("/") || url.startsWith("//") || url.includes("\\")) continue;
    const action = el2("a", "stx-button", label);
    action.href = url;
    action.target = "_blank";
    action.rel = "noopener";
    actions.append(action);
  }
  if (actions.childElementCount) preview.append(actions);
}
function previewButton(label, action) {
  const button = el2("button", null, label);
  button.type = "button";
  button.addEventListener("click", action);
  return button;
}
function renderSourceContent(panel, result, load) {
  if (result.kind === "image") {
    const image = el2("img");
    image.src = `data:${result.media_type};base64,${result.data}`;
    image.alt = result.file;
    panel.append(image);
  } else if (result.kind === "text") {
    const code = el2("code", result.language ? "language-" + result.language : null, result.text);
    const block = el2("pre");
    block.append(code);
    panel.append(block);
    if (result.language) window.hljs?.highlightElement(code);
  } else if (result.kind === "archive") {
    const list = el2("ul", "lp-archive-preview");
    for (const item of result.members) {
      const row = el2("li");
      row.append(previewButton(item.name, () => load({ member: item.id })));
      list.append(row);
    }
    panel.append(el2("p", null, "First archive entries"), list);
  } else if (result.kind === "metadata") {
    const size = result.size.toLocaleString();
    const identity = el2("details");
    identity.append(el2("summary", null, "Recorded hash"), el2("code", null, result.hash));
    panel.append(el2("p", null, `${result.description} \xB7 ${size} bytes`), identity);
  }
}
var graphLayouts = /* @__PURE__ */ new Map();
var maxLayouts = 32;
function invalidateEvidenceGraphs() {
  graphLayouts.clear();
}
function cachedLayout(hash, render) {
  const hit = graphLayouts.get(hash);
  if (hit) {
    graphLayouts.delete(hash);
    graphLayouts.set(hash, hit);
    return hit;
  }
  const rendered = Promise.resolve().then(render).catch((error) => {
    if (graphLayouts.get(hash) === rendered) graphLayouts.delete(hash);
    throw error;
  });
  graphLayouts.set(hash, rendered);
  if (graphLayouts.size > maxLayouts) graphLayouts.delete(graphLayouts.keys().next().value);
  return rendered;
}
async function renderDagPane(dagBox, claimId, apiBase, { signal, selectReference, requireClaim, onReferences } = {}) {
  let body;
  try {
    const selector = new URLSearchParams({ claim_id: claimId });
    const url = withBundleContext(apiBase + "dag?" + selector);
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal
    });
    body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || "dag request failed: " + res.status);
    if (requireClaim && body.scope !== "claim") throw new Error("No Clew retrieval graph is recorded for this citation.");
  } catch (err) {
    if (signal?.aborted) return;
    dagBox.replaceChildren(el2(
      "p",
      "lp-claim-dag-empty",
      String(err && err.message || "Evidence graph unavailable.")
    ));
    return;
  }
  if (signal?.aborted) return;
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
    const render = () => {
      window.mermaid.initialize?.({ startOnLoad: false, securityLevel: "strict", htmlLabels: false });
      return window.mermaid.render("lp-dag-" + ++graphSequence, body.mermaid);
    };
    const { svg } = body.graph_sha256 ? await cachedLayout(body.graph_sha256, render) : await render();
    if (signal?.aborted) return;
    const title = body.scope === "claim" ? "Evidence graph" : "Bundle graph";
    const heading = el2("h3", "lp-claim-graph-title", title);
    if (body.provider) heading.append(" (" + body.provider + ")");
    const wrap = el2("div", "lp-claim-dag-svg");
    wrap.dataset.evidenceState = body.state || "";
    wrap.innerHTML = svg;
    dagBox.replaceChildren(heading);
    if (selectReference && body.reason) {
      const status = el2("p", "lp-claim-trace-status", body.state === "supported" ? "Recorded trace verified" : body.reason);
      status.dataset.state = body.state;
      dagBox.append(status);
    }
    dagBox.append(graphControls(wrap, signal), wrap);
    if (body.scope === "claim") {
      let updateGraphLink = function() {
        const theme = document.documentElement.dataset.theme;
        if (theme === "light" || theme === "dark") graphPage.searchParams.set("theme", theme);
        else graphPage.searchParams.delete("theme");
        link.href = withBundleContext(graphPage.href);
      };
      const graphPage = new URL("../graph.html", new URL(apiBase, location.href));
      graphPage.searchParams.set("claim_id", claimId);
      const link = el2("a", "lp-claim-graph-link", "Open full evidence graph");
      updateGraphLink();
      link.addEventListener("click", updateGraphLink);
      dagBox.append(link);
      bindReferences(dagBox, wrap, body.references, selectReference);
      onReferences?.(body.references);
    }
  } catch (err) {
    if (signal?.aborted) return;
    dagBox.innerHTML = "";
    dagBox.appendChild(el2(
      "p",
      "lp-claim-dag-empty",
      "DAG render failed (" + String(err && err.message || err) + ")."
    ));
  }
}
function bindReferences(dagBox, graph, references, selectReference) {
  if (!Array.isArray(references) || !references.length) return;
  const nodes = [...graph.querySelectorAll("g.node")];
  const entries = references.map((reference) => ({
    reference,
    node: nodes.find((element2) => element2.id.startsWith("flowchart-" + reference.id + "-"))
  }));
  let activeReference;
  let pinnedReference = false;
  let hoverTimer;
  const fallback = entries.length > 6 || entries.some(({ node }) => !node);
  const list = fallback ? el2("ul", "lp-claim-references") : null;
  function activate(entry, pin = false) {
    if (pinnedReference && !pin) return;
    if (pin) pinnedReference = true;
    const { reference, node } = entry;
    if (activeReference === reference.id) return;
    activeReference = reference.id;
    for (const other of entries) {
      const selected = other === entry;
      other.node?.setAttribute("aria-pressed", String(selected));
      other.node?.classList.toggle("lp-source-highlight", selected);
      other.button?.setAttribute("aria-pressed", String(selected));
    }
    if (selectReference) selectReference(reference);
    else node?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
  for (const entry of entries) {
    const { reference, node } = entry;
    const role = { input: "Input", output: "Output", process: "Run" }[reference.kind];
    const label = (role ? role + " " : "") + (reference.script_file || reference.label);
    const select = () => activate(entry, true);
    const preview = () => activate(entry);
    if (node) {
      node.setAttribute("role", "button");
      node.setAttribute("tabindex", "0");
      node.setAttribute("aria-label", label);
      node.setAttribute("aria-pressed", "false");
      node.addEventListener("click", select);
      node.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        select();
      });
    }
    if (list) {
      const item = el2("li");
      entry.button = previewButton(label, select);
      entry.button.setAttribute("aria-pressed", "false");
      item.append(entry.button);
      list.append(item);
    }
    if (!selectReference) continue;
    for (const control of [node, entry.button].filter(Boolean)) {
      control.addEventListener("pointerenter", () => {
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(() => {
          if (control.isConnected) preview();
        }, 80);
      });
      control.addEventListener("pointerleave", () => clearTimeout(hoverTimer));
      control.addEventListener("focus", preview);
    }
  }
  if (list) {
    const details = el2("details");
    details.append(el2("summary", null, "Browse sources"), list);
    dagBox.append(details);
  }
}

// src/scitex_live_paper/_django/static/live_paper/js/pdf-viewer.js
function toOverlay(claim) {
  const anchor = pickAnchor(claim);
  if (!Number.isInteger(anchor?.page) || anchor.page < 1 || !Array.isArray(anchor.bbox) || anchor.bbox.length !== 4 || !anchor.bbox.every(Number.isFinite)) return null;
  const figure = claim.claim_type === "figure" || claim.figure_id || claim.extras?.figure_id;
  return {
    id: claim.claim_id,
    page: anchor.page,
    bbox: anchor.bbox,
    appearance: figure ? "region" : "highlight",
    label: "Trace evidence for " + (claim.claim_value ?? claim.claim_id),
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
    const bibliography = createBibliographyHighlights(options.citationVerification, options.onCitationSelect);
    this.navigation = createPdfNavigation({
      ...options.navigation,
      pdfjs: options.pdfjs,
      onDocument: bibliography.documentLoaded
    });
    this.container.classList.add("pdf-viewer-host");
    this.provider = createRichPdfViewer({
      container: this.container,
      feedContainer: options.feedContainer,
      createPdfViewer: options.createPdfViewer,
      rendererOptions: {
        pdfjs: this.navigation.runtime,
        workerSrc: options.workerSrc,
        hooks: {
          onPageRender: (page, _viewport, surface) => {
            this.navigation.pageRendered(page, surface);
            bibliography.pageRendered(page, surface);
          }
        },
        textLayer: true,
        linkLayer: true
      },
      ports: {
        documents: { resolve: (docType) => ({
          id: String(docType || "manuscript"),
          src: withBundleContext(this.apiBase + "pdf?doc_type=" + encodeURIComponent(docType || "manuscript") + "&t=" + Date.now())
        }) },
        overlays: { list: () => this.claims.map(toOverlay).filter(Boolean) },
        feed: options.feedContainer && {
          list: () => this.claims.map((claim) => ({
            id: claim.claim_id,
            label: claim.claim_id,
            overlayId: toOverlay(claim)?.id,
            data: claim
          })),
          renderEntry: (entry) => options.renderFeedEntry(entry.data),
          navigate: (overlay) => {
            options.showPdf?.();
            this.navigation.goTo(overlay);
          }
        },
        comments: {
          list: () => this.comments.map(toComment),
          create: async (_document, target, body) => {
            const nativeTarget = target.overlayId ? { claim_id: target.overlayId } : { page: target.page, bbox: target.bbox };
            const comment = await postComment(this.apiBase, { body, target: nativeTarget });
            this.comments.push(comment);
            return toComment(comment);
          }
        },
        preview: options.inlineEvidence && { render: (panel, overlay, signal2) => {
          const claim = this.claims.find((claim2) => claim2.claim_id === overlay.id);
          if (claim) renderEvidencePreview(panel, claim, this.apiBase, signal2);
        } },
        events: { emit: (event) => {
          const fromFeed = event.type === "feed-select";
          const fromOverlay = !options.inlineEvidence && event.overlay && (event.type === "overlay-select" || event.type === "overlay-preview");
          if (fromFeed || fromOverlay) {
            this.container.dispatchEvent(new CustomEvent("live-paper:claim", {
              bubbles: true,
              detail: {
                id: fromFeed ? event.entry.id : event.overlay.id,
                preview: event.type === "overlay-preview"
              }
            }));
          }
          if (fromOverlay && event.type === "overlay-select" && event.overlay.target?.figureId) {
            this.container.dispatchEvent(new CustomEvent("live-paper:evidence-request", {
              bubbles: true,
              detail: { port: "figure", target: event.overlay.target.figureId }
            }));
          }
          this.container.dispatchEvent(new CustomEvent("live-paper:pdf", { bubbles: true, detail: event }));
        } }
      }
    });
    this.zoomListeners = new AbortController();
    const { signal } = this.zoomListeners;
    const manuscript = this.container.closest(".lp-reader-document") || this.container;
    bindScopedZoom(manuscript, (action, point) => this.zoomAt(action, point), signal);
    const navigation = options.navigation.container;
    bindScopedZoom(navigation, (action) => zoomNavigation(navigation, action), signal);
    options.bindClaimFilters?.(this.provider.setFeedFilter);
    this.provider.renderer.setInteractive(false);
    if (options.evidencePane) this.stopEvidencePane = bindEvidencePane(this.container);
  }
  goToClaim(overlay) {
    this.provider.selectOverlay(overlay.id);
    this.navigation.goTo(overlay);
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
    this.loaded = false;
    try {
      await this.provider.load(docType);
      await this.provider.renderer.fitWidth();
      this.navigation.finishRender();
      this.loaded = true;
      this.watchFitWidth();
      return true;
    } catch (error) {
      console.warn("[pdf-viewer] load failed:", error);
      this.renderPlaceholder("No PDF available.");
      return false;
    }
  }
  watchFitWidth() {
    this.resizeObserver?.disconnect();
    let width = this.container.clientWidth;
    this.resizeObserver = new ResizeObserver(() => {
      const next = this.container.clientWidth;
      if (next <= 0 || Math.abs(next - width) < 2) return;
      width = next;
      clearTimeout(this.resizeTimer);
      if (this.manualZoom === void 0) {
        this.resizeTimer = setTimeout(() => this.queueZoom(null), 180);
      }
    });
    this.resizeObserver.observe(this.container);
  }
  zoomAt(action, point) {
    if (!this.loaded) return false;
    clearTimeout(this.resizeTimer);
    if (action === "reset") {
      this.manualZoom = void 0;
    } else {
      const current = this.manualZoom ?? this.provider.renderer.getScale();
      const factor = action === "in" ? 1.2 : 1 / 1.2;
      const minimum = Math.min(current, 0.25);
      const maximum = Math.max(current, 4);
      this.manualZoom = Math.max(minimum, Math.min(maximum, current * factor));
    }
    this.queueZoom(this.manualZoom ?? null, point);
  }
  async queueZoom(scale, point) {
    this.pendingZoom = { scale, point };
    if (this.zooming) return;
    this.zooming = true;
    try {
      while (this.pendingZoom && !this.zoomListeners.signal.aborted) {
        const next = this.pendingZoom;
        this.pendingZoom = null;
        const renderer = this.provider.renderer;
        if (next.scale !== null && next.scale === renderer.getScale()) continue;
        await this.keepPosition(() => next.scale === null ? renderer.fitWidth() : renderer.setScale(next.scale), next.point);
      }
    } catch (error) {
      console.warn("[pdf-viewer] zoom failed:", error);
    } finally {
      this.zooming = false;
    }
  }
  async keepPosition(action, point) {
    const scroller = readerScroller(this.container);
    const bounds = scroller.getBoundingClientRect();
    const y = point?.y ?? Math.max(0, bounds.top);
    const pages = [...this.container.querySelectorAll(".stx-pdf-page")];
    const index = pages.findIndex((page) => page.getBoundingClientRect().bottom > y);
    const before = pages[index]?.getBoundingClientRect();
    const fractionY = before && Math.max(0, Math.min(1, (y - before.top) / before.height));
    const fractionX = before && point && point.x >= before.left && point.x <= before.right ? (point.x - before.left) / before.width : null;
    await action();
    const after = this.container.querySelectorAll(".stx-pdf-page")[index]?.getBoundingClientRect();
    if (!before || !after) return;
    scroller.scrollBy({
      top: after.top - before.top + fractionY * (after.height - before.height),
      left: fractionX === null ? 0 : after.left + fractionX * after.width - point.x,
      behavior: "instant"
    });
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
    clearTimeout(this.resizeTimer);
    this.resizeObserver?.disconnect();
    this.zoomListeners.abort();
    this.stopEvidencePane?.();
    this.navigation.destroy();
    this.provider.destroy();
  }
};
function readerScroller(container) {
  for (let node = container.parentElement; node; node = node.parentElement) {
    if (/auto|scroll/.test(getComputedStyle(node).overflowY)) return node;
  }
  return container.ownerDocument.scrollingElement;
}
function zoomNavigation(container, action) {
  if (container.hasAttribute("data-collapsed")) return false;
  const list = container.querySelector(".rpdf-nav-content > :not([hidden]) > :is(.rpdf-nav-pages, .rpdf-nav-bookmarks)");
  if (!list) return false;
  const zoom = Number(list.style.zoom || 1);
  list.style.zoom = String(action === "reset" ? 1 : Math.max(0.5, Math.min(3, zoom + (action === "in" ? 0.2 : -0.2))));
}
function bindEvidencePane(container) {
  const listeners = new AbortController();
  const { signal } = listeners;
  let lastScroll = -Infinity;
  let hover;
  function select(anchor, preview) {
    if (!preview) {
      for (const current of container.querySelectorAll('.lp-rich-overlay[aria-current="true"]')) {
        current.removeAttribute("aria-current");
      }
      anchor.setAttribute("aria-current", "true");
    }
    container.dispatchEvent(new CustomEvent("live-paper:claim", {
      bubbles: true,
      detail: { id: anchor.dataset.overlayId, preview }
    }));
  }
  container.ownerDocument.addEventListener("scroll", (event) => {
    if (!event.target.contains?.(container)) return;
    lastScroll = performance.now();
    clearTimeout(hover);
  }, { capture: true, passive: true, signal });
  container.addEventListener("pointerenter", (event) => {
    const anchor = event.target;
    if (!anchor.matches?.(".lp-rich-overlay")) return;
    event.stopImmediatePropagation();
    if (event.pointerType === "touch" || performance.now() - lastScroll < 120) return;
    clearTimeout(hover);
    hover = setTimeout(() => {
      if (anchor.isConnected) select(anchor, true);
    }, 160);
  }, { capture: true, signal });
  container.addEventListener("pointerleave", (event) => {
    if (event.target.matches?.(".lp-rich-overlay")) clearTimeout(hover);
  }, { capture: true, signal });
  container.addEventListener("focus", (event) => {
    if (event.target.matches?.(".lp-rich-overlay")) event.stopImmediatePropagation();
  }, { capture: true, signal });
  container.addEventListener("click", (event) => {
    const anchor = event.target.closest?.(".lp-rich-overlay");
    if (!anchor) return;
    event.stopImmediatePropagation();
    clearTimeout(hover);
    select(anchor, false);
  }, { capture: true, signal });
  return () => {
    clearTimeout(hover);
    listeners.abort();
  };
}

// src/scitex_live_paper/_django/static/live_paper/js/pdf-downloads.js
function bindPdfDownloads(root2, claims, original) {
  const options = root2.querySelector(".lp-pdf-download");
  if (!options) return;
  const status = options.querySelector("[role='status']");
  const menu = options.querySelector("details");
  const buttons = [...options.querySelectorAll("button")];
  function graphSelection() {
    const detail = root2.querySelector(".lp-claim-detail");
    const svg = detail?.querySelector(".lp-claim-dag-svg svg");
    return svg ? { svg, claim: detail.dataset.claimId } : null;
  }
  const withGraph = options.querySelector('[data-pdf-export="graph"]');
  let busy = false;
  function update() {
    withGraph.disabled = busy || !graphSelection();
  }
  const sidebar = root2.querySelector(".live-paper-claims");
  if (sidebar) new MutationObserver(update).observe(sidebar, { childList: true, subtree: true });
  for (const button of buttons) {
    button.addEventListener("click", async () => {
      if (busy) return;
      const graph = button === withGraph ? graphSelection() : null;
      if (button === withGraph && !graph) return;
      const style = getComputedStyle(root2);
      const marks = claims.map(toOverlay).filter(Boolean).map((mark) => ({
        ...mark,
        color: pdfColor(style, mark.status)
      }));
      const graphCopy = graph && { ...graph, svg: graph.svg.cloneNode(true) };
      busy = true;
      buttons.forEach((control) => {
        control.disabled = true;
      });
      status.textContent = "Preparing PDF\u2026";
      try {
        const module = await import(options.dataset.exportSrc || new URL("./pdf-export-entry.js", import.meta.url).href);
        const response = await fetch(original);
        if (!response.ok) throw new Error("Original PDF could not be downloaded.");
        const bytes = await module.exportReaderPdf(await response.arrayBuffer(), marks, graphCopy);
        const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = graph ? "manuscript-with-evidence-graph.pdf" : "manuscript-highlighted.pdf";
        link.click();
        menu.open = false;
        setTimeout(() => URL.revokeObjectURL(url), 3e4);
        status.textContent = "";
      } catch (error) {
        status.textContent = error.message || "PDF export failed.";
      } finally {
        busy = false;
        buttons.forEach((control) => {
          control.disabled = false;
        });
        update();
      }
    });
  }
  update();
  options.hidden = false;
}
function pdfColor(style, status) {
  const allowed = ["verified", "suspect", "unsourced", "mismatch", "missing", "registered"];
  const token = allowed.includes(status) ? status : "registered";
  const hex = style.getPropertyValue("--lp-status-" + token).trim();
  const digits = /^#[\da-f]{6}$/i.test(hex) ? hex.slice(1) : "6e7681";
  return digits.match(/../g).map((value) => parseInt(value, 16) / 255);
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
    btn.dispatchEvent(new CustomEvent("live-paper:evidence-updated", { bubbles: true }));
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
  sidebar.hidden = false;
  bindClaimTabs(sidebar);
  const allClaims = sidebar.querySelector("#lp-all-claims-panel");
  const count = claimsPayload.claims.length;
  sidebar.querySelector("#lp-all-claims-tab").textContent = `All claims (${count})`;
  if (!count) {
    const message = document.createElement("p");
    message.textContent = "No claims are registered for this manuscript.";
    allClaims.append(message);
  }
  const reVerifyEnabled = !!claimsPayload.re_verify_enabled;
  const pinnedCommit = claimsPayload.pinned_commit || null;
  if (reVerifyEnabled) {
    allClaims.append(renderReverifyAllButton(apiBase, pinnedCommit));
  }
  const container = document.createElement("div");
  container.className = "lp-claims-list";
  allClaims.querySelector("#lp-claim-type-results").append(container);
  return {
    feedContainer: container,
    bindClaimFilters: (setFilter) => bindClaimFilters(allClaims, claimsPayload.claims, setFilter),
    renderFeedEntry: (claim) => renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit)
  };
}
var claimTypes = /* @__PURE__ */ new Set(["sentence", "value", "statistic", "table", "figure"]);
function normalize(text) {
  return String(text ?? "").normalize("NFKC").toLowerCase().trim();
}
function filterType(claim) {
  const type = normalize(claim.claim_type);
  if (type === "text") return "sentence";
  return claimTypes.has(type) ? type : "other";
}
function bindClaimFilters(panel, claims, setFilter) {
  if (!claims.length) return;
  const controls = panel.querySelector(".lp-claim-filters");
  const search = controls.querySelector("input");
  const tabList = controls.querySelector(".lp-claim-type-tabs");
  const results = panel.querySelector("#lp-claim-type-results");
  const status = results.querySelector(".lp-claim-filter-status");
  const index = claims.map((claim) => ({
    id: claim.claim_id,
    type: filterType(claim),
    text: normalize([claim.claim_id, claim.claim_value, claim.source_file, claim.file_path].join(" "))
  }));
  tabList.querySelector('[data-claim-type="other"]').hidden = !index.some((entry) => entry.type === "other");
  let type = "all";
  bindTabs(tabList, (tab) => {
    type = tab.dataset.claimType;
    results.setAttribute("aria-labelledby", tab.id);
    update();
  });
  function update() {
    const terms = normalize(search.value).split(/\s+/).filter(Boolean);
    if (type === "all" && !terms.length) {
      setFilter(null);
      status.textContent = "";
      return;
    }
    const matched = new Set(index.filter(
      (entry) => (type === "all" || type === entry.type) && terms.every((term) => entry.text.includes(term))
    ).map((entry) => entry.id));
    setFilter((entry) => matched.has(entry.id));
    status.textContent = matched.size ? `${matched.size} of ${claims.length} claims` : "No claims match these filters.";
  }
  search.addEventListener("input", update);
  controls.hidden = false;
  update();
}
function bindClaimTabs(sidebar) {
  bindTabs(sidebar.querySelector(".lp-claims-tabs"), (selected, refresh) => {
    for (const tab of sidebar.querySelectorAll(".lp-claims-tabs > [role='tab']")) {
      sidebar.querySelector("#" + tab.getAttribute("aria-controls")).hidden = tab !== selected;
    }
    sidebar.scrollTop = 0;
    if (refresh && selected.id === "lp-selection-tab") {
      sidebar.dispatchEvent(new CustomEvent("live-paper:selection-tab", { bubbles: true }));
    }
  });
}
function bindTabs(tabList, onSelect) {
  const tabs = [...tabList.querySelectorAll(":scope > [role='tab']:not([hidden])")];
  function select(tab, refresh) {
    for (const button of tabs) {
      const active = button === tab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    }
    onSelect(tab, refresh);
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", (event) => select(tab, event.isTrusted));
    tab.addEventListener("keydown", (event) => {
      const direction = { ArrowLeft: -1, ArrowRight: 1 };
      if (!(event.key in direction) && !["Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + direction[event.key] + tabs.length) % tabs.length;
      select(tabs[next], true);
      tabs[next].focus();
    });
  });
}
function renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit) {
  const li = document.createElement("div");
  li.className = "lp-claim";
  li.dataset.claimId = claim.claim_id;
  li.dataset.status = claim.status || "registered";
  li.classList.add("lp-claim-selectable");
  li.addEventListener("click", function(event) {
    if (event.target.closest("button")) return;
    li.dispatchEvent(new CustomEvent("live-paper:claim", {
      bubbles: true,
      detail: { id: claim.claim_id, preview: false }
    }));
  });
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
    if (res.ok) rowEl.dispatchEvent(new CustomEvent("live-paper:evidence-updated", { bubbles: true }));
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
  bindReaderLayout(rootEl);
  bindPdfTheme(rootEl);
  bindPortEvents(rootEl, apiBase);
  const eventLog = createEventLog();
  bindEventLog(rootEl, eventLog);
  rootEl._livePaperEventLog = eventLog;
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
    rootEl.dataset.paperStage = bundleInfo.paper_state?.stage || "";
    void renderTraceSummary(rootEl, apiBase);
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
  let sidebarOptions;
  if (claimsPayload) {
    try {
      sidebarOptions = renderClaimsSidebar(rootEl, claimsPayload, apiBase);
    } catch (err) {
      console.warn("[live-paper] claims sidebar render failed", err);
    }
  }
  rootEl.addEventListener("live-paper:evidence-updated", () => {
    invalidateEvidenceGraphs();
    closeClaimDetail(ensureClaimsSidebar(rootEl));
  });
  function showClaim(sidebar, claim, refresh) {
    const overlay = toOverlay(claim);
    renderClaimDetail(sidebar, claim, apiBase, {
      refresh,
      goToPdf: overlay && (() => {
        showPdf();
        hideEvidenceDrawer(rootEl)?.focus({ preventScroll: true });
        viewer.goToClaim(overlay);
      })
    });
  }
  rootEl.addEventListener("live-paper:selection-tab", (event) => {
    const sidebar = event.target;
    const id = sidebar.querySelector(".lp-claim-detail")?.dataset.claimId;
    const claim = claimsPayload?.claims?.find((entry) => entry.claim_id === id);
    if (claim) showClaim(sidebar, claim, true);
  });
  rootEl.addEventListener("live-paper:claim", (event) => {
    const id = event && event.detail ? event.detail.id : null;
    const claims = claimsPayload && Array.isArray(claimsPayload.claims) ? claimsPayload.claims : [];
    const claim = claims.find((c) => c && c.claim_id === id);
    if (!claim) return;
    try {
      const sidebar = ensureClaimsSidebar(rootEl);
      if (event.detail?.preview && sidebar.dataset.pinnedClaim) return;
      if (!event.detail?.preview) {
        sidebar.removeAttribute("data-document-focused");
        sidebar.dataset.pinnedClaim = id;
      }
      showClaim(sidebar, claim, !event.detail?.preview);
    } catch (err) {
      console.warn("[live-paper] anchor detail render failed", err);
    }
  });
  const pdfContainer = ensurePdfContainer(rootEl);
  const navigation = rootEl.querySelector("#live-paper-navigation");
  const showPdf = bindManuscriptFormats(rootEl, navigation);
  const viewer = new PDFViewer({
    ...sidebarOptions,
    showPdf,
    evidencePane: true,
    citationVerification: claimsPayload?.citation_verification,
    onCitationSelect(key, citation, goToReference) {
      const sidebar = ensureClaimsSidebar(rootEl);
      const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
      if (getComputedStyle(toggle).display !== "none" && toggle.getAttribute("aria-expanded") === "false") {
        toggle.click();
      }
      renderCitationDetail(sidebar, key, citation, apiBase, goToReference);
    },
    navigation: {
      container: navigation
    },
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
  const download = rootEl.querySelector("#live-paper-download-pdf");
  if (bundleInfo && download) {
    download.href = withBundleContext(apiBase + "pdf?download=1");
    bindPdfDownloads(rootEl, viewer.claims, download.href);
  }
  await viewer.load();
  const shareStatus = bindShare(rootEl);
  openSharedClaim(rootEl, viewer.claims, shareStatus);
}
async function renderTraceSummary(rootEl, apiBase) {
  const url = new URL("../review.json", new URL(apiBase, location.href));
  const packet = await fetchOrNull(url.href);
  if (!packet?.counts) return;
  const banner = rootEl.querySelector("#live-paper-trace-status");
  if (!banner) return;
  const summary = document.createElement("a");
  summary.className = "lp-trace-summary";
  summary.href = withBundleContext(url.href);
  const total = packet.supported.length + packet.needs_inspection.length;
  if (total === 0) return;
  const provider = packet.provider?.name;
  const label = typeof provider === "string" && provider ? `${provider[0].toUpperCase()}${provider.slice(1)} calculation traces` : "Calculation traces";
  const verified = document.createElement("strong");
  verified.className = "lp-trace-verified";
  verified.textContent = packet.counts.supported + " verified";
  const inspect = document.createElement("strong");
  inspect.className = "lp-trace-inspect";
  inspect.textContent = packet.needs_inspection.length + " to inspect";
  summary.dataset.needsInspection = String(packet.needs_inspection.length > 0);
  summary.append(label, " \xB7 ", verified, " \xB7 ", inspect);
  banner.replaceChildren(summary);
  banner.hidden = false;
}
function hideEvidenceDrawer(rootEl) {
  const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
  if (getComputedStyle(toggle).display === "none") return null;
  const sidebar = rootEl.querySelector("#live-paper-claims");
  sidebar.removeAttribute("data-drawer-open");
  sidebar.setAttribute("data-document-focused", "");
  toggle.setAttribute("aria-expanded", "false");
  return toggle;
}
function bindManuscriptFormats(rootEl, navigation) {
  const tabs = rootEl.querySelector(".lp-format-tabs");
  if (!tabs) return () => {
  };
  const pdfTab = tabs.querySelector("#lp-format-pdf");
  const pdf = rootEl.querySelector("#lp-format-panel-pdf");
  const html = rootEl.querySelector("#lp-format-panel-html");
  const frame = html.querySelector("iframe");
  bindTabs(tabs, (selected) => {
    const showPdf = selected === pdfTab;
    rootEl.dataset.manuscriptFormat = showPdf ? "pdf" : "html";
    pdf.hidden = navigation.hidden = !showPdf;
    html.hidden = showPdf;
    if (!showPdf) {
      hideEvidenceDrawer(rootEl);
      if (!frame.hasAttribute("src")) frame.src = frame.dataset.src;
    }
  });
  window.addEventListener("message", (event) => {
    if (html.hidden || event.origin !== location.origin || event.source !== frame.contentWindow || event.data?.type !== "live-paper:html-claim" || typeof event.data.id !== "string") return;
    rootEl.dispatchEvent(new CustomEvent("live-paper:claim", { detail: { id: event.data.id } }));
  });
  return () => {
    if (pdf.hidden) pdfTab.click();
  };
}
function bindPdfTheme(rootEl) {
  const picker = rootEl.querySelector(".lp-pdf-theme");
  const key = "live-paper.pdf-theme";
  let saved;
  try {
    saved = localStorage.getItem(key);
  } catch {
  }
  if (saved === "light" || saved === "dark") picker.value = saved;
  rootEl.dataset.pdfTheme = picker.value;
  picker.closest("label").hidden = false;
  picker.addEventListener("change", () => {
    rootEl.dataset.pdfTheme = picker.value;
    try {
      localStorage.setItem(key, picker.value);
    } catch {
    }
  });
}
function bindReaderLayout(rootEl) {
  const header = rootEl.previousElementSibling;
  const shell = rootEl.closest("#main-content");
  const fitReader = () => {
    const top = rootEl.getBoundingClientRect().top;
    const bottom = shell?.getBoundingClientRect().bottom;
    const height = Math.floor(Math.min(bottom ?? window.innerHeight, window.innerHeight) - top);
    if (height > 0) rootEl.style.setProperty("--lp-reader-height", height + "px");
  };
  const observer = new ResizeObserver(fitReader);
  if (shell) observer.observe(shell);
  if (header) observer.observe(header);
  window.addEventListener("resize", fitReader);
  fitReader();
  const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
  const sidebar = rootEl.querySelector("#live-paper-claims");
  toggle.addEventListener("click", () => {
    sidebar.removeAttribute("data-document-focused");
    const open = sidebar.toggleAttribute("data-drawer-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
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
  renderTraceSummary
};
