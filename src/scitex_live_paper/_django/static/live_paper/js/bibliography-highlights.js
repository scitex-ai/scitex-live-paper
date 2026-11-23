// Writer's citation destinations identify the start of each bibliography entry.
export function createBibliographyHighlights(citations = {}, onSelect) {
  const pages = new Map();
  let references = new Map();
  let activeDocument;
  function select(key, goToReference) {
    onSelect?.(key, Object.hasOwn(citations, key) ? citations[key] : { status: "unknown" }, goToReference);
  }
  function mark(node, key) {
    node.dataset.citationKey = key;
    node.dataset.status = Object.hasOwn(citations, key) ? citations[key].status : "unknown";
    node.title = key + " · " + node.dataset.status;
  }

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
    },
  };
}

function markReferences(surface, references, mark, select) {
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
    if (annotation.subtype !== "Link" || typeof annotation.dest !== "string"
      || !annotation.dest.startsWith("cite.") || !Array.isArray(annotation.rect)) continue;
    const [x0, y0, x1, y1] = surface.pdfToViewportRect(annotation.rect);
    const rect = [Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)];
    const link = links.find((item) => !item.dataset.citationKey
      && ["left", "top", "width", "height"].every((prop, index) =>
        Math.abs(parseFloat(item.style[prop]) - rect[index]) < 0.5));
    if (!link) continue;
    const key = annotation.dest.slice(5);
    mark(link, key);
    link.setAttribute("aria-label", "Inspect citation " + key + " (" + link.dataset.status + ")");
    function inspect(event) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      select(key, () => {
        link.removeEventListener("click", inspect, true);
        link.click();
        link.addEventListener("click", inspect, true);
      });
    }
    link.addEventListener("click", inspect, true);
  }
}
