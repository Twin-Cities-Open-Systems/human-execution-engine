/* collapse.js -- collapse and expand any card, state remembered per card.
 *
 * section: 3
 *
 * Operator brief, verbatim: "should be able to collaplse/expand each card at
 * will". State is persisted in localStorage keyed by page path plus card id,
 * so a collapsed card stays collapsed across reloads.
 *
 * MARKUP
 *   <section data-tc-collapse="fleet-hosts">
 *     <h2 data-tc-collapse-toggle>Fleet hosts</h2>
 *     <div data-tc-collapse-body> ... </div>
 *   </section>
 *
 * The persistence id is the value of data-tc-collapse, falling back to the
 * element's id. A card with neither is still collapsible but is NOT persisted
 * -- it has no stable name to store under, and inventing one from DOM position
 * would silently reassign state the moment the page reorders (which arrange.js
 * exists to do).
 *
 * data-tc-collapse-toggle is optional: without it the first heading, <summary>
 * or .tc-card-head inside the card is used, and if there is none a button is
 * created. data-tc-collapse-body is optional too: without it every child of
 * the card except the toggle is hidden when collapsed.
 *
 * data-tc-collapse-default="collapsed" starts a card collapsed the first time
 * it is seen (stored state always wins after that).
 *
 * Zero dependencies. No build step. Does nothing if no matching markup exists.
 */
(function (window, document) {
  "use strict";

  if (!document.querySelectorAll) { return; }

  var STYLE_ID = "tc-collapse-style";
  var KEY_PREFIX = "tc.collapse.";

  var CSS = [
    "[data-tc-collapse][data-tc-collapsed='true'][data-tc-collapse-mode='body'] [data-tc-collapse-body]",
    "{display:none}",
    "[data-tc-collapse][data-tc-collapsed='true'][data-tc-collapse-mode='children']",
    ">*:not([data-tc-collapse-head])",
    "{display:none}",
    "[data-tc-collapse-head]{cursor:pointer;user-select:none;-webkit-user-select:none}",
    "[data-tc-collapse-head]:focus-visible{outline:2px solid var(--accent,#2f6feb);outline-offset:2px}",
    ".tc-collapse-marker{display:inline-block;width:1em;margin-right:.35em;",
    "font-size:.8em;color:var(--ink-faint,#6b7280);transform-origin:50% 50%}",
    "[data-tc-collapsed='true'] .tc-collapse-marker{transform:rotate(-90deg)}",
    "@media (prefers-reduced-motion:no-preference){",
    ".tc-collapse-marker{transition:transform .12s ease}}",
    ".tc-collapse-btn{display:block;width:100%;text-align:left;font:inherit;",
    "color:inherit;background:none;border:0;padding:0;cursor:pointer}"
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

  /* localStorage throws in private mode and is absent on file:// in some
   * browsers. A storage failure must degrade to "not remembered", never to a
   * broken page. */
  function storeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function storeSet(key, value) {
    try { window.localStorage.setItem(key, value); return true; } catch (e) { return false; }
  }

  function pageKey() {
    return window.location.pathname || "/";
  }

  function idOf(card) {
    return card.getAttribute("data-tc-collapse") || card.id || "";
  }

  function findToggle(card) {
    var t = card.querySelector("[data-tc-collapse-toggle]");
    if (t) { return t; }
    /* Direct children only, scanned by hand rather than with ":scope >" --
     * a nested card's heading must not become the outer card's toggle. */
    var kids = card.children;
    for (var i = 0; i < kids.length; i++) {
      var name = kids[i].tagName.toLowerCase();
      if (name === "summary" || /^h[1-6]$/.test(name) ||
          (" " + (kids[i].getAttribute("class") || "") + " ").indexOf(" tc-card-head ") > -1) {
        return kids[i];
      }
    }
    var made = document.createElement("button");
    made.type = "button";
    made.className = "tc-collapse-btn";
    made.appendChild(document.createTextNode(card.getAttribute("data-tc-collapse-label") || "Toggle"));
    card.insertBefore(made, card.firstChild);
    return made;
  }

  function apply(card, collapsed) {
    card.setAttribute("data-tc-collapsed", collapsed ? "true" : "false");
    var toggle = card.querySelector("[data-tc-collapse-head]");
    if (toggle) { toggle.setAttribute("aria-expanded", collapsed ? "false" : "true"); }
  }

  function setup(card) {
    if (card.getAttribute("data-tc-collapse-bound") === "true") { return; }
    card.setAttribute("data-tc-collapse-bound", "true");

    var body = card.querySelector("[data-tc-collapse-body]");
    card.setAttribute("data-tc-collapse-mode", body ? "body" : "children");

    var toggle = findToggle(card);
    toggle.setAttribute("data-tc-collapse-head", "");

    /* A <div> or <h2> used as a control is not focusable and reports no role,
     * so it is given both. A real <button> or <summary> already has them. */
    var tag = toggle.tagName.toLowerCase();
    if (tag !== "button" && tag !== "summary") {
      if (!toggle.hasAttribute("tabindex")) { toggle.setAttribute("tabindex", "0"); }
      if (!toggle.hasAttribute("role")) { toggle.setAttribute("role", "button"); }
    }
    if (body) {
      if (!body.id) { body.id = "tc-collapse-body-" + Math.random().toString(36).slice(2, 9); }
      toggle.setAttribute("aria-controls", body.id);
    }

    if (!toggle.querySelector(".tc-collapse-marker")) {
      var marker = document.createElement("span");
      marker.className = "tc-collapse-marker";
      marker.setAttribute("aria-hidden", "true");
      marker.appendChild(document.createTextNode("▾"));
      toggle.insertBefore(marker, toggle.firstChild);
    }

    var id = idOf(card);
    var key = id ? KEY_PREFIX + pageKey() + "." + id : null;
    var stored = key ? storeGet(key) : null;
    var collapsed;
    if (stored === "collapsed") {
      collapsed = true;
    } else if (stored === "expanded") {
      collapsed = false;
    } else {
      collapsed = card.getAttribute("data-tc-collapse-default") === "collapsed";
    }
    apply(card, collapsed);

    function toggleNow() {
      var next = card.getAttribute("data-tc-collapsed") !== "true";
      apply(card, next);
      if (key) { storeSet(key, next ? "collapsed" : "expanded"); }
    }

    toggle.addEventListener("click", function (e) {
      if (tag === "summary") { e.preventDefault(); }
      toggleNow();
    });
    toggle.addEventListener("keydown", function (e) {
      var k = e.key;
      if (k === "Enter" || k === " " || k === "Spacebar" || e.keyCode === 13 || e.keyCode === 32) {
        if (tag === "button" || tag === "summary") { return; } /* native already does it */
        e.preventDefault();
        toggleNow();
      }
    });
  }

  function setAll(collapsed, root) {
    each((root || document).querySelectorAll("[data-tc-collapse]"), function (card) {
      apply(card, collapsed);
      var id = idOf(card);
      if (id) { storeSet(KEY_PREFIX + pageKey() + "." + id, collapsed ? "collapsed" : "expanded"); }
    });
  }

  function init(root) {
    root = root || document;
    var cards = root.querySelectorAll("[data-tc-collapse]");
    if (!cards.length) { return; }
    injectStyle();
    each(cards, setup);
  }

  window.TC = window.TC || {};
  window.TC.collapse = {
    init: init,
    collapseAll: function (root) { setAll(true, root); },
    expandAll: function (root) { setAll(false, root); }
  };

  ready(function () { init(document); });
})(window, document);
