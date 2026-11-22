// Writer's citation destinations identify the start of each bibliography entry.
export function createBibliographyHighlights() {
  const pages = new Map();
  let references = new Map();
  let activeDocument;
  return {
    documentLoaded(pdf) {
      activeDocument = pdf;
      pages.clear();
      references = new Map();
      void pdf.getDestinations().then(async (destinations) => {
        const resolved = new Map();
        for (const [name, dest] of Object.entries(destinations ?? {})) {
          if (!name.startsWith("cite.") || !Array.isArray(dest)) continue;
          const [ref, mode, left, top] = dest;
          if (mode?.name !== "XYZ" || !Number.isFinite(left) || !Number.isFinite(top)) continue;
          const index = Number.isInteger(ref) ? ref : await pdf.getPageIndex(ref).catch(() => -1);
          if (index < 0 || index >= pdf.numPages) continue;
          const page = resolved.get(index + 1) ?? [];
          page.push({ left, top });
          resolved.set(index + 1, page);
        }
        if (pdf !== activeDocument) return;
        references = resolved;
        for (const [page, surface] of pages) markReferences(surface, references.get(page));
      }).catch((error) => console.warn("[pdf-viewer] bibliography destinations unavailable", error));
    },
    pageRendered(page, surface) {
      pages.set(page, surface);
      markReferences(surface, references.get(page));
    },
  };
}

function markReferences(surface, references) {
  if (!references?.length) return;
  const origin = surface.element.getBoundingClientRect();
  const spans = [...surface.element.querySelectorAll('[data-stx-pdf-layer="text"] span')]
    .filter((span) => !span.childElementCount && span.textContent.trim())
    .map((span) => ({ span, bounds: span.getBoundingClientRect() }));
  for (const reference of references) {
    const [x, y] = surface.pdfToViewportPoint(reference.left, reference.top);
    const start = spans.find(({ bounds }) =>
      Math.abs(bounds.left - origin.x - x) < bounds.height * 0.7
      && Math.abs(bounds.top - origin.y - y) < bounds.height * 0.65
    );
    if (!start) continue;
    for (const { span, bounds } of spans) {
      if (bounds.left >= start.bounds.left - 1
        && Math.abs(bounds.top - start.bounds.top) < start.bounds.height * 0.45) {
        span.classList.add("lp-bibliography-highlight");
      }
    }
  }
}
