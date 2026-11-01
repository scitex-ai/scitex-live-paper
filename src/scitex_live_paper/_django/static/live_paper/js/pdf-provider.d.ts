import type { PdfSource, PdfViewerApi, PdfViewerOptions, PenInput } from '@scitex/sdk/ui/pdf-viewer';
export interface PdfDocument { id: string; src: PdfSource; readonly?: boolean; }
/** All geometry uses 1-based pages and bottom-left PDF units. */
export interface PdfTarget { overlayId?: string; page?: number; bbox?: number[]; readonly?: boolean; }
export interface PdfOverlay { id: string; page: number; bbox: number[]; label?: string; status?: string; readonly?: boolean; target?: unknown; }
export interface PdfComment { id: string; body: string; author?: string; target: PdfTarget; }
export interface PdfEvent { type: string; documentId: string | null; [key: string]: unknown; }
export interface RichPdfPorts {
  documents: { resolve(key: unknown): PdfDocument | Promise<PdfDocument> };
  overlays?: { list(document: PdfDocument): PdfOverlay[] | Promise<PdfOverlay[]> };
  comments?: { list(document: PdfDocument): PdfComment[] | Promise<PdfComment[]>; create?(document: PdfDocument, target: PdfTarget, body: string): Promise<PdfComment> };
  events?: { emit(event: PdfEvent): void };
  mutations?: { createMark?(document: PdfDocument, input: PenInput): void | Promise<void> };
  policy?: { canMutate(context: { document: PdfDocument; action: string; target: unknown }): boolean };
}
export interface RichPdfOptions {
  container: HTMLElement;
  createPdfViewer(options: PdfViewerOptions): PdfViewerApi;
  ports: RichPdfPorts;
  rendererOptions?: Omit<PdfViewerOptions, 'container' | 'src'>;
  commentsContainer?: HTMLElement;
}
export interface RichPdfApi {
  readonly renderer: PdfViewerApi;
  load(key: unknown): Promise<boolean>;
  refresh(): Promise<void>;
  setOverlays(overlays: PdfOverlay[]): void;
  setComments(comments: PdfComment[]): void;
  selectTarget(target: PdfTarget, anchor?: HTMLElement, overlay?: PdfOverlay | null): void;
  createComment(target: PdfTarget, body: string): Promise<PdfComment>;
  destroy(): void;
}
export function createRichPdfViewer(options: RichPdfOptions): RichPdfApi;
