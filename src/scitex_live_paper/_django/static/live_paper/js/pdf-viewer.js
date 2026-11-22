/** Native bundle adapter for LivePaper's public rich PDF provider.
 * This is the only place the PDF component knows the native bundle/API DTOs.
 */
import { createPdfNavigation, createRichPdfViewer } from "./pdf-provider.js";
import { withBundleContext } from "./_utils.js";
import { pickAnchor } from "./claim-overlays.js";
import { createBibliographyHighlights } from "./bibliography-highlights.js";
import { postComment } from "./comments.js";
import { renderEvidencePreview } from "./claim-details.js";

export function toOverlay(claim) {
  const anchor = pickAnchor(claim);
  if (!anchor || !Number.isInteger(anchor.page) || !Array.isArray(anchor.bbox)) return null;
  const figure = claim.claim_type === "figure" || claim.figure_id || claim.extras?.figure_id;
  return { id: claim.claim_id, page: anchor.page, bbox: anchor.bbox,
    appearance: figure ? "region" : "highlight",
    label: "Trace evidence for " + (claim.claim_value ?? claim.claim_id), status: claim.status,
    readonly: claim.readonly === true || claim.extras?.locked === true,
    target: { figureId: claim.figure_id ?? claim.extras?.figure_id ?? null } };
}
export function toComment(comment) {
  const { claim_id, ...region } = comment.target || {};
  return { id: comment.id, body: comment.body, author: comment.author,
    target: claim_id ? { overlayId: claim_id } : region };
}

export class PDFViewer {
  constructor(options) {
    this.container = options.container;
    this.apiBase = options.apiBase;
    this.claims = [];
    this.comments = [];
    const bibliography = createBibliographyHighlights(options.citationVerification, options.onCitationSelect);
    this.navigation = createPdfNavigation({
      ...options.navigation,
      pdfjs: options.pdfjs,
      onDocument: bibliography.documentLoaded,
    });
    this.container.classList.add("pdf-viewer-host");
    this.provider = createRichPdfViewer({
      container: this.container,
      feedContainer: options.feedContainer,
      createPdfViewer: options.createPdfViewer,
      rendererOptions: { pdfjs: this.navigation.runtime, workerSrc: options.workerSrc,
        hooks: {
          onPageRender: (page, _viewport, surface) => {
            this.navigation.pageRendered(page, surface);
            bibliography.pageRendered(page, surface);
          },
        },
        textLayer: true, linkLayer: true },
      ports: {
        documents: { resolve: (docType) => ({ id: String(docType || "manuscript"),
          src: withBundleContext(this.apiBase + "pdf?doc_type=" + encodeURIComponent(docType || "manuscript") + "&t=" + Date.now()) }) },
        overlays: { list: () => this.claims.map(toOverlay).filter(Boolean) },
        feed: options.feedContainer && {
          list: () => this.claims.map((claim) => ({
            id: claim.claim_id,
            label: claim.claim_id,
            overlayId: toOverlay(claim)?.id,
            data: claim,
          })),
          renderEntry: (entry) => options.renderFeedEntry(entry.data),
        },
        comments: {
          list: () => this.comments.map(toComment),
          create: async (_document, target, body) => {
            const nativeTarget = target.overlayId ? { claim_id: target.overlayId } : { page: target.page, bbox: target.bbox };
            const comment = await postComment(this.apiBase, { body, target: nativeTarget });
            this.comments.push(comment);
            return toComment(comment);
          },
        },
        preview: options.inlineEvidence && { render: (panel, overlay, signal) => {
          const claim = this.claims.find((claim) => claim.claim_id === overlay.id);
          if (claim) renderEvidencePreview(panel, claim, this.apiBase, signal);
        } },
        events: { emit: (event) => {
          const fromFeed = event.type === "feed-select";
          const fromOverlay = !options.inlineEvidence && event.overlay
            && (event.type === "overlay-select" || event.type === "overlay-preview");
          if (fromFeed || fromOverlay) {
            this.container.dispatchEvent(new CustomEvent("live-paper:claim", {
              bubbles: true,
              detail: {
                id: fromFeed ? event.entry.id : event.overlay.id,
                preview: event.type === "overlay-preview",
              },
            }));
          }
          if (fromOverlay && event.type === "overlay-select" && event.overlay.target?.figureId) {
            this.container.dispatchEvent(new CustomEvent("live-paper:evidence-request", {
              bubbles: true, detail: { port: "figure", target: event.overlay.target.figureId },
            }));
          }
          this.container.dispatchEvent(new CustomEvent("live-paper:pdf", { bubbles: true, detail: event }));
        } },
      },
    });
    this.provider.renderer.setInteractive(false);
    if (options.evidencePane) this.stopEvidencePane = bindEvidencePane(this.container);
  }
  setClaims(claims) { this.claims = claims || []; this.provider.setOverlays(this.claims.map(toOverlay).filter(Boolean)); }
  setComments(comments) { this.comments = comments || []; this.provider.setComments(this.comments.map(toComment)); }
  async load(docType = "manuscript") {
    try {
      await this.provider.load(docType);
      await this.provider.renderer.fitWidth();
      this.navigation.finishRender();
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
      this.resizeTimer = setTimeout(() => void this.refitVisiblePage(), 180);
    });
    this.resizeObserver.observe(this.container);
  }

  async refitVisiblePage() {
    const scroller = readerScroller(this.container);
    const top = scroller === document.scrollingElement ? 0 : scroller.getBoundingClientRect().top;
    const pages = [...this.container.querySelectorAll(".stx-pdf-page")];
    const index = pages.findIndex((page) => page.getBoundingClientRect().bottom > top);
    const old = pages[index]?.getBoundingClientRect();
    const offset = old && old.top < top ? (top - old.top) / old.height : null;
    try {
      await this.provider.renderer.fitWidth();
      if (offset === null) return;
      const rect = this.container.querySelectorAll(".stx-pdf-page")[index]?.getBoundingClientRect();
      if (rect) scroller.scrollBy({ top: rect.top + rect.height * offset - top, behavior: "instant" });
    } catch (error) {
      console.warn("[pdf-viewer] refit failed:", error);
    }
  }

  clear() { this.container.replaceChildren(); }
  renderPlaceholder(message = "No PDF available.") {
    this.clear(); const placeholder = document.createElement("p");
    placeholder.className = "pdf-placeholder"; placeholder.textContent = message; this.container.append(placeholder);
  }
  render() { return this.provider.renderer.setScale(this.provider.renderer.getScale()); }
  setZoom(delta) { return this.provider.renderer.setScale(Math.max(0.4, Math.min(3, this.provider.renderer.getScale() + delta))); }
  setFitWidth() { return this.provider.renderer.fitWidth(); }
  get zoomPercent() { return Math.round(this.provider.renderer.getScale() * 100); }
  destroy() {
    clearTimeout(this.resizeTimer);
    this.resizeObserver?.disconnect();
    this.stopEvidencePane?.();
    this.navigation.destroy();
    this.provider.destroy();
  }
}

function readerScroller(container) {
  for (let node = container.parentElement; node; node = node.parentElement) {
    if (node.scrollHeight > node.clientHeight && /auto|scroll/.test(getComputedStyle(node).overflowY)) return node;
  }
  return container.ownerDocument.scrollingElement;
}

/** Use the viewer's existing overlay buttons as entry points to the side pane. */
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
      detail: { id: anchor.dataset.overlayId, preview },
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
