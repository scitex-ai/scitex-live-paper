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
import { bindPdfDownloads } from "./pdf-downloads.js";
import { PDFViewer } from "./pdf-viewer.js";
import { renderClaimDetail } from "./claim-details.js";
import { renderClaimsSidebar } from "./claims-sidebar.js";
import { renderReReviewBadge } from "./re-review-badge.js";
import { bindPortEvents } from "./port-events.js";
import { createEventLog, bindEventLog } from "./event-log.js";
import { fetchComments } from "./comments.js";
import { renderArchiveButton } from "./archive.js";
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
  // CCT 3000 overlay wiring: port bus serves evidence popups for
  // overlay regions; the event log records the session for the
  // archive sidecar (PDF + event-log). Both bind once at boot.
  bindPortEvents(rootEl, apiBase);
  const eventLog = createEventLog();
  bindEventLog(rootEl, eventLog);
  rootEl._livePaperEventLog = eventLog;
  // Archive action renders immediately (reads log + bundle lazily
  // at click time) so it survives failed boot RPCs.
  try {
    renderArchiveButton(rootEl, apiBase);
  } catch (err) {
    console.warn("[live-paper] archive button render failed", err);
  }

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
      if (event.detail?.preview && sidebar.dataset.pinnedClaim) return;
      if (!event.detail?.preview) sidebar.dataset.pinnedClaim = id;
      renderClaimDetail(sidebar, claim, apiBase);
    } catch (err) {
      console.warn("[live-paper] anchor detail render failed", err);
    }
  });

  const pdfContainer = ensurePdfContainer(rootEl);
  const viewer = new PDFViewer({
    ...sidebarOptions,
    evidencePane: true,
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
  if (await viewer.load()) {
    const download = rootEl.querySelector("#live-paper-download-pdf");
    if (download) {
      download.href = withBundleContext(apiBase + "pdf?download=1");
      download.hidden = false;
      bindPdfDownloads(rootEl, viewer.claims, download.href);
    }
  }
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
