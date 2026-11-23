import type { PdfSource, PdfViewerApi, PdfViewerOptions, PenInput } from '@scitex/sdk/ui/pdf-viewer';
export interface PdfDocument { id: string; src: PdfSource; revision?: string; readonly?: boolean; }
/** All geometry uses 1-based pages and bottom-left PDF units. */
export interface PdfTarget { overlayId?: string; page?: number; bbox?: number[]; readonly?: boolean; }
export interface PdfOverlay { id: string; page: number; bbox: number[]; label?: string; status?: string; appearance?: "highlight" | "region"; readonly?: boolean; target?: unknown; }
export interface PdfComment { id: string; body: string; author?: string; createdAt?: string; target: PdfTarget; }
export interface PdfEvent { type: string; documentId: string | null; [key: string]: unknown; }
export interface PdfFeedEntry {
  id: string;
  label: string;
  overlayId?: string;
  data?: unknown;
}
export interface RichPdfPorts {
  documents: { resolve(key: unknown): PdfDocument | Promise<PdfDocument> };
  overlays?: { list(document: PdfDocument): PdfOverlay[] | Promise<PdfOverlay[]> };
  comments?: { list(document: PdfDocument): PdfComment[] | Promise<PdfComment[]>; create?(document: PdfDocument, target: PdfTarget, body: string): Promise<PdfComment> };
  feed?: {
    list(document: PdfDocument): PdfFeedEntry[] | Promise<PdfFeedEntry[]>;
    renderEntry?(entry: PdfFeedEntry): Node | null;
  };
  preview?: { render(container: HTMLElement, overlay: PdfOverlay, signal: AbortSignal): void };
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
  feedContainer?: HTMLElement;
}
export interface RichPdfApi {
  readonly renderer: PdfViewerApi;
  load(key: unknown): Promise<boolean>;
  refresh(): Promise<void>;
  setOverlays(overlays: PdfOverlay[]): void;
  setComments(comments: PdfComment[]): void;
  setFeedFilter(filter: ((entry: PdfFeedEntry) => boolean) | null): void;
  selectTarget(target: PdfTarget, anchor?: HTMLElement, overlay?: PdfOverlay | null): void;
  createComment(target: PdfTarget, body: string): Promise<PdfComment>;
  destroy(): void;
}
export function createRichPdfViewer(options: RichPdfOptions): RichPdfApi;

export interface PdfDiscussionOptions {
  title?: string;
  load(): PdfComment[] | Promise<PdfComment[]>;
  post?(body: string): Promise<PdfComment>;
  targetControl?: HTMLElement;
  labelTarget?(target: PdfTarget): string;
}
export function renderPdfDiscussion(container: HTMLElement, options: PdfDiscussionOptions): Promise<void>;

type PdfRuntime = NonNullable<PdfViewerOptions["pdfjs"]>;
type LoadedPdf = Awaited<ReturnType<PdfRuntime["getDocument"]>["promise"]>;

export interface PdfNavigationOptions {
  /** Empty mount beside the scrollable PDF viewport. */
  container: HTMLElement;
  toggle?: HTMLButtonElement;
  pdfjs: PdfRuntime;
  initiallyOpen?: boolean;
  onDocument?(document: LoadedPdf): void;
}

export interface PdfNavigationApi {
  readonly runtime: PdfRuntime;
  pageRendered(page: number, surface: import('@scitex/sdk/ui/pdf-viewer').PdfPageSurface): void;
  finishRender(): void;
  goTo(target: {page: number; bbox?: number[]; left?: number; top?: number}): void;
  destroy(): void;
}

export function createPdfNavigation(options: PdfNavigationOptions): PdfNavigationApi;


type PdfMenuPoint = {x: number; y: number};
type PdfMenuEntry =
  | {kind: "divider"}
  | {label: string; disabled?: boolean; shortcut?: string; onSelect(): void};
type PdfMenuOptions = {
  items(): PdfMenuEntry[];
  onOpen(): void;
  onClose(): void;
};
export interface PdfContextMenuOptions {
  ContextMenu: new (options: PdfMenuOptions) => {
    openAt(x: number, y: number, target: HTMLElement): void;
    close(): void;
    destroy(): void;
  };
  container: HTMLElement;
  scrollContainer?: HTMLElement;
  canOpen?(): boolean;
  items?(target: HTMLElement, point?: PdfMenuPoint): PdfMenuEntry[];
  pan?: boolean;
  copy?: boolean;
  zoom?(action: "in" | "out" | "reset", point?: PdfMenuPoint): void;
}
export function bindPdfContextMenu(options: PdfContextMenuOptions): () => void;
