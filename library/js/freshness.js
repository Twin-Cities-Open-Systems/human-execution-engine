/* freshness.js -- how old is this page, and say so in a hue.
 *
 * section: 3
 *
 * Operator brief, 2026-09-10, verbatim: "standardize on a freshness that
 * works, changes color (hue) when stale (12h is stale, default)". Until this
 * file, every view.lab page carried a data-tc-epoch that nothing read, so a
 * page from last week looked exactly like one from this morning.
 *
 * MARKUP
 *   <section class="card" data-tc-epoch="1789024938">           the source's commit time, unix seconds
 *   <section class="card" data-tc-epoch="..." data-tc-stale-hours="24">   per-page threshold
 *
 * What it does, for every [data-tc-epoch]:
 *   - sets data-tc-fresh="ok" or "stale" on the element (stale = older than
 *     data-tc-stale-hours, default 12), and the same on <html> for the page's
 *     first such element so a page-wide rule can key on it;
 *   - adds one pill inside the element's header (or at its top) reading
 *     "● OK · 3h" or "▲ STALE · 2d 4h" -- icon AND label, never a color alone,
 *     per the org's status-output rule;
 *   - re-evaluates once a minute, so a page left open turns stale on its own;
 *   - an empty or non-numeric epoch (a source not yet committed) is reported
 *     as "○ UNKNOWN · not committed" and gets data-tc-fresh="unknown".
 *
 * Hue comes from the host page's own tokens when it has them
 * (--good/--warning/--muted and their -bg pairs, the same names view.css and
 * the org's render view use), with plain fallbacks otherwise, so the file
 * works on any static tree. The element's left border takes the hue too, so
 * the state is visible with the card collapsed.
 *
 * Zero dependencies. No build step. Does nothing if no matching markup exists.
 */
(function (window, document) {
  "use strict";

  if (!document.querySelectorAll) { return; }

  var STYLE_ID = "tc-freshness-style";
  var DEFAULT_STALE_HOURS = 12;
  var TICK_MS = 60000;

  var CSS = [
    "[data-tc-fresh='ok']{border-left-color:var(--good,#2e8b57)!important}",
    "[data-tc-fresh='stale']{border-left-color:var(--warning,#c98a00)!important}",
    "[data-tc-fresh='unknown']{border-left-color:var(--muted,#888)!important}",
    ".tc-fresh-pill{display:inline-flex;align-items:center;gap:.32rem;font-family:ui-monospace,monospace;",
    "  font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;padding:.12rem .5rem;border-radius:999px;",
    "  margin-left:.5rem;white-space:nowrap;vertical-align:middle}",
    ".tc-fresh-pill[data-tc-fresh='ok']{color:var(--good,#2e8b57);background:var(--good-bg,rgba(46,139,87,.12))}",
    ".tc-fresh-pill[data-tc-fresh='stale']{color:var(--warning,#c98a00);background:var(--warning-bg,rgba(201,138,0,.14))}",
    ".tc-fresh-pill[data-tc-fresh='unknown']{color:var(--muted,#888);background:var(--sunk,rgba(128,128,128,.12))}"
  ].join("\n");

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) { return; }
    var s = document.createElement("style");
    s.id = STYLE_ID;
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  function ageText(seconds) {
    var m = Math.floor(seconds / 60), h = Math.floor(m / 60), d = Math.floor(h / 24);
    if (d > 0) { return d + "d " + (h - d * 24) + "h"; }
    if (h > 0) { return h + "h " + (m - h * 60) + "m"; }
    return m + "m";
  }

  function judge(el) {
    var raw = (el.getAttribute("data-tc-epoch") || "").trim();
    var epoch = /^\d+$/.test(raw) ? parseInt(raw, 10) : NaN;
    var hours = parseFloat(el.getAttribute("data-tc-stale-hours"));
    if (!(hours > 0)) { hours = DEFAULT_STALE_HOURS; }
    if (isNaN(epoch)) {
      return { state: "unknown", icon: "○", label: "UNKNOWN", detail: "not committed" };
    }
    var age = Math.max(0, Math.floor(Date.now() / 1000) - epoch);
    var stale = age >= hours * 3600;
    return {
      state: stale ? "stale" : "ok",
      icon: stale ? "▲" : "●",
      label: stale ? "STALE" : "OK",
      detail: ageText(age) + (stale ? " · >" + hours + "h" : "")
    };
  }

  function pillFor(el) {
    var pill = el.querySelector(":scope > header .tc-fresh-pill, :scope > .tc-fresh-pill");
    if (pill) { return pill; }
    pill = document.createElement("span");
    pill.className = "tc-fresh-pill";
    pill.setAttribute("role", "status");
    var header = el.querySelector(":scope > header");
    var toggle = header && header.querySelector("h1,h2,h3,[data-tc-collapse-toggle]");
    if (toggle && toggle.parentNode === header) {
      header.insertBefore(pill, toggle.nextSibling);
    } else if (header) {
      header.appendChild(pill);
    } else {
      el.insertBefore(pill, el.firstChild);
    }
    return pill;
  }

  function render(el, first) {
    var v = judge(el);
    el.setAttribute("data-tc-fresh", v.state);
    if (first) { document.documentElement.setAttribute("data-tc-fresh", v.state); }
    var pill = pillFor(el);
    pill.setAttribute("data-tc-fresh", v.state);
    pill.textContent = v.icon + " " + v.label + " · " + v.detail;
    pill.title = v.state === "unknown"
      ? "This page's source is not committed, so it has no freshness."
      : "Source last changed " + v.detail.split(" · ")[0] + " ago. Stale after "
        + (parseFloat(el.getAttribute("data-tc-stale-hours")) || DEFAULT_STALE_HOURS) + "h.";
  }

  function run() {
    var els = document.querySelectorAll("[data-tc-epoch]");
    if (!els.length) { return; }
    ensureStyle();
    for (var i = 0; i < els.length; i++) { render(els[i], i === 0); }
  }

  function start() {
    run();
    if (document.querySelectorAll("[data-tc-epoch]").length) {
      window.setInterval(run, TICK_MS);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window, document);
