/**
 * SciTeX Rich PDF provider. Framework-neutral and route-neutral.
 *
 * All anchors: 1-based page, bottom-left PDF units, bbox [x0,y0,x1,y1].
 * SDK owns raster/text/link rendering and viewport transforms. Consumers own
 * document resolution, DTO translation, authentication, persistence and policy.
 * See the package README for the port contract and package exports.
 */
export function createRichPdfViewer(options) {
  const { container, createPdfViewer, ports = {}, rendererOptions = {} } = options;
  if (typeof createPdfViewer !== "function") throw new TypeError("SDK PDF factory required");
  if (typeof ports.documents?.resolve !== "function") throw new TypeError("Document port required");
  let current = null;
  let overlays = [];
  let comments = [];
  let sequence = 0;
  let disposed = false;
  const pages = new Map();
  const layers = new Map();
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
        if (!allow("mark-create", input)) { emit({ type: "mutation-refused", action: "mark-create" }); return; }
        if (ports.mutations?.createMark) {
          const document = current;
          Promise.resolve().then(() => ports.mutations.createMark(document, input)).catch((error) => emit({ type: "mutation-error", action: "mark-create", documentId: document.id, error }));
        } else hooks.onPenInput?.(input);
        emit({ type: "pen-input", input });
      },
      onRegionSelect(region) {
        if (!allow("region-select", region)) return;
        hooks.onRegionSelect?.(region);
        emit({ type: "region-select", region });
      },
    },
  });

  function setOverlays(values) { overlays = Array.isArray(values) ? [...values] : []; repaint(); }
  function setComments(values) { comments = Array.isArray(values) ? [...values] : []; repaint(); }
  function repaint() { for (const page of pages.keys()) paint(page); }
  function rectStyle(element, surface, bbox) {
    const [x0, y0, x1, y1] = surface.pdfToViewportRect(bbox);
    Object.assign(element.style, { position: "absolute", left: `${Math.min(x0, x1)}px`, top: `${Math.min(y0, y1)}px`, width: `${Math.abs(x1-x0)}px`, height: `${Math.abs(y1-y0)}px`, pointerEvents: "auto" });
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
      if (count) { const badge = document.createElement("span"); badge.className = "lp-rich-comment-count"; badge.textContent = `✎${count}`; button.append(badge); }
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
      button.type = "button"; button.className = "lp-rich-comment-marker"; button.textContent = "✎";
      button.setAttribute("aria-label", `Comment: ${comment.body || ""}`);
      rectStyle(button, surface, comment.target.bbox);
      button.style.width = "24px"; button.style.height = "24px";
      button.addEventListener("click", () => selectTarget(comment.target, button));
      layer.append(button);
    }
    preview?.reanchor(previousLayer, layer);
    previousLayer?.remove();
  }
  function selectOverlay(overlayId) {
    selectedOverlayId = overlayId ?? null;
    for (const layer of layers.values()) {
      for (const element of layer.querySelectorAll("[data-overlay-id]")) {
        if (element.dataset.overlayId === selectedOverlayId) {
          element.setAttribute("aria-current", "true");
        } else {
          element.removeAttribute("aria-current");
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
      const anchor = [...(layers.get(overlay?.page)?.children ?? [])]
        .find((element) => element.dataset.overlayId === entry.overlayId);
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
    panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", "PDF comments");
    const close = document.createElement("button"); close.type = "button"; close.textContent = "Close comments";
    close.addEventListener("click", () => { panel.remove(); anchor?.focus(); });
    panel.append(close);
    for (const comment of comments.filter((item) => sameTarget(item.target, target))) {
      const row = document.createElement("p"); row.className = "lp-rich-comment";
      row.textContent = [comment.author, comment.body].filter(Boolean).join(": "); panel.append(row);
    }
    if (ports.comments?.create) {
      const form = document.createElement("form");
      const input = document.createElement("textarea"); input.setAttribute("aria-label", "New PDF comment"); input.required = true;
      const submit = document.createElement("button"); submit.type = "submit"; submit.textContent = "Add comment";
      const status = document.createElement("p"); status.setAttribute("role", "status");
      if (!allow("comment-create", target)) { input.disabled = true; submit.disabled = true; status.textContent = "Comments are read-only for this target."; }
      form.append(input, submit, status); panel.append(form);
      form.addEventListener("submit", async (event) => {
        event.preventDefault(); submit.disabled = true; status.textContent = "Saving comment…";
        try {
          await createComment(target, input.value);
          if (!panel.isConnected) return;
          status.textContent = "Comment saved."; input.value = "";
          selectTarget(target, anchor, overlay);
        } catch (error) { if (panel.isConnected) status.textContent = error.message || "Comment could not be saved."; }
        finally { if (panel.isConnected) submit.disabled = !allow("comment-create", target); }
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
    const document = current; const token = sequence;
    try {
      const comment = await ports.comments.create(document, target, body.trim());
      if (!comment?.id) throw new Error("Comment port returned no saved comment identity");
      if (disposed || token !== sequence) return comment;
      comments = [...comments.filter((item) => item.id !== comment.id), comment]; repaint(); emit({ type: "comment-created", comment });
      return comment;
    } catch (error) { emit({ type: "mutation-error", action: "comment-create", documentId: document.id, error }); throw error; }
  }
  async function refresh() {
    if (!current || disposed) return;
    const token = sequence; const document = current;
    const requests = [
      Promise.resolve().then(() => ports.overlays?.list?.(document) ?? overlays),
      Promise.resolve().then(() => ports.comments?.list?.(document) ?? comments),
      Promise.resolve().then(() => feed && ports.feed?.list?.(document)),
    ];
    const values = await Promise.allSettled(requests);
    if (disposed || token !== sequence) return;
    if (values[0].status === "fulfilled") overlays = [...(values[0].value || [])];
    else emit({ type: "port-error", port: "overlays", error: values[0].reason });
    if (values[1].status === "fulfilled") comments = [...(values[1].value || [])];
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
    popup?.remove(); popup = null;
    current = null;
    selectedOverlayId = null;
    feed?.reset();
    for (const layer of layers.values()) layer.remove();
    layers.clear(); pages.clear();
    const document = await ports.documents.resolve(key);
    if (!document?.id || !document.src) throw new Error("Document port must return id and src");
    if (disposed || token !== sequence) return false;
    current = document; pages.clear(); overlays = []; comments = [];
    await refresh();
    if (disposed || token !== sequence) return false;
    await renderer.load(document.src);
    if (disposed || token !== sequence) return false;
    emit({ type: "document-loaded" });
    return true;
  }
  function destroy() {
    if (disposed) return;
    disposed = true; sequence++; popup?.remove();
    preview?.close();
    feed?.destroy();
    for (const layer of layers.values()) layer.remove();
    layers.clear(); pages.clear(); renderer.destroy();
  }
  return { renderer, load, refresh, setOverlays, setComments,
    setFeedFilter: (filter) => feed?.setFilter(filter), selectOverlay, selectTarget, createComment, destroy };
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
    button.textContent = "×";
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
      const horizontal = rect.right + panel.offsetWidth + margin <= innerWidth
        ? rect.right + margin : rect.left - panel.offsetWidth - margin;
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
      (element) => element.dataset.overlayId === anchor.dataset.overlayId,
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

function validBox(box) { return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite); }
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
      const element = list.ownerDocument.createElement("li");
      const button = list.ownerDocument.createElement("button");
      button.type = "button";
      button.textContent = entry.label;
      const row = { entry, element, button };
      button.addEventListener("click", () => {
        select(row);
        choose(entry);
      });
      element.append(button);
      const content = renderEntry?.(entry);
      if (content) element.append(content);
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
    reset() { setEntries([]); },
    destroy() { list.remove(); },
  };
}

/** Shared PDF navigation. Wrap the PDF.js runtime passed to the renderer once. */
export function createPdfNavigation({ container, pdfjs, onDocument }) {
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
  const surfaces = new Map();
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
    toggle.textContent = open ? "‹" : "›";
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
      // Center a line or small region. Give tall figures a visible top edge.
      const inset = Math.max(12, (scroller.clientHeight - Math.abs(y1 - y0)) / 2);
      const scrollerTop = scroller === scrollRoot ? 0 : scroller.getBoundingClientRect().top;
      scroller.scrollTo({
        top: scroller.scrollTop + surface.element.getBoundingClientRect().top - scrollerTop + y - inset,
        behavior: "instant",
      });
    } else if (scroller) {
      const [, offset] = Number.isFinite(destination.top)
        ? surface.pdfToViewportPoint(destination.left ?? 0, destination.top)
        : [0, 0];
      const top = scroller.scrollTop + surface.element.getBoundingClientRect().top
        - (scroller === scrollRoot ? 0 : scroller.getBoundingClientRect().top);
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
        void renderThumbnail(pdf, page, entry.target, () => current === generation).catch(() => {});
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
      pagePanel.textContent = "Loading pages…";
      bookmarkPanel.textContent = "Loading bookmarks…";
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
    },
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
    },
  };
}

function closestScrollContainer(element) {
  for (let parent = element.parentElement; parent; parent = parent.parentElement) {
    if (["auto", "scroll"].includes(getComputedStyle(parent).overflowY)) return parent;
  }
  return null;
}

async function renderThumbnail(pdf, number, canvas, isCurrent) {
  const page = await pdf.getPage(number);
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
    return { page: index + 1, left: mode?.name === "XYZ" ? left : null,
      top: mode?.name === "XYZ" ? top : mode?.name === "FitH" ? left : null };
  } catch {
    return null;
  }
}
