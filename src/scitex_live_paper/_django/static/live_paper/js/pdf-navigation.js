// Use the same PDF.js document as the SDK renderer.
export function bindPdfNavigation(pdfjs, outline) {
  let documentTask;
  let references = new Map();
  const pages = new Map();
  const runtime = {
    ...pdfjs,
    getDocument(...args) {
      const task = pdfjs.getDocument(...args);
      documentTask = task.promise;
      return task;
    },
  };

  function jump(target, navigate) {
    const surface = pages.get(target.page);
    if (!surface || !Number.isFinite(target.top)) {
      navigate(target.page);
      return;
    }
    const [, offset] = surface.pdfToViewportPoint(0, target.top);
    navigate(target.page, offset);
  }

  return {
    runtime,
    async load() {
      if (outline) {
        outline.hidden = true;
        outline.querySelector("nav").replaceChildren();
      }
      references = new Map();
      const pdf = await documentTask;
      if (!pdf) return;
      const [items, names] = await Promise.all([pdf.getOutline(), pdf.getDestinations()]);
      const fromName = (destination) => resolveDestination(pdf, names, destination);
      if (outline && items?.length) {
        const list = await renderOutline(items, fromName, (target) => {
          jump(target, (page, offset) => navigateToPage(pages, page, offset));
          outline.open = false;
          outline.querySelector("summary").focus({ preventScroll: true });
        });
        if (list.childElementCount) {
          outline.querySelector("nav").append(list);
          outline.hidden = false;
        }
      }
      for (const [name, dest] of Object.entries(names ?? {})) {
        if (!name.startsWith("cite.")) continue;
        const location = await fromName(dest);
        if (!location || !Number.isFinite(location.left) || !Number.isFinite(location.top)) continue;
        const page = references.get(location.page) ?? [];
        page.push(location);
        references.set(location.page, page);
      }
      for (const [page, surface] of pages) markReferences(surface, references.get(page));
    },
    pageRendered(page, _viewport, surface) {
      pages.set(page, surface);
      markReferences(surface, references.get(page));
    },
  };
}

async function resolveDestination(pdf, names, value) {
  const dest = typeof value === "string" ? names?.[value] : value;
  if (!Array.isArray(dest)) return null;
  const [ref, mode, left, top] = dest;
  let index;
  try {
    index = Number.isInteger(ref) ? ref : ref ? await pdf.getPageIndex(ref) : -1;
  } catch {
    return null;
  }
  if (index < 0 || index >= pdf.numPages) return null;
  return {
    page: index + 1,
    left: mode?.name === "XYZ" ? left : null,
    top: mode?.name === "XYZ" ? top : mode?.name === "FitH" ? left : null,
  };
}

async function renderOutline(items, resolve, navigate) {
  const list = document.createElement("ul");
  for (const item of items) {
    const target = await resolve(item.dest);
    const children = await renderOutline(item.items ?? [], resolve, navigate);
    if (!target && !children.childElementCount) continue;
    const row = document.createElement("li");
    const title = document.createElement(target ? "button" : "span");
    title.textContent = item.title;
    if (target) {
      title.type = "button";
      title.addEventListener("click", () => navigate(target));
    }
    row.append(title);
    if (children.childElementCount) row.append(children);
    list.append(row);
  }
  return list;
}

function navigateToPage(pages, page, offset = 0) {
  const surface = pages.get(page);
  if (!surface?.element.isConnected) return;
  const manuscript = surface.element.closest(".lp-reader-document");
  if (!manuscript) {
    surface.element.scrollIntoView({ block: "start" });
    return;
  }
  const top = manuscript.scrollTop + surface.element.getBoundingClientRect().top
    - manuscript.getBoundingClientRect().top + offset;
  manuscript.scrollTo({ top: top - 12 });
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
