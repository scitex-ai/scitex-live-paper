/** Zoom the SVG inside its own scrollable viewport. Native scrolling also
 * supports arrow keys, trackpads and touch without changing the PDF zoom. */
export function graphControls(viewport, signal) {
  const controls = document.createElement("div");
  controls.className = "lp-graph-controls";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "Evidence graph controls");
  viewport.tabIndex = 0;
  viewport.setAttribute("role", "region");
  viewport.setAttribute("aria-label", "Evidence graph viewport");

  let zoom = 1;
  const step = 0.25;
  const minimum = 0.5;
  const maximum = 4;

  function button(label, text, action) {
    const control = document.createElement("button");
    control.type = "button";
    control.className = "stx-button";
    control.setAttribute("aria-label", label);
    control.title = label;
    control.textContent = text;
    control.addEventListener("click", action);
    return control;
  }

  const out = button("Zoom out of evidence graph", "−", () => resize(zoom - step));
  const inside = button("Zoom in on evidence graph", "+", () => resize(zoom + step));
  const reset = button("Reset evidence graph zoom", "Reset zoom", () => resize(1, true));
  const percent = document.createElement("output");
  controls.append(out, inside, reset, percent, downloadMenu(viewport));

  function updatePan() {
    viewport.toggleAttribute("data-can-pan",
      viewport.scrollWidth > viewport.clientWidth || viewport.scrollHeight > viewport.clientHeight);
  }

  function resize(next, resetPosition = false) {
    const previous = zoom;
    zoom = Math.max(minimum, Math.min(maximum, next));
    const centerX = viewport.clientWidth / 2;
    const centerY = viewport.clientHeight / 2;
    const x = (viewport.scrollLeft + centerX) * zoom / previous - centerX;
    const y = (viewport.scrollTop + centerY) * zoom / previous - centerY;
    viewport.style.setProperty("--lp-graph-zoom", String(zoom));
    viewport.scrollTo({
      left: resetPosition ? 0 : x,
      top: resetPosition ? 0 : y,
      behavior: "instant",
    });
    out.disabled = zoom <= minimum;
    inside.disabled = zoom >= maximum;
    percent.textContent = Math.round(zoom * 100) + "%";
    updatePan();
  }
  resize(1);

  const observer = new ResizeObserver(updatePan);
  observer.observe(viewport);
  signal?.addEventListener("abort", () => observer.disconnect(), { once: true });

  let drag;
  viewport.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" || event.button !== 0 ||
        !viewport.hasAttribute("data-can-pan") || event.target.closest('[role="button"], a')) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY,
      left: viewport.scrollLeft, top: viewport.scrollTop };
    viewport.focus({ preventScroll: true });
    viewport.setPointerCapture(event.pointerId);
    viewport.setAttribute("data-panning", "");
    event.preventDefault();
  });
  viewport.addEventListener("pointermove", (event) => {
    if (event.pointerId !== drag?.id) return;
    viewport.scrollTo({ left: drag.left + drag.x - event.clientX,
      top: drag.top + drag.y - event.clientY, behavior: "instant" });
  });
  viewport.addEventListener("lostpointercapture", () => {
    drag = null;
    viewport.removeAttribute("data-panning");
  });
  return controls;
}

function downloadMenu(viewport) {
  const menu = document.createElement("details");
  const title = document.createElement("summary");
  title.textContent = "Download graph";
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  menu.append(title);
  for (const format of ["svg", "png"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "stx-button";
    button.textContent = format.toUpperCase();
    button.addEventListener("click", async () => {
      button.disabled = true;
      status.textContent = "";
      try {
        const svg = viewport.querySelector("svg");
        let blob;
        if (format === "svg") {
          blob = new Blob([graphSvg(svg)], { type: "image/svg+xml;charset=utf-8" });
        } else {
          const canvas = await graphCanvas(svg);
          blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        }
        if (!blob) throw new Error("Empty graph image");
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "evidence-graph." + format;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        menu.open = false;
        title.focus({ preventScroll: true });
      } catch {
        status.textContent = "Graph download failed. Try again.";
      } finally {
        button.disabled = false;
      }
    });
    menu.append(button);
  }
  menu.append(status);
  return menu;
}

function graphSize(svg) {
  const view = svg?.viewBox.baseVal;
  if (!view?.width || !view.height) throw new Error("Evidence graph is not ready.");
  return view;
}

function graphSvg(svg, scale = 1) {
  const view = graphSize(svg);
  const copy = svg.cloneNode(true);
  copy.removeAttribute("style");
  copy.setAttribute("width", Math.max(1, Math.ceil(view.width * scale)));
  copy.setAttribute("height", Math.max(1, Math.ceil(view.height * scale)));
  return new XMLSerializer().serializeToString(copy);
}

export async function graphCanvas(svg) {
  const view = graphSize(svg);
  const scale = Math.min(2, 3800 / Math.max(view.width, view.height));
  const image = new Image();
  image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(graphSvg(svg, scale));
  await image.decode();
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Unable to render the evidence graph.");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0);
  return canvas;
}
