/**
 * LivePaper public rich PDF provider. Framework-neutral, route-neutral.
 *
 * All anchors: 1-based page, bottom-left PDF units, bbox [x0,y0,x1,y1].
 * SDK owns raster/text/link rendering and viewport transforms. Consumers own
 * document resolution, DTO translation, authentication, persistence and policy.
 * See docs/rich-pdf-provider.md for the port contract and package export.
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
      if (count) { const badge = document.createElement("span"); badge.className = "lp-rich-comment-count"; badge.textContent = `✎${count}`; button.append(badge); }
      button.addEventListener("click", () => selectTarget({ overlayId: overlay.id, page, bbox: overlay.bbox, readonly: overlay.readonly }, button, overlay));
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
  }
  function selectTarget(target, anchor, overlay = null) {
    if (disposed || !current) return;
    popup?.remove();
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
    const values = await Promise.allSettled([ports.overlays?.list?.(document) ?? overlays, ports.comments?.list?.(document) ?? comments]);
    if (disposed || token !== sequence) return;
    if (values[0].status === "fulfilled") overlays = [...(values[0].value || [])];
    else emit({ type: "port-error", port: "overlays", error: values[0].reason });
    if (values[1].status === "fulfilled") comments = [...(values[1].value || [])];
    else emit({ type: "port-error", port: "comments", error: values[1].reason });
    repaint();
  }
  async function load(key) {
    if (disposed) throw new Error("PDF provider has been destroyed");
    const token = ++sequence;
    popup?.remove(); popup = null;
    current = null;
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
    for (const layer of layers.values()) layer.remove();
    layers.clear(); pages.clear(); renderer.destroy();
  }
  return { renderer, load, refresh, setOverlays, setComments, selectTarget, createComment, destroy };
}

function validBox(box) { return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite); }
function sameTarget(left, right) {
  if (left?.overlayId || right?.overlayId) return Boolean(left?.overlayId && left.overlayId === right?.overlayId);
  return left?.page === right?.page && JSON.stringify(left?.bbox) === JSON.stringify(right?.bbox);
}
