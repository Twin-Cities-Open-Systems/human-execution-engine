/* arrange.js -- drag cards into a new order, order remembered.
 *
 * section: 3
 *
 * Operator brief, verbatim: "should also be able to move the cards around,
 * rearrange them at will too". Uses the browser's own HTML5 drag-and-drop
 * API -- no dependency, no bundler, nothing to serve but this file.
 *
 * MARKUP
 *   <div data-tc-arrange="dashboard">
 *     <section data-tc-arrange-item="hosts">
 *       <h2 data-tc-arrange-handle>Hosts</h2>
 *       ...
 *     </section>
 *     <section data-tc-arrange-item="alerts"> ... </section>
 *   </div>
 *
 * The container's data-tc-arrange value is the persistence key. Each item's
 * id is data-tc-arrange-item, falling back to the element's id. An item with
 * neither is still draggable, but the container's order is NOT persisted --
 * a position-derived name would silently reattach state to a different card
 * the first time the order changed, which is the one thing this file does.
 * That case is reported once to the console rather than passing in silence.
 *
 * data-tc-arrange-handle is optional. With a handle, dragging starts only
 * from the handle, so text inside a card stays selectable and its links stay
 * clickable. Without one, the whole item is the drag surface.
 *
 * KEYBOARD (drag-and-drop is mouse-only, so this is the real path, not a
 * courtesy): Tab to a handle, Space or Enter to pick the card up, Arrow keys
 * to move it, Space or Enter to drop, Escape to cancel and restore the
 * original position. Every step is announced through an aria-live region.
 *
 * Zero dependencies. No build step. Does nothing if no matching markup exists.
 */
(function (window, document) {
  "use strict";

  if (!document.querySelectorAll) { return; }

  var STYLE_ID = "tc-arrange-style";
  var LIVE_ID = "tc-arrange-live";
  var KEY_PREFIX = "tc.arrange.";
  var warned = false;

  var CSS = [
    "[data-tc-arrange-item]{position:relative}",
    "[data-tc-arrange-handle]{cursor:grab;user-select:none;-webkit-user-select:none}",
    "[data-tc-arrange-handle]:active{cursor:grabbing}",
    "[data-tc-arrange-handle]:focus-visible{outline:2px solid var(--accent,#2f6feb);outline-offset:2px}",
    "[data-tc-arrange-item][data-tc-dragging='true']{opacity:.45}",
    "[data-tc-arrange-item][data-tc-grabbed='true']{outline:2px dashed var(--accent,#2f6feb);",
    "outline-offset:3px}",
    "[data-tc-arrange-item][data-tc-dropbefore='true']{box-shadow:0 -3px 0 0 var(--accent,#2f6feb)}",
    "[data-tc-arrange-item][data-tc-dropafter='true']{box-shadow:0 3px 0 0 var(--accent,#2f6feb)}",
    "@media (prefers-reduced-motion:no-preference){",
    "[data-tc-arrange-item]{transition:opacity .12s ease,box-shadow .12s ease}}",
    ".tc-arrange-live{position:absolute;width:1px;height:1px;margin:-1px;padding:0;",
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

  function storeGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function storeSet(key, value) {
    try { window.localStorage.setItem(key, value); return true; } catch (e) { return false; }
  }

  function live(msg) {
    var el = document.getElementById(LIVE_ID);
    if (!el) {
      el = document.createElement("div");
      el.id = LIVE_ID;
      el.className = "tc-arrange-live";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    el.textContent = msg;
  }

  function items(container) {
    var out = [];
    each(container.children, function (c) {
      if (c.hasAttribute && c.hasAttribute("data-tc-arrange-item")) { out.push(c); }
    });
    return out;
  }

  function idOf(item) {
    return item.getAttribute("data-tc-arrange-item") || item.id || "";
  }

  function label(item) {
    var h = item.querySelector("[data-tc-arrange-handle]");
    var text = (h ? h.textContent : item.textContent) || "";
    text = text.replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "");
    return text.length > 60 ? text.slice(0, 60) + "…" : (text || idOf(item) || "card");
  }

  function persistable(container) {
    var list = items(container);
    if (!container.getAttribute("data-tc-arrange")) { return false; }
    for (var i = 0; i < list.length; i++) {
      if (!idOf(list[i])) {
        if (!warned && window.console && window.console.warn) {
          warned = true;
          window.console.warn(
            "arrange.js: an item in this container has no data-tc-arrange-item and no id, " +
            "so the order is not persisted. Give every item a stable id."
          );
        }
        return false;
      }
    }
    return true;
  }

  function save(container) {
    if (!persistable(container)) { return; }
    var order = [];
    each(items(container), function (i) { order.push(idOf(i)); });
    storeSet(KEY_PREFIX + (window.location.pathname || "/") + "." +
             container.getAttribute("data-tc-arrange"), JSON.stringify(order));
  }

  function restore(container) {
    if (!persistable(container)) { return; }
    var raw = storeGet(KEY_PREFIX + (window.location.pathname || "/") + "." +
                       container.getAttribute("data-tc-arrange"));
    if (!raw) { return; }
    var order;
    try { order = JSON.parse(raw); } catch (e) { return; }
    if (!order || typeof order.length !== "number") { return; }
    var byId = {};
    each(items(container), function (i) { byId[idOf(i)] = i; });
    /* Append in stored order; anything stored but since removed is skipped,
     * and anything new stays where the markup put it, after the known ones. */
    for (var i = 0; i < order.length; i++) {
      var el = byId[order[i]];
      if (el) { container.appendChild(el); }
    }
  }

  function clearDropHints(container) {
    each(items(container), function (i) {
      i.removeAttribute("data-tc-dropbefore");
      i.removeAttribute("data-tc-dropafter");
    });
  }

  function moveBy(container, item, delta) {
    var list = items(container);
    var at = -1;
    for (var i = 0; i < list.length; i++) { if (list[i] === item) { at = i; } }
    if (at < 0) { return false; }
    var to = at + delta;
    if (to < 0 || to >= list.length) { return false; }
    if (delta > 0) {
      container.insertBefore(item, list[to].nextSibling);
    } else {
      container.insertBefore(item, list[to]);
    }
    return true;
  }

  /* Put the item back at an absolute index. Computed against the list with
   * the item taken out, because inserting before the element now standing at
   * that index lands one slot short whenever the item was moved upward. */
  function moveTo(container, item, index) {
    var rest = [];
    each(items(container), function (i) { if (i !== item) { rest.push(i); } });
    if (index >= rest.length) {
      container.appendChild(item);
    } else {
      container.insertBefore(item, rest[index]);
    }
  }

  function setupItem(container, item) {
    if (item.getAttribute("data-tc-arrange-bound") === "true") { return; }
    item.setAttribute("data-tc-arrange-bound", "true");

    var handle = item.querySelector("[data-tc-arrange-handle]");
    var grip = handle || item;
    var moving = false;

    /* Whole-item drag is always armed. With a handle, draggable is armed only
     * while the pointer is down on the handle, so selecting text and clicking
     * links inside the card keep working. */
    if (!handle) {
      item.setAttribute("draggable", "true");
    } else {
      handle.addEventListener("mousedown", function () { item.setAttribute("draggable", "true"); });
      handle.addEventListener("touchstart", function () { item.setAttribute("draggable", "true"); }, { passive: true });
      document.addEventListener("mouseup", function () { item.setAttribute("draggable", "false"); });
    }

    if (!grip.hasAttribute("tabindex") && !/^(a|button|input|select|textarea)$/i.test(grip.tagName)) {
      grip.setAttribute("tabindex", "0");
    }
    if (!grip.hasAttribute("aria-label")) {
      grip.setAttribute("aria-label", "Reorder " + label(item) + ". Press Space to pick up.");
    }

    item.addEventListener("dragstart", function (e) {
      item.setAttribute("data-tc-dragging", "true");
      container.setAttribute("data-tc-arrange-active", "true");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        /* Firefox will not start a drag unless some data is set. */
        try { e.dataTransfer.setData("text/plain", idOf(item) || "card"); } catch (err) { /* IE guard */ }
      }
    });

    item.addEventListener("dragend", function () {
      item.removeAttribute("data-tc-dragging");
      item.setAttribute("draggable", handle ? "false" : "true");
      container.removeAttribute("data-tc-arrange-active");
      clearDropHints(container);
      save(container);
    });

    item.addEventListener("dragover", function (e) {
      var dragging = container.querySelector("[data-tc-dragging='true']");
      if (!dragging || dragging === item) { return; }
      e.preventDefault();
      if (e.dataTransfer) { e.dataTransfer.dropEffect = "move"; }
      var r = item.getBoundingClientRect();
      var after = (e.clientY - r.top) > r.height / 2;
      clearDropHints(container);
      item.setAttribute(after ? "data-tc-dropafter" : "data-tc-dropbefore", "true");
    });

    item.addEventListener("dragleave", function () {
      item.removeAttribute("data-tc-dropbefore");
      item.removeAttribute("data-tc-dropafter");
    });

    item.addEventListener("drop", function (e) {
      var dragging = container.querySelector("[data-tc-dragging='true']");
      if (!dragging || dragging === item) { return; }
      e.preventDefault();
      e.stopPropagation();
      var r = item.getBoundingClientRect();
      var after = (e.clientY - r.top) > r.height / 2;
      container.insertBefore(dragging, after ? item.nextSibling : item);
      clearDropHints(container);
      save(container);
      live(label(dragging) + " moved.");
    });

    grip.addEventListener("keydown", function (e) {
      var k = e.key;
      var grabbed = item.getAttribute("data-tc-grabbed") === "true";
      var isSpace = k === " " || k === "Spacebar" || e.keyCode === 32;
      var isEnter = k === "Enter" || e.keyCode === 13;
      var vertical = { ArrowUp: -1, ArrowDown: 1, Up: -1, Down: 1 };
      var horizontal = { ArrowLeft: -1, ArrowRight: 1, Left: -1, Right: 1 };

      if (isSpace || isEnter) {
        e.preventDefault();
        if (!grabbed) {
          item.setAttribute("data-tc-grabbed", "true");
          item.setAttribute("data-tc-arrange-home", String(indexOf(container, item)));
          live(label(item) + " picked up. Use the arrow keys to move it, Space to drop, Escape to cancel.");
        } else {
          item.removeAttribute("data-tc-grabbed");
          item.removeAttribute("data-tc-arrange-home");
          save(container);
          live(label(item) + " dropped at position " + (indexOf(container, item) + 1) +
               " of " + items(container).length + ".");
        }
        return;
      }

      if (k === "Escape" || e.keyCode === 27) {
        if (!grabbed) { return; }
        e.preventDefault();
        moving = true;
        var home = parseInt(item.getAttribute("data-tc-arrange-home"), 10);
        if (home >= 0) { moveTo(container, item, home); }
        item.removeAttribute("data-tc-grabbed");
        item.removeAttribute("data-tc-arrange-home");
        grip.focus();
        moving = false;
        live("Move cancelled. " + label(item) + " is back where it was.");
        return;
      }

      if (!grabbed) { return; }
      var delta = vertical[k];
      if (delta === undefined) { delta = horizontal[k]; }
      if (delta === undefined) { return; }
      e.preventDefault();
      /* insertBefore detaches and re-inserts the node, which blurs it. Without
       * this guard the blur handler would drop the card after a single arrow
       * press and the keyboard path would be unusable past one step. */
      moving = true;
      if (moveBy(container, item, delta)) {
        live(label(item) + " now at position " + (indexOf(container, item) + 1) +
             " of " + items(container).length + ".");
      } else {
        live(label(item) + " is already at the " + (delta < 0 ? "start" : "end") + ".");
      }
      grip.focus();
      moving = false;
    });

    grip.addEventListener("blur", function () {
      if (moving) { return; }
      if (item.getAttribute("data-tc-grabbed") === "true") {
        item.removeAttribute("data-tc-grabbed");
        item.removeAttribute("data-tc-arrange-home");
        save(container);
      }
    });
  }

  function indexOf(container, item) {
    var list = items(container);
    for (var i = 0; i < list.length; i++) { if (list[i] === item) { return i; } }
    return -1;
  }

  function setupContainer(container) {
    if (container.getAttribute("data-tc-arrange-bound") === "true") { return; }
    container.setAttribute("data-tc-arrange-bound", "true");
    restore(container);
    each(items(container), function (item) { setupItem(container, item); });
    /* Dropping onto container padding rather than onto a card lands the item
     * at the end -- without this the drop is rejected and the card snaps back. */
    container.addEventListener("dragover", function (e) {
      if (container.querySelector("[data-tc-dragging='true']")) { e.preventDefault(); }
    });
    container.addEventListener("drop", function (e) {
      var dragging = container.querySelector("[data-tc-dragging='true']");
      if (!dragging) { return; }
      e.preventDefault();
      if (e.target === container) {
        container.appendChild(dragging);
        save(container);
      }
      clearDropHints(container);
    });
  }

  function reset(key) {
    each(document.querySelectorAll("[data-tc-arrange]"), function (c) {
      if (key && c.getAttribute("data-tc-arrange") !== key) { return; }
      try {
        window.localStorage.removeItem(
          KEY_PREFIX + (window.location.pathname || "/") + "." + c.getAttribute("data-tc-arrange")
        );
      } catch (e) { /* storage unavailable: nothing was saved to clear */ }
    });
  }

  function init(root) {
    root = root || document;
    var containers = root.querySelectorAll("[data-tc-arrange]");
    if (!containers.length) { return; }
    injectStyle();
    each(containers, setupContainer);
  }

  window.TC = window.TC || {};
  window.TC.arrange = { init: init, reset: reset };

  ready(function () { init(document); });
})(window, document);
