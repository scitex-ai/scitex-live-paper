import { withBundleContext } from "./_utils.js";

// Claims sidebar + per-claim Re-verify wire-up. Vanilla ES module.
// Imports the shared helpers + the bulk Re-verify-all button from the
// sibling modules so this file stays focused on per-claim rendering.

import { ensureClaimsSidebar } from "./_utils.js";
import { renderReverifyAllButton } from "./reverify-all.js";

export function renderClaimsSidebar(rootEl, claimsPayload, apiBase) {
  if (!claimsPayload || !Array.isArray(claimsPayload.claims)) return;

  const sidebar = ensureClaimsSidebar(rootEl);
  sidebar.hidden = false;
  bindClaimTabs(sidebar);
  const allClaims = sidebar.querySelector("#lp-all-claims-panel");
  const count = claimsPayload.claims.length;
  sidebar.querySelector("#lp-all-claims-tab").textContent = `All claims (${count})`;
  if (!count) {
    const message = document.createElement("p");
    message.textContent = "No claims are registered for this manuscript.";
    allClaims.append(message);
  }

  const reVerifyEnabled = !!claimsPayload.re_verify_enabled;
  const pinnedCommit = claimsPayload.pinned_commit || null;

  // "Re-verify all" — same visibility gate as per-claim button.
  if (reVerifyEnabled) {
    allClaims.append(renderReverifyAllButton(apiBase, pinnedCommit));
  }

  const container = document.createElement("div");
  container.className = "lp-claims-list";
  allClaims.querySelector("#lp-claim-type-results").append(container);
  return {
    feedContainer: container,
    bindClaimFilters: (setFilter) => bindClaimFilters(allClaims, claimsPayload.claims, setFilter),
    renderFeedEntry: (claim) => renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit),
  };
}

const claimTypes = new Set(["sentence", "value", "statistic", "table", "figure"]);

function normalize(text) {
  return String(text ?? "").normalize("NFKC").toLowerCase().trim();
}

function filterType(claim) {
  const type = normalize(claim.claim_type);
  if (type === "text") return "sentence";
  return claimTypes.has(type) ? type : "other";
}

function bindClaimFilters(panel, claims, setFilter) {
  if (!claims.length) return;
  const controls = panel.querySelector(".lp-claim-filters");
  const search = controls.querySelector("input");
  const tabList = controls.querySelector(".lp-claim-type-tabs");
  const results = panel.querySelector("#lp-claim-type-results");
  const status = results.querySelector(".lp-claim-filter-status");
  const index = claims.map((claim) => ({
    id: claim.claim_id,
    type: filterType(claim),
    text: normalize([claim.claim_id, claim.claim_value, claim.source_file, claim.file_path].join(" ")),
  }));
  tabList.querySelector('[data-claim-type="other"]').hidden = !index.some((entry) => entry.type === "other");
  let type = "all";
  bindTabs(tabList, (tab) => {
    type = tab.dataset.claimType;
    results.setAttribute("aria-labelledby", tab.id);
    update();
  });

  function update() {
    const terms = normalize(search.value).split(/\s+/).filter(Boolean);
    if (type === "all" && !terms.length) {
      setFilter(null);
      status.textContent = "";
      return;
    }
    const matched = new Set(index.filter((entry) =>
      (type === "all" || type === entry.type) && terms.every((term) => entry.text.includes(term))
    ).map((entry) => entry.id));
    setFilter((entry) => matched.has(entry.id));
    status.textContent = matched.size
      ? `${matched.size} of ${claims.length} claims`
      : "No claims match these filters.";
  }

  search.addEventListener("input", update);
  controls.hidden = false;
  update();
}

function bindClaimTabs(sidebar) {
  bindTabs(sidebar.querySelector(".lp-claims-tabs"), (selected, refresh) => {
    for (const tab of sidebar.querySelectorAll(".lp-claims-tabs > [role='tab']")) {
      sidebar.querySelector("#" + tab.getAttribute("aria-controls")).hidden = tab !== selected;
    }
    sidebar.scrollTop = 0;
    if (refresh && selected.id === "lp-selection-tab") {
      sidebar.dispatchEvent(new CustomEvent("live-paper:selection-tab", { bubbles: true }));
    }
  });
}

function bindTabs(tabList, onSelect) {
  const tabs = [...tabList.querySelectorAll(":scope > [role='tab']:not([hidden])")];
  function select(tab, refresh) {
    for (const button of tabs) {
      const active = button === tab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    }
    onSelect(tab, refresh);
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", (event) => select(tab, event.isTrusted));
    tab.addEventListener("keydown", (event) => {
      const direction = { ArrowLeft: -1, ArrowRight: 1 };
      if (!(event.key in direction) && !["Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1
        : (index + direction[event.key] + tabs.length) % tabs.length;
      select(tabs[next], true);
      tabs[next].focus();
    });
  });
}

export function renderClaimRow(claim, apiBase, reVerifyEnabled, pinnedCommit) {
  const li = document.createElement("div");
  li.className = "lp-claim";
  li.dataset.claimId = claim.claim_id;
  li.dataset.status = claim.status || "registered";
  li.classList.add("lp-claim-selectable");
  li.addEventListener("click", function (event) {
    // Buttons (Re-verify) keep their own handlers — row click opens detail.
    if (event.target.closest("button")) return;
    li.dispatchEvent(new CustomEvent("live-paper:claim", {
      bubbles: true, detail: { id: claim.claim_id, preview: false },
    }));
  });

  const valueSpan = document.createElement("span");
  valueSpan.className = "lp-claim-value";
  valueSpan.textContent =
    claim.claim_value || claim.file_path || "(no value)";
  li.appendChild(valueSpan);

  const statusBadge = document.createElement("span");
  statusBadge.className = "lp-claim-status";
  statusBadge.dataset.status = claim.status || "registered";
  statusBadge.textContent = claim.status || "registered";
  li.appendChild(statusBadge);

  // Re-verify button — only visible when PaperState.re_verify_enabled
  // (accepted/published + pinned_commit set). Hosts on draft/preprint
  // bundles see the claim row WITHOUT a button.
  if (reVerifyEnabled) {
    const btn = document.createElement("button");
    btn.className = "lp-claim-reverify";
    btn.type = "button";
    btn.textContent = "Re-verify";
    btn.dataset.claimId = claim.claim_id;
    btn.addEventListener("click", function () {
      void reverifyClaim(li, claim.claim_id, pinnedCommit, apiBase);
    });
    li.appendChild(btn);
  }

  return li;
}

export async function reverifyClaim(rowEl, claimId, pinnedCommit, apiBase) {
  const statusBadge = rowEl.querySelector(".lp-claim-status");
  const btn = rowEl.querySelector(".lp-claim-reverify");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Verifying…";
  }
  if (statusBadge) {
    statusBadge.dataset.status = "verifying";
    statusBadge.textContent = "verifying";
  }

  try {
    const body = { claim_id: claimId };
    if (pinnedCommit) body.pinned_commit = pinnedCommit;

    const res = await fetch(withBundleContext(apiBase + "claim/verify"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await res.json();
    if (res.ok) rowEl.dispatchEvent(new CustomEvent("live-paper:evidence-updated", { bubbles: true }));

    let nextStatus;
    let statusNote = "";
    if (res.status === 200 && payload.ok === true) {
      nextStatus = payload.status || "verified";
    } else if (res.status === 200 && payload.fallback === true) {
      nextStatus = payload.status || "stale";
      statusNote = payload.reason || "";
      console.info("[live-paper] re-verify fallback:", payload.reason);
    } else {
      nextStatus = "error";
      statusNote = payload.reason || payload.error || ("HTTP " + res.status);
      console.error("[live-paper] re-verify failed", res.status, payload);
    }

    rowEl.dataset.status = nextStatus;
    if (statusBadge) {
      statusBadge.dataset.status = nextStatus;
      statusBadge.textContent = nextStatus;
      // Beta-5: the reason was console-only — hover now tells the user why.
      if (statusNote) statusBadge.title = String(statusNote).slice(0, 240);
      else statusBadge.removeAttribute("title");
    }
  } catch (err) {
    console.error("[live-paper] re-verify network error", err);
    if (statusBadge) {
      statusBadge.dataset.status = "error";
      statusBadge.textContent = "error";
      statusBadge.title = String((err && err.message) || err).slice(0, 240);
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Re-verify";
    }
  }
}
