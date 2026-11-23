// Live-paper SPA viewer — thin orchestrator. Loads PDF.js, runs the
// boot RPCs (ping + bundle-info + claims), mounts the PDFViewer +
// claims sidebar. The actual rendering / sidebar / re-verify logic
// lives in sibling modules so each file stays focused.
//
// Module layout (under _django/static/live_paper/js/):
//   - viewer.js          (this file — orchestrator, public global)
//   - pdf-viewer.js      (PDFViewer class + claim-anchor overlays)
//   - claim-overlays.js  (anchor bbox -> overlay regions, port attrs)
//   - port-events.js     (evidence-request bus + popup chrome)
//   - event-log.js       (overlay event-log sidecar for archive replay)
//   - claims-sidebar.js  (sidebar + per-claim Re-verify)
//   - reverify-all.js    (bulk Re-verify-all button)
//   - _utils.js          (shared helpers)
//
// Vanilla ES modules — no Vite / TS build needed. The HTML templates
// load this file with `type="module"` so dynamic + static imports
// work without ceremony.

import {
  normalizeBase,
  withBundleContext,
  fetchJson,
  fetchOrNull,
  setStatus,
  ensurePdfContainer,
  ensureClaimsSidebar,
  renderError,
} from "./_utils.js";
import { bindShare, openSharedClaim } from "./share.js";
import { bindPdfDownloads } from "./pdf-downloads.js";
import { PDFViewer, toOverlay } from "./pdf-viewer.js";
import { bindPdfContextMenu } from "./pdf-context-menu.js";
import { closeClaimDetail, invalidateEvidenceGraphs, renderCitationDetail, renderClaimDetail } from "./claim-details.js";
import { bindTabs, renderClaimsSidebar } from "./claims-sidebar.js";
import { renderReReviewBadge } from "./re-review-badge.js";
import { bindPortEvents } from "./port-events.js";
import { createEventLog, bindEventLog } from "./event-log.js";
import { fetchComments, showComments } from "./comments.js";
import { isMissingPaper, renderEmptyState } from "./empty-state.js";
import { hideLoading } from "./_utils.js";

// PDF.js vendor bundle lives next to this module under staticfiles
// (live_paper/pdfjs/). Resolve it from `import.meta.url` — never from
// the API base: the API base moves with the mount point (standalone
// root vs hub /apps/live-paper/api/), while static files always sit
// beside this module. The old apiBase-relative join built
// /pdfjs/... (404) instead of /static/live_paper/pdfjs/....
const pdfjsUrl = new URL("../pdfjs/pdf.min.mjs", import.meta.url).href;
const pdfjsWorkerUrl = new URL(
  "../pdfjs/pdf.worker.min.mjs",
  import.meta.url
).href;

const root = document.getElementById("live-paper-root");
if (!root) {
  console.error("[live-paper] root element missing");
} else {
  boot(root);
}

async function boot(rootEl) {
  const apiBase = normalizeBase(rootEl.getAttribute("data-api-base") || "/api/");
  // Project picker into the canonical AppHeader slot (stats
  // pattern): the header component mounts on DOMContentLoaded, which
  // runs after this module — move now if the slot exists, else once
  // when it appears.
  movePickerIntoHeaderSlot(rootEl);
  // Empty state first: the mount wrapper renders the shell with a
  // reason when no bundle resolved (HTTP 200, no RPCs to boot
  // against). Guidance now, viewer later.
  const emptyReason = rootEl.getAttribute("data-empty-reason") || "";
  if (emptyReason) {
    hideLoading(rootEl);
    renderEmptyState(rootEl, emptyReason);
    return;
  }
  bindReaderLayout(rootEl);
  bindPdfTheme(rootEl);
  // CCT 3000 overlay wiring: port bus serves evidence popups for
  // overlay regions; the event log records the session for the
  // archive sidecar (PDF + event-log). Both bind once at boot.
  bindPortEvents(rootEl, apiBase);
  const eventLog = createEventLog();
  bindEventLog(rootEl, eventLog);
  rootEl._livePaperEventLog = eventLog;
  let pdfjs;
  let createPdfViewer;
  try {
    const factoryUrl = rootEl.dataset.pdfFactory;
    if (!factoryUrl) throw new Error("SDK PDF factory URL missing");
    ({ createPdfViewer } = await import(factoryUrl));
    pdfjs = await import(pdfjsUrl);
    pdfjs.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl;
  } catch (err) {
    console.error("[live-paper] PDF.js failed to load", err);
    renderError("PDF.js bundle not available at " + pdfjsUrl);
    return;
  }

  // Boot RPCs — prefer the merged `dashboard` endpoint (one round-trip
  // returning bundle-info + claims in one go). Falls back to the
  // 3-call path if dashboard isn't served by the backend yet (so SPA
  // bundles built after this PR keep working against develop snapshots
  // that haven't picked up `api/dashboard`).
  let bundleInfo = null;
  let claimsPayload = null;

  try {
    const ping = await fetchJson(apiBase + "ping");
    if (!ping || ping.ok !== true) {
      throw new Error("ping returned non-ok: " + JSON.stringify(ping));
    }

    const dash = await fetchOrNull(apiBase + "dashboard");
    if (dash && dash.bundle && dash.claims) {
      bundleInfo = dash.bundle;
      claimsPayload = dash.claims;
    } else {
      // Fallback: separate calls. Keeps old backends working + lets
      // the SPA boot in environments where the dashboard endpoint
      // isn't reachable (e.g. an early hub-side wrapper that hasn't
      // re-deployed).
      bundleInfo = await fetchJson(apiBase + "bundle-info");
      claimsPayload = await fetchJson(apiBase + "claims");
    }

    setStatus(bundleInfo);
    rootEl.dataset.paperStage = bundleInfo.paper_state?.stage || "";
    void renderTraceSummary(rootEl, apiBase);
    renderReReviewBadge(rootEl, bundleInfo);
    // Stash for the Archive action (archive.js reads it lazily at
    // click time, so the button renders even when boot RPCs fail).
    rootEl._livePaperBundle = bundleInfo;
  } catch (err) {
    console.error("[live-paper] boot RPCs failed", err);
    // Missing paper (unpinned bundle, resolver 404) gets guidance,
    // not a raw JSON dump — same empty state as the mount wrapper.
    if (isMissingPaper(String((err && err.message) || err))) {
      hideLoading(rootEl);
      renderEmptyState(rootEl, String((err && err.message) || err));
    } else {
      setStatus({ error: String(err) });
    }
  }

  // Claims sidebar — best-effort; if the claims payload didn't land
  // (boot RPC raised), the PDF viewer still mounts.
  let sidebarOptions;
  if (claimsPayload) {
    try {
      sidebarOptions = renderClaimsSidebar(rootEl, claimsPayload, apiBase);
    } catch (err) {
      console.warn("[live-paper] claims sidebar render failed", err);
    }
  }

  rootEl.addEventListener("live-paper:evidence-updated", () => {
    invalidateEvidenceGraphs();
    closeClaimDetail(ensureClaimsSidebar(rootEl));
  });

  function showClaim(sidebar, claim, refresh) {
    const overlay = toOverlay(claim);
    renderClaimDetail(sidebar, claim, apiBase, {
      refresh,
      goToPdf: overlay && (() => {
        showPdf();
        hideEvidenceDrawer(rootEl)?.focus({ preventScroll: true });
        viewer.goToClaim(overlay);
      }),
    });
  }

  rootEl.addEventListener("live-paper:selection-tab", (event) => {
    const sidebar = event.target;
    const id = sidebar.querySelector(".lp-claim-detail")?.dataset.claimId;
    const claim = claimsPayload?.claims?.find((entry) => entry.claim_id === id);
    if (claim) showClaim(sidebar, claim, true);
  });

  // The PDF and the claim list both open the evidence sidebar.
  rootEl.addEventListener("live-paper:claim", (event) => {
    const id = event && event.detail ? event.detail.id : null;
    const claims =
      claimsPayload && Array.isArray(claimsPayload.claims)
        ? claimsPayload.claims
        : [];
    const claim = claims.find((c) => c && c.claim_id === id);
    if (!claim) return;
    try {
      const sidebar = ensureClaimsSidebar(rootEl);
      if (event.detail?.preview &&
          (sidebar.dataset.pinnedClaim || !sidebar.querySelector("#lp-comments-panel").hidden)) return;
      if (!event.detail?.preview) {
        sidebar.removeAttribute("data-document-focused");
        sidebar.dataset.pinnedClaim = id;
      }
      showClaim(sidebar, claim, !event.detail?.preview);
    } catch (err) {
      console.warn("[live-paper] anchor detail render failed", err);
    }
  });

  const pdfContainer = ensurePdfContainer(rootEl);
  const navigation = rootEl.querySelector("#live-paper-navigation");
  const showPdf = bindManuscriptFormats(rootEl, navigation);
  const viewer = new PDFViewer({
    ...sidebarOptions,
    showPdf,
    evidencePane: true,
    citationVerification: claimsPayload?.citation_verification,
    onCitationSelect(key, citation, goToReference) {
      const sidebar = ensureClaimsSidebar(rootEl);
      showEvidenceDrawer(rootEl);
      renderCitationDetail(sidebar, key, citation, apiBase, goToReference);
    },
    navigation: {
      container: navigation,
    },
    container: pdfContainer,
    pdfjs: pdfjs,
    createPdfViewer,
    workerSrc: pdfjsWorkerUrl,
    apiBase: apiBase,
  });
  // Overlay regions paint from the same claims payload as the
  // sidebar, so sidebar rows and PDF regions never disagree.
  if (claimsPayload && Array.isArray(claimsPayload.claims)) {
    viewer.setClaims(claimsPayload.claims);
  }
  // Comment badges + region markers (provider item 4):
  // best-effort — the viewer works fine with zero comments.
  try {
    viewer.setComments(await fetchComments(apiBase));
  } catch (err) {
    console.warn("[live-paper] comments boot fetch failed", err);
  }
  let commentTarget;
  function openComments(sidebar, { page, note, focus }) {
    const panel = sidebar.querySelector("#lp-comments-panel");
    const ready = showComments(panel, {
      apiBase,
      page,
      note,
      claimId: sidebar.querySelector("#lp-selection-panel .lp-claim-detail")?.dataset.claimId,
      onComments: (comments) => viewer.setComments(comments),
    });
    if (focus) void ready.then(() => {
      if (!panel.hidden) panel.querySelector("textarea")?.focus();
    });
  }
  rootEl.addEventListener("live-paper:comments-tab", (event) => {
    openComments(event.target, commentTarget ?? { page: viewer.currentPage() });
  });
  const download = rootEl.querySelector("#live-paper-download-pdf");
  if (bundleInfo && download) {
    download.href = withBundleContext(apiBase + "pdf?download=1");
    bindPdfDownloads(rootEl, viewer.claims, download.href);
  }
  const menuUrl = rootEl.dataset.pdfContextMenu;
  if (menuUrl) {
    import(menuUrl).then(({ ContextMenu }) => {
      viewer.stopContextMenu = bindPdfContextMenu(ContextMenu, viewer, {
        revealSidebar: () => showEvidenceDrawer(rootEl),
        commentOnPage(page, note) {
          const sidebar = ensureClaimsSidebar(rootEl);
          showEvidenceDrawer(rootEl);
          const tab = sidebar.querySelector("#lp-comments-tab");
          if (tab.getAttribute("aria-selected") === "true") {
            openComments(sidebar, { page, note, focus: true });
          } else {
            commentTarget = { page, note, focus: true };
            tab.click();
            commentTarget = null;
          }
          tab.focus({ preventScroll: true });
        },
      });
    }).catch((error) => console.warn("[live-paper] PDF actions unavailable", error));
  }
  await viewer.load();
  const shareStatus = bindShare(rootEl);
  openSharedClaim(rootEl, viewer.claims, shareStatus);
}

/**
 * Move the server-rendered project picker (`[data-stx-project-picker]`)
 * into the AppHeader's canonical slot. The header component mounts on
 * DOMContentLoaded — after this module runs — so move immediately
 * when the slot already exists, otherwise once via MutationObserver.
 */
export async function renderTraceSummary(rootEl, apiBase) {
  const url = new URL("../review.json", new URL(apiBase, location.href));
  const packet = await fetchOrNull(url.href);
  if (!packet?.counts) return;
  const banner = rootEl.querySelector("#live-paper-trace-status");
  if (!banner) return;
  const summary = document.createElement("a");
  summary.className = "lp-trace-summary";
  summary.href = withBundleContext(url.href);
  const total = packet.supported.length + packet.needs_inspection.length;
  if (total === 0) return;
  const provider = packet.provider?.name;
  const label = typeof provider === "string" && provider
    ? `${provider[0].toUpperCase()}${provider.slice(1)} calculation traces`
    : "Calculation traces";
  const verified = document.createElement("strong");
  verified.className = "lp-trace-verified";
  verified.textContent = packet.counts.supported + " verified";
  const inspect = document.createElement("strong");
  inspect.className = "lp-trace-inspect";
  inspect.textContent = packet.needs_inspection.length + " to inspect";
  summary.dataset.needsInspection = String(packet.needs_inspection.length > 0);
  summary.append(label, " · ", verified, " · ", inspect);
  banner.replaceChildren(summary);
  banner.hidden = false;
}

function showEvidenceDrawer(rootEl) {
  const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
  if (getComputedStyle(toggle).display !== "none" && toggle.getAttribute("aria-expanded") === "false") {
    toggle.click();
  }
}

function hideEvidenceDrawer(rootEl) {
  const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
  if (getComputedStyle(toggle).display === "none") return null;
  const sidebar = rootEl.querySelector("#live-paper-claims");
  sidebar.removeAttribute("data-drawer-open");
  sidebar.setAttribute("data-document-focused", "");
  toggle.setAttribute("aria-expanded", "false");
  return toggle;
}

function bindManuscriptFormats(rootEl, navigation) {
  const tabs = rootEl.querySelector(".lp-format-tabs");
  if (!tabs) return () => {};
  const pdfTab = tabs.querySelector("#lp-format-pdf");
  const pdf = rootEl.querySelector("#lp-format-panel-pdf");
  const html = rootEl.querySelector("#lp-format-panel-html");
  const frame = html.querySelector("iframe");
  bindTabs(tabs, (selected) => {
    const showPdf = selected === pdfTab;
    rootEl.dataset.manuscriptFormat = showPdf ? "pdf" : "html";
    pdf.hidden = navigation.hidden = !showPdf;
    html.hidden = showPdf;
    if (!showPdf) {
      hideEvidenceDrawer(rootEl);
      if (!frame.hasAttribute("src")) frame.src = frame.dataset.src;
    }
  });
  window.addEventListener("message", (event) => {
    if (html.hidden || event.origin !== location.origin || event.source !== frame.contentWindow ||
        event.data?.type !== "live-paper:html-claim" || typeof event.data.id !== "string") return;
    rootEl.dispatchEvent(new CustomEvent("live-paper:claim", { detail: { id: event.data.id } }));
  });
  return () => { if (pdf.hidden) pdfTab.click(); };
}

function bindPdfTheme(rootEl) {
  const picker = rootEl.querySelector(".lp-pdf-theme");
  const key = "live-paper.pdf-theme";
  let saved;
  try {
    saved = localStorage.getItem(key);
  } catch { /* Embedded readers can have storage disabled. */ }
  if (saved === "light" || saved === "dark") picker.value = saved;
  rootEl.dataset.pdfTheme = picker.value;
  picker.closest("label").hidden = false;
  picker.addEventListener("change", () => {
    rootEl.dataset.pdfTheme = picker.value;
    try {
      localStorage.setItem(key, picker.value);
    } catch { /* The displayed preference still applies for this session. */ }
  });
}

function bindReaderLayout(rootEl) {
  const header = rootEl.previousElementSibling;
  const shell = rootEl.closest("#main-content");
  const fitReader = () => {
    const top = rootEl.getBoundingClientRect().top;
    const bottom = shell?.getBoundingClientRect().bottom;
    const height = Math.floor(Math.min(bottom ?? window.innerHeight, window.innerHeight) - top);
    if (height > 0) rootEl.style.setProperty("--lp-reader-height", height + "px");
  };
  const observer = new ResizeObserver(fitReader);
  if (shell) observer.observe(shell);
  if (header) observer.observe(header);
  window.addEventListener("resize", fitReader);
  fitReader();

  const toggle = rootEl.querySelector(".lp-reader-evidence-toggle");
  const sidebar = rootEl.querySelector("#live-paper-claims");
  toggle.addEventListener("click", () => {
    sidebar.removeAttribute("data-document-focused");
    const open = sidebar.toggleAttribute("data-drawer-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

function movePickerIntoHeaderSlot(rootEl) {
  // The Django template places the picker in the header immediately
  // before the viewer main, not inside that main. Keep placement scoped
  // to this leaf header so an embedded viewer cannot move a host picker.
  const headerRoot = rootEl.previousElementSibling;
  if (!headerRoot?.matches("[data-stx-app-header]")) return;
  const picker = headerRoot.querySelector("[data-stx-project-picker]");
  if (!picker) return;
  const move = () => {
    const slot = headerRoot.querySelector(".stx-app-header__slot--project-selector");
    if (picker && slot && picker.parentElement !== slot) {
      slot.appendChild(picker);
      return true;
    }
    return Boolean(picker && slot);
  };
  if (move()) return;
  const observer = new MutationObserver(() => {
    if (move()) observer.disconnect();
  });
  observer.observe(headerRoot, { childList: true, subtree: true });
}

// Legacy native-adapter global for existing standalone automation.
// New consumers use the generic public rich PDF provider, not this adapter.
window.LivePaperPDFViewer = PDFViewer;
