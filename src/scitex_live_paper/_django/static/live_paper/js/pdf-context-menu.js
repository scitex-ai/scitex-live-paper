import { bindPdfContextMenu as attachContextMenu } from "./pdf-provider.js";

export function bindPdfContextMenu(ContextMenu, viewer, { commentOnPage, revealSidebar }) {
  const pdf = viewer.container;
  return attachContextMenu({
    ContextMenu,
    container: pdf,
    scrollContainer: pdf.closest(".lp-reader-document") || pdf,
    canOpen: () => viewer.loaded,
    zoom: (action, point) => viewer.zoomAt(action, point),
    items(target, point) {
      const index = [...pdf.querySelectorAll(".stx-pdf-page")].indexOf(target.closest(".stx-pdf-page"));
      const page = index >= 0 ? index + 1 : viewer.currentPage();
      if (!page) return [];
      const note = index >= 0 && viewer.noteTarget(page, point);
      const overlay = target.closest(".lp-rich-overlay");
      const entries = [];
      if (overlay) entries.push({ label: "View claim evidence", onSelect: () => {
        revealSidebar();
        overlay.click();
      } });
      entries.push({
        label: note ? "Add note here" : "Comment on this page",
        onSelect: () => commentOnPage(page, note),
      });
      return entries;
    },
  });
}
