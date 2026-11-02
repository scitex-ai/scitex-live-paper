/** Native bundle adapter for LivePaper's public rich PDF provider.
 * This is the only place the PDF component knows the native bundle/API DTOs.
 */
import { createRichPdfViewer } from "./pdf-provider.js";
import { withBundleContext } from "./_utils.js";
import { pickAnchor } from "./claim-overlays.js";
import { postComment } from "./comments.js";

export function toOverlay(claim) {
  const anchor = pickAnchor(claim);
  if (!anchor || !Number.isInteger(anchor.page) || !Array.isArray(anchor.bbox)) return null;
  return { id: claim.claim_id, page: anchor.page, bbox: anchor.bbox,
    label: claim.claim_value || claim.claim_id, status: claim.status,
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
      createPdfViewer: options.createPdfViewer,
      rendererOptions: { pdfjs: options.pdfjs, workerSrc: options.workerSrc,
        textLayer: true, linkLayer: true },
      ports: {
        documents: { resolve: (docType) => ({ id: String(docType || "manuscript"),
          src: withBundleContext(this.apiBase + "pdf?doc_type=" + encodeURIComponent(docType || "manuscript") + "&t=" + Date.now()) }) },
        overlays: { list: () => this.claims.map(toOverlay).filter(Boolean) },
        comments: {
          list: () => this.comments.map(toComment),
          create: async (_document, target, body) => {
            const nativeTarget = target.overlayId ? { claim_id: target.overlayId } : { page: target.page, bbox: target.bbox };
            const comment = await postComment(this.apiBase, { body, target: nativeTarget });
            this.comments.push(comment);
            return toComment(comment);
          },
        },
        events: { emit: (event) => {
          if (event.type === "overlay-select" && event.overlay) {
            this.container.dispatchEvent(new CustomEvent("live-paper:claim", { bubbles: true, detail: { id: event.overlay.id } }));
            if (event.overlay.target?.figureId) this.container.dispatchEvent(new CustomEvent("live-paper:evidence-request", { bubbles: true, detail: { port: "figure", target: event.overlay.target.figureId } }));
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
