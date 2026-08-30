// tc-grid: generic, reusable Card-grid dashboard engine (JS half).
// Renders an array of real `kind: Card` objects (the ones carrying an
// additive spec.ui block -- see human-execution-engine's
// tooling/bin/cards-to-ui-json.py) into a CSS-grid of .tc-card tiles,
// with drag-to-reorder and corner-handle resize on desktop.
//
// Real, deliberate rule: below 640px, NO drag/resize listener is ever
// attached, full stop -- mobile always gets a fixed, non-draggable
// single-column stack in source order. Card *position* (order/size)
// is never stored on the Card object itself -- only here, in this
// grid's own layout store -- so routine rearranging never touches or
// re-versions governed content.
//
// Usage:
//   TCGrid.init("#dashboard", cards, { pageId: "view-lab-ops", cols: 4 });
(function (global) {
  "use strict";

  var MOBILE_QUERY = "(max-width: 640px)";

  function isMobile() {
    return global.matchMedia && global.matchMedia(MOBILE_QUERY).matches;
  }

  function layoutKey(pageId) {
    return "tcos-layout:" + pageId;
  }

  function loadLayout(pageId) {
    try {
      var raw = localStorage.getItem(layoutKey(pageId));
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function saveLayout(pageId, layout) {
    try {
      localStorage.setItem(layoutKey(pageId), JSON.stringify(layout));
    } catch (e) {
      /* storage unavailable -- degrade to session-only, no throw */
    }
  }

  function cardName(card) {
    return (card.metadata && card.metadata.name) || card.name;
  }

  function cardUi(card) {
    return (card.spec && card.spec.ui) || card.ui || {};
  }

  function renderCard(card, savedLayout) {
    var ui = cardUi(card);
    var name = cardName(card);
    var layout = ui.layout || {};
    var w = (savedLayout[name] && savedLayout[name].w) || layout.w || 1;
    var h = (savedLayout[name] && savedLayout[name].h) || layout.h || 1;

    var el = document.createElement("div");
    el.className = "tc-card";
    el.dataset.name = name;
    el.dataset.minW = layout.minW || 1;
    el.dataset.minH = layout.minH || 1;
    el.style.setProperty("--w", w);
    el.style.setProperty("--h", h);

    var head = document.createElement("div");
    head.className = "tc-card-head";
    var dot = document.createElement("span");
    dot.className = "tc-card-dot " + (ui.status || "good");
    var title = document.createElement("span");
    title.className = "tc-card-title";
    title.textContent = ui.title || name;
    head.appendChild(dot);
    head.appendChild(title);
    el.appendChild(head);

    if (ui.body) {
      var body = document.createElement("div");
      body.className = "tc-card-body";
      body.textContent = ui.body;
      el.appendChild(body);
    }

    if (ui.links && ui.links.length) {
      var linksEl = document.createElement("div");
      linksEl.className = "tc-card-links";
      ui.links.forEach(function (l) {
        var a = document.createElement("a");
        a.href = l.href;
        a.textContent = l.label;
        a.target = "_blank";
        a.rel = "noopener";
        linksEl.appendChild(a);
      });
      el.appendChild(linksEl);
    }

    return el;
  }

  function currentOrder(host) {
    return Array.prototype.map.call(host.querySelectorAll(".tc-card"), function (el) {
      return el.dataset.name;
    });
  }

  function persist(host, pageId) {
    var layout = {};
    Array.prototype.forEach.call(host.querySelectorAll(".tc-card"), function (el, i) {
      layout[el.dataset.name] = {
        order: i,
        w: parseInt(getComputedStyle(el).getPropertyValue("--w"), 10) || 1,
        h: parseInt(getComputedStyle(el).getPropertyValue("--h"), 10) || 1,
      };
    });
    saveLayout(pageId, layout);
    host.dispatchEvent(new CustomEvent("tcgrid:layoutchange", { detail: layout, bubbles: true }));
  }

  function attachDrag(host, pageId) {
    var dragged = null;

    host.addEventListener("dragstart", function (e) {
      var card = e.target.closest(".tc-card");
      if (!card) return;
      dragged = card;
      card.classList.add("tc-dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    host.addEventListener("dragend", function () {
      if (dragged) dragged.classList.remove("tc-dragging");
      Array.prototype.forEach.call(host.querySelectorAll(".tc-drop-target"), function (el) {
        el.classList.remove("tc-drop-target");
      });
      dragged = null;
    });

    host.addEventListener("dragover", function (e) {
      var card = e.target.closest(".tc-card");
      if (!card || card === dragged) return;
      e.preventDefault();
      card.classList.add("tc-drop-target");
    });

    host.addEventListener("dragleave", function (e) {
      var card = e.target.closest(".tc-card");
      if (card) card.classList.remove("tc-drop-target");
    });

    host.addEventListener("drop", function (e) {
      var target = e.target.closest(".tc-card");
      if (!target || !dragged || target === dragged) return;
      e.preventDefault();
      target.classList.remove("tc-drop-target");
      var before = Array.prototype.indexOf.call(host.children, target) >
                   Array.prototype.indexOf.call(host.children, dragged);
      host.insertBefore(dragged, before ? target.nextSibling : target);
      persist(host, pageId);
    });

    Array.prototype.forEach.call(host.querySelectorAll(".tc-card"), function (el) {
      el.setAttribute("draggable", "true");
    });
  }

  function attachResize(host, pageId) {
    Array.prototype.forEach.call(host.querySelectorAll(".tc-card"), function (card) {
      var handle = document.createElement("div");
      handle.className = "tc-resize-handle";
      card.appendChild(handle);

      var startX, startY, startW, startH;

      function onMove(e) {
        var cell = card.parentElement.getBoundingClientRect().width / (getComputedStyle(host).getPropertyValue("--tc-cols") || 4);
        var dw = Math.round((e.clientX - startX) / cell);
        var dh = Math.round((e.clientY - startY) / 90); // ~row height
        var minW = parseInt(card.dataset.minW, 10) || 1;
        var minH = parseInt(card.dataset.minH, 10) || 1;
        var w = Math.max(minW, startW + dw);
        var h = Math.max(minH, startH + dh);
        card.style.setProperty("--w", w);
        card.style.setProperty("--h", h);
      }

      function onUp() {
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        persist(host, pageId);
      }

      handle.addEventListener("pointerdown", function (e) {
        e.preventDefault();
        startX = e.clientX;
        startY = e.clientY;
        startW = parseInt(getComputedStyle(card).getPropertyValue("--w"), 10) || 1;
        startH = parseInt(getComputedStyle(card).getPropertyValue("--h"), 10) || 1;
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
      });
    });
  }

  function init(selector, cards, opts) {
    opts = opts || {};
    var pageId = opts.pageId || location.pathname;
    var host = typeof selector === "string" ? document.querySelector(selector) : selector;
    if (!host) return;

    host.classList.add("tc-grid");
    host.style.setProperty("--tc-cols", opts.cols || 4);

    var savedLayout = loadLayout(pageId);
    var ordered = cards.slice().sort(function (a, b) {
      var oa = (savedLayout[cardName(a)] && savedLayout[cardName(a)].order);
      var ob = (savedLayout[cardName(b)] && savedLayout[cardName(b)].order);
      if (oa == null && ob == null) return 0;
      if (oa == null) return 1;
      if (ob == null) return -1;
      return oa - ob;
    });

    host.innerHTML = "";
    ordered.forEach(function (card) {
      host.appendChild(renderCard(card, savedLayout));
    });

    if (!isMobile()) {
      attachDrag(host, pageId);
      attachResize(host, pageId);
    }
    // Deliberately no resize-observer re-check: a card grid that was
    // interactive at load stays interactive until reload, and one that
    // loaded on mobile never becomes draggable mid-session either --
    // simpler and more predictable than re-wiring on viewport change.
  }

  global.TCGrid = { init: init };
})(window);
