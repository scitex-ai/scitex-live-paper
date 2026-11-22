import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

export async function exportReaderPdf(original, marks, graph) {
  const pdf = await PDFDocument.load(original, { updateMetadata: false });
  for (const mark of marks) {
    const page = pdf.getPages()[mark.page - 1];
    if (!page || mark.bbox.length !== 4) continue;
    const [x0, y0, x1, y1] = mark.bbox;
    if (![x0, y0, x1, y1].every(Number.isFinite) || x1 <= x0 || y1 <= y0) continue;
    const color = rgb(...mark.color);
    const rect = { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
    if (mark.appearance === "region") {
      page.drawRectangle({ ...rect, borderColor: color, borderWidth: 1.5 });
    } else {
      page.drawRectangle({ ...rect, color, opacity: .27 });
    }
  }
  if (graph) await appendGraph(pdf, graph);
  return pdf.save();
}

async function appendGraph(pdf, graph) {
  const { svg, claim } = graph;
  const view = svg.viewBox.baseVal;
  if (!view.width || !view.height) throw new Error("Evidence graph is not ready.");
  const scale = Math.min(2, 3800 / Math.max(view.width, view.height));
  const width = Math.max(1, Math.ceil(view.width * scale));
  const height = Math.max(1, Math.ceil(view.height * scale));
  const copy = svg.cloneNode(true);
  copy.removeAttribute("style");
  copy.setAttribute("width", width);
  copy.setAttribute("height", height);
  const xml = new XMLSerializer().serializeToString(copy);
  const image = new Image();
  image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
  await image.decode();
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Unable to render the evidence graph.");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0);
  const raster = await pdf.embedPng(canvas.toDataURL("image/png"));
  const pageWidth = 842;
  const pageHeight = 595;
  const padding = 36;
  const rendered = raster.scaleToFit(pageWidth - 2 * padding, pageHeight - 3 * padding);
  const page = pdf.addPage([pageWidth, pageHeight]);
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  // Built-in PDF label font uses WinAnsi. The graph itself keeps its Unicode labels.
  const caption = ("Evidence graph · " + claim).replace(/[^\x20-\x7e]/g, " ").slice(0, 110);
  page.drawText(caption, { x: padding, y: pageHeight - padding, size: 15, font });
  page.drawImage(raster, { x: padding, y: pageHeight - 2 * padding - rendered.height,
    width: rendered.width, height: rendered.height });
}
