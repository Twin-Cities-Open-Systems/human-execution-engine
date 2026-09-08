/* links.js -- every external link opens in a new tab, safely.
 *
 * section: 3
 *
 * Operator brief, verbatim: "external links should always open a new tab".
 *
 * target="_blank" on its own is a real vulnerability, not a style question:
 * without rel="noopener" the opened page gets a window.opener handle back to
 * the page that opened it and can navigate this tab somewhere else -- tab-
 * nabbing. Modern browsers imply noopener for target="_blank", but "modern
 * browsers" is not the guarantee a kiosk gets, so it is written out. noreferrer
 * goes with it so the destination is not handed this page's URL.
 *
 * WHAT COUNTS AS EXTERNAL
 *   an http: or https: link whose origin differs from this page's.
 * Everything else is left exactly as authored: same-origin links, fragments,
 * mailto:, tel:, and any other scheme.
 *
 * OPT OUT, per link or per subtree:
 *   <a href="..." data-tc-external="keep">        this link is left alone
 *   <div data-tc-links-skip> ... </div>           nothing inside is touched
 *   <a href="..." download>                       downloads are left alone
 *
 * Links that already carry an explicit target keep it; only their rel is
 * repaired, because overriding an author's stated target would be the script
 * deciding it knows better.
 *
 * A screen reader gets told the link opens a new tab -- an unannounced context
 * switch is disorienting, and WCAG 3.2.5 asks for the warning.
 *
 * Zero dependencies. No build step. Does nothing if the page has no links.
 */
(function (window, document) {
  "use strict";

  if (!document.querySelectorAll) { return; }

  var STYLE_ID = "tc-links-style";
  var HINT = "(opens in a new tab)";

  var CSS = [
    ".tc-sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;",
    "overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}"
  ].join("");

  function each(list, fn) {
    if (!list) { return; }
    for (var i = 0; i < list.length; i++) { fn(list[i], i); }
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) { return; }
    var s = document.createElement("style");
    s.id = STYLE_ID;
    s.appendChild(document.createTextNode(CSS));
    (document.head || document.documentElement).appendChild(s);
  }

  function inSkippedSubtree(a) {
    var n = a;
    while (n && n.nodeType === 1) {
      if (n.hasAttribute("data-tc-links-skip")) { return true; }
      n = n.parentNode;
    }
    return false;
  }

  /* The anchor's own resolved properties are used rather than the raw href
   * string: the browser has already resolved "../x", "//host/x" and any
   * <base> on the page, and comparing resolved origins is the only comparison
   * that is actually right. */
  function isExternal(a) {
    if (a.protocol !== "http:" && a.protocol !== "https:") { return false; }
    if (!a.host) { return false; }
    return (a.protocol + "//" + a.host) !== (window.location.protocol + "//" + window.location.host);
  }

  function addRel(a) {
    var rel = (a.getAttribute("rel") || "").split(/\s+/);
    var have = {};
    var out = [];
    for (var i = 0; i < rel.length; i++) {
      if (!rel[i] || have[rel[i]]) { continue; }
      have[rel[i]] = true;
      out.push(rel[i]);
    }
    if (!have.noopener) { out.push("noopener"); }
    if (!have.noreferrer) { out.push("noreferrer"); }
    a.setAttribute("rel", out.join(" "));
  }

  function addHint(a) {
    if (a.getAttribute("data-tc-links-nohint") !== null) { return; }
    if (a.querySelector(".tc-sr-only")) { return; }
    /* An aria-label would replace the link's whole accessible name and lose
     * any markup inside it, so the hint is appended as visually-hidden text
     * instead -- read out, never seen, never affecting layout. */
    if (a.getAttribute("aria-label") || a.getAttribute("aria-labelledby")) { return; }
    if ((a.textContent || "").indexOf("new tab") > -1) { return; }
    var span = document.createElement("span");
    span.className = "tc-sr-only";
    span.appendChild(document.createTextNode(" " + HINT));
    a.appendChild(span);
  }

  function apply(a) {
    if (a.getAttribute("data-tc-links-bound") === "true") { return; }
    if (a.getAttribute("data-tc-external") === "keep") { return; }
    if (a.hasAttribute("download")) { return; }
    if (inSkippedSubtree(a)) { return; }

    var already = a.getAttribute("target");

    if (already === "_blank") {
      /* Author asked for a new tab and may not have said noopener. Repair the
       * rel whether the link is external or not: the opener handle is handed
       * over either way. */
      a.setAttribute("data-tc-links-bound", "true");
      addRel(a);
      addHint(a);
      return;
    }
    if (already) { return; }              /* explicit _self, a named frame: honored */
    if (!isExternal(a)) { return; }

    a.setAttribute("data-tc-links-bound", "true");
    a.setAttribute("target", "_blank");
    a.setAttribute("data-tc-external", "true");
    addRel(a);
    addHint(a);
  }

  function init(root) {
    root = root || document;
    var links = root.querySelectorAll("a[href]");
    if (!links.length) { return; }
    injectStyle();
    each(links, apply);
  }

  window.TC = window.TC || {};
  window.TC.links = { init: init, apply: apply, isExternal: isExternal };

  ready(function () { init(document); });
})(window, document);
