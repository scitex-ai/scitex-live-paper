/** Native bundle adapter for LivePaper's public rich PDF provider.
 * This is the only place the PDF component knows the native bundle/API DTOs.
 */
import { createRichPdfViewer } from "./pdf-provider.js";
import { withBundleContext } from "./_utils.js";
import { pickAnchor } from "./claim-overlays.js";
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
    this.container.classList.add("pdf-viewer-host");
    this.provider = createRichPdfViewer({
      container: this.container,
      feedContainer: options.feedContainer,
      createPdfViewer: options.createPdfViewer,
      rendererOptions: { pdfjs: options.pdfjs, workerSrc: options.workerSrc,
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
        preview: { render: (panel, overlay, signal) => {
          const claim = this.claims.find((claim) => claim.claim_id === overlay.id);
          if (claim) renderEvidencePreview(panel, claim, this.apiBase, signal);
        } },
        events: { emit: (event) => {
          if (event.type === "feed-select") {
            this.container.dispatchEvent(new CustomEvent("live-paper:claim", {
              bubbles: true, detail: { id: event.entry.id },
            }));
          }
          this.container.dispatchEvent(new CustomEvent("live-paper:pdf", { bubbles: true, detail: event }));
        } },
      },
    });
    this.provider.renderer.setInteractive(false);
  }
  setClaims(claims) { this.claims = claims || []; this.provider.setOverlays(this.claims.map(toOverlay).filter(Boolean)); }
  setComments(comments) { this.comments = comments || []; this.provider.setComments(this.comments.map(toComment)); }
  async load(docType = "manuscript") {
    try { await this.provider.load(docType); await this.provider.renderer.fitWidth(); return true; }
    catch (error) { console.warn("[pdf-viewer] load failed:", error); this.renderPlaceholder("No PDF available."); return false; }
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
  destroy() { this.provider.destroy(); }
}
