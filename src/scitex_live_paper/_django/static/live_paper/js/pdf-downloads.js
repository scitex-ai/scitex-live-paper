import { toOverlay } from "./pdf-viewer.js";

export function bindPdfDownloads(root, claims, original) {
  const options = root.querySelector(".lp-pdf-download");
  if (!options) return;
  const status = options.querySelector("[role='status']");
  const menu = options.querySelector("details");
  const buttons = [...options.querySelectorAll("button")];
  function graphSelection() {
    const detail = root.querySelector(".lp-claim-detail");
    const svg = detail?.querySelector(".lp-claim-dag-svg svg");
    return svg ? { svg, claim: detail.dataset.claimId } : null;
  }

  const withGraph = options.querySelector('[data-pdf-export="graph"]');
  let busy = false;
  function update() { withGraph.disabled = busy || !graphSelection(); }
  const sidebar = root.querySelector(".live-paper-claims");
  if (sidebar) new MutationObserver(update).observe(sidebar, { childList: true, subtree: true });

  for (const button of buttons) {
    button.addEventListener("click", async () => {
      if (busy) return;
      const graph = button === withGraph ? graphSelection() : null;
      if (button === withGraph && !graph) return;
      const style = getComputedStyle(root);
      const marks = claims.map(toOverlay).filter(Boolean).map(mark => ({
        ...mark,
        color: pdfColor(style, mark.status),
      }));
      const graphCopy = graph && { ...graph, svg: graph.svg.cloneNode(true) };
      busy = true;
      buttons.forEach(control => { control.disabled = true; });
      status.textContent = "Preparing PDF…";
      try {
        const module = await import(options.dataset.exportSrc || new URL("./pdf-export-entry.js", import.meta.url).href);
        const response = await fetch(original);
        if (!response.ok) throw new Error("Original PDF could not be downloaded.");
        const bytes = await module.exportReaderPdf(await response.arrayBuffer(), marks, graphCopy);
        const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = graph ? "manuscript-with-evidence-graph.pdf" : "manuscript-highlighted.pdf";
        link.click();
        menu.open = false;
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        status.textContent = "";
      } catch (error) {
        status.textContent = error.message || "PDF export failed.";
      } finally {
        busy = false;
        buttons.forEach(control => { control.disabled = false; });
        update();
      }
    });
  }
  update();
  options.hidden = false;
}

function pdfColor(style, status) {
  const allowed = ["verified", "suspect", "unsourced", "mismatch", "missing", "registered"];
  const token = allowed.includes(status) ? status : "registered";
  const hex = style.getPropertyValue("--lp-status-" + token).trim();
  const digits = /^#[\da-f]{6}$/i.test(hex) ? hex.slice(1) : "6e7681";
  return digits.match(/../g).map(value => parseInt(value, 16) / 255);
}
