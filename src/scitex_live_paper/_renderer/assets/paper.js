/* scitex-live-paper / paper page: navigate the paper through its claims.
 *
 * A CLASSIC script (not a module) on purpose: module scripts do not run
 * from file://, and the static site must work opened straight from disk.
 * Loaded after paper-panel.js (window.LivePaperPanel fills the panel).
 *
 * Reads the review-packet entries embedded in #lp-claims-data (needs
 * inspection first) and wires:
 *
 *   - claim marks: click / tap / Enter opens the evidence panel in place;
 *     modifier-click still follows the link to the full graph page;
 *   - the claims navigator: scrolls to the claim, highlights it, opens it;
 *   - Esc / the close button: closes the panel and restores focus;
 *   - #claim-<id> deep links open the panel on load, and every claim opened
 *     is a history entry, so back/forward step through them.
 */
(function () {
  'use strict';

  var dataEl = document.getElementById('lp-claims-data');
  var panel = document.getElementById('lp-claim-panel');
  var Panel = window.LivePaperPanel;
  if (!dataEl || !panel || !Panel) return;
  var claims;
  try {
    claims = JSON.parse(dataEl.textContent || '[]');
  } catch (err) {
    console.error('live-paper: unreadable claims data', err);
    return;
  }
  if (!Array.isArray(claims) || !claims.length) return;

  var byId = new Map();
  claims.forEach(function (c) { byId.set(c.claim_id, c); });
  var titleEl = document.getElementById('lp-claim-panel-title');
  var closeBtn = panel.querySelector('.lp-claim-panel-close');

  function markOf(id) {
    var m = id === null ? null : document.getElementById('claim-' + id);
    return m && m.matches('mark.lp-claim-span') ? m : null;
  }
  function markLink(id) {
    var m = markOf(id);
    return m ? m.querySelector('a') : null;
  }
  function navItem(id) {
    var found = null;
    document.querySelectorAll('.lp-claim-nav-item[data-claim-id]').forEach(function (a) {
      if (a.getAttribute('data-claim-id') === id) found = a;
    });
    return found;
  }

  // Reading order: marks in document order, then claims with no mark.
  // Inspection order: the packet's (not supported, not checkable, no graph).
  var readingOrder = [];
  var seen = new Set();
  document.querySelectorAll('mark.lp-claim-span[data-claim-id]').forEach(function (m) {
    var id = m.getAttribute('data-claim-id');
    if (byId.has(id) && !seen.has(id)) { seen.add(id); readingOrder.push(id); }
  });
  claims.forEach(function (c) { if (!seen.has(c.claim_id)) readingOrder.push(c.claim_id); });
  var inspectionOrder = claims.filter(function (c) { return c.needs_inspection; })
    .map(function (c) { return c.claim_id; });

  var current = null;
  var returnFocus = null;

  var ctx = {
    titleEl: titleEl,
    body: panel.querySelector('.lp-claim-panel-body'),
    readingOrder: readingOrder,
    inspectionOrder: inspectionOrder,
    inText: function (id) { return markOf(id) !== null; },
    isCurrent: function (id) { return current === id && !panel.hidden; },
    navigate: function (id) {
      returnFocus = null;
      openClaim(id, { push: true, focus: true, scroll: true });
    },
  };

  function idFromHash(hash) {
    if (!hash || hash.indexOf('#claim-') !== 0) return null;
    var raw = hash.slice(7);
    var id;
    try { id = decodeURIComponent(raw); } catch (e) { id = raw; }
    return byId.has(id) ? id : null;
  }
  function hashOf(id) { return '#claim-' + encodeURIComponent(id); }

  var NARROW = '(max-width: 760px)';
  function media(q) { return !!(window.matchMedia && window.matchMedia(q).matches); }

  function setActive(id) {
    document.querySelectorAll('mark.lp-claim-span[data-lp-active]').forEach(function (m) {
      m.removeAttribute('data-lp-active');
      m.classList.remove('lp-claim-flash');
    });
    document.querySelectorAll('mark.lp-claim-span a[aria-expanded]').forEach(function (a) {
      a.setAttribute('aria-expanded', 'false');
    });
    document.querySelectorAll('.lp-claim-nav-item[aria-current]').forEach(function (a) {
      a.removeAttribute('aria-current');
    });
    if (id === null) return;
    var m = markOf(id);
    if (m) {
      m.setAttribute('data-lp-active', '');
      var a = m.querySelector('a');
      if (a) a.setAttribute('aria-expanded', 'true');
    }
    var item = navItem(id);
    if (item) item.setAttribute('aria-current', 'true');
  }

  function scrollToClaim(id) {
    var m = markOf(id);
    if (!m) return;
    var behavior = media('(prefers-reduced-motion: reduce)') ? 'auto' : 'smooth';
    if (media(NARROW)) {
      // Bottom-sheet layout: keep the claim in the upper part of the page.
      var top = m.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top: Math.max(0, top), behavior: behavior });
    } else {
      m.scrollIntoView({ block: 'center', behavior: behavior });
    }
    m.classList.remove('lp-claim-flash');
    void m.offsetWidth; // restart the highlight flash
    m.classList.add('lp-claim-flash');
  }

  function openClaim(id, opts) {
    var c = byId.get(id);
    if (!c) return;
    if (opts.push && idFromHash(location.hash) !== id) {
      history.pushState({ claim: id }, '', hashOf(id));
    }
    var fresh = current !== id || panel.hidden;
    current = id;
    panel.hidden = false;
    panel.setAttribute('data-support', c.state);
    panel.setAttribute('data-claim-id', c.claim_id);
    if (fresh) Panel.render(ctx, c);
    document.body.classList.add('lp-panel-open');
    setActive(id);
    if (opts.scroll) scrollToClaim(id);
    if (opts.focus) titleEl.focus({ preventScroll: true });
  }

  function closePanel(opts) {
    if (panel.hidden) return;
    var was = current;
    panel.hidden = true;
    current = null;
    Panel.cancel();
    document.body.classList.remove('lp-panel-open');
    setActive(null);
    if (opts.push && idFromHash(location.hash) !== null) {
      history.pushState(null, '', location.pathname + location.search);
    }
    if (opts.restoreFocus) {
      var target = (returnFocus && document.contains(returnFocus) ? returnFocus : null) ||
        markLink(was) || navItem(was);
      if (target) target.focus();
    }
    returnFocus = null;
  }

  function syncFromHash() {
    var id = idFromHash(location.hash);
    if (id === null) closePanel({ push: false, restoreFocus: false });
    else if (id !== current || panel.hidden) openClaim(id, { push: false, focus: false, scroll: true });
  }

  function plainClick(ev) {
    return ev.button === 0 && !ev.metaKey && !ev.ctrlKey && !ev.shiftKey && !ev.altKey;
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target instanceof Element ? ev.target : null;
    if (!t || !plainClick(ev)) return;
    var link = t.closest('mark.lp-claim-span a');
    var item = link ? null : t.closest('.lp-claim-nav-item[data-claim-id]');
    var host = link ? link.closest('mark.lp-claim-span') : item;
    var id = host ? host.getAttribute('data-claim-id') : null;
    if (id === null || !byId.has(id)) return;
    ev.preventDefault();
    returnFocus = link || item;
    // From the text the claim is already in view (except under the narrow
    // layout's bottom sheet); from the navigator, go to it.
    openClaim(id, { push: true, focus: true, scroll: !link || media(NARROW) });
  });

  closeBtn.addEventListener('click', function () { closePanel({ push: true, restoreFocus: true }); });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && !panel.hidden) {
      ev.preventDefault();
      closePanel({ push: true, restoreFocus: true });
    }
  });

  window.addEventListener('popstate', syncFromHash);
  window.addEventListener('hashchange', syncFromHash);

  // Narrow screens: the navigator starts collapsed so the text comes first.
  var navBox = document.querySelector('.lp-claim-nav-box');
  if (navBox && media(NARROW)) navBox.open = false;

  var initial = idFromHash(location.hash);
  if (initial !== null) openClaim(initial, { push: false, focus: true, scroll: true });
  document.documentElement.setAttribute('data-lp-paper-ready', '');
})();
