/* table.js -- click-to-sort any column, and a live text filter across every
 * field of every row.
 *
 * section: 3
 *
 * Operator brief, verbatim: "should be able to sort every table and have text
 * search for all the fields. actual text box search with dynamic response to
 * what is typed in the box. not a pulldown, actuaul elstastc-style search."
 *
 * So: a real <input type="search">, filtering on every keystroke, matching
 * across all columns at once. Space-separated words are ANDed, each matched as
 * a substring anywhere in the row -- typing "pve down" finds the rows that
 * mention both, in any column, in any order. Entirely client-side over rows
 * the page has already rendered; nothing is fetched and no row is re-created.
 *
 * MARKUP
 *   <input type="search" data-tc-table-filter="#hosts">
 *   <span data-tc-table-count="#hosts"></span>
 *   <table id="hosts" data-tc-table>
 *     <thead><tr><th>Host</th><th data-tc-sort="number">Uptime</th></tr></thead>
 *     <tbody> ... </tbody>
 *   </table>
 *
 * Column options on a <th>:
 *   data-tc-sort="text|number|date"  force a comparison type (else detected)
 *   data-tc-nosort                   this column is not sortable
 * Cell option on a <td>:
 *   data-tc-sort-value="..."         sort and filter on this instead of the
 *                                    cell's text -- the way to sort "3 days
 *                                    ago" or a status icon correctly
 *
 * Every table.tc-table is bound as if it carried data-tc-table. A table
 * styled as the org's table is a sortable table, so no page can ship one that
 * forgets the attribute. Operator, 2026-09-11: "make sure all columns are
 * sortable, the scorecard is not". agents-live's scorecard had the class and
 * not the attribute, and showed no sort control at all.
 *
 * LIVE PAGES
 *   A page that re-renders rows on a poll keeps the viewer's sort and search.
 *   Rows added to or replaced in a bound table are re-sorted by the active
 *   column and re-filtered by the bound search box, with nothing for the page
 *   to call. Before this, agents-live re-rendered every 15 s and tickets
 *   every 60 s, and each render undid the viewer's sort while the header
 *   still showed it. TC.table.refresh(tableOrSelector) does the same on
 *   demand, for a page that changes cell text in place.
 *
 * The filter input's value is a selector for the table. Left empty, it binds
 * to the first bound table inside the input's own parent element.
 *
 * Zero dependencies. No build step. Does nothing if no matching markup exists.
 */
(function (window, document) {
  "use strict";

  /* What gets bound: the explicit attribute, or the org's table class. */
  var TABLE_SEL = "[data-tc-table], table.tc-table";

  if (!document.querySelectorAll) { return; }

  var STYLE_ID = "tc-table-style";

  var CSS = [
    "[data-tc-table] th[data-tc-sortable]{cursor:pointer;user-select:none;",
    "-webkit-user-select:none;white-space:nowrap}",
    "[data-tc-table] th[data-tc-sortable]:focus-visible{outline:2px solid var(--accent,#2f6feb);",
    "outline-offset:-2px}",
    "[data-tc-table] th .tc-sort-marker{margin-left:.4em;font-size:.85em;",
    "opacity:.35;color:var(--ink-faint,#6b7280)}",
    "[data-tc-table] th[aria-sort='ascending'] .tc-sort-marker,",
    "[data-tc-table] th[aria-sort='descending'] .tc-sort-marker{opacity:1;",
    "color:var(--accent,#2f6feb)}",
    "[data-tc-table] tr[data-tc-filtered='true']{display:none}",
    ".tc-table-empty td{padding:.75em;font-style:italic;color:var(--ink-faint,#6b7280)}"
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

  function bodyOf(table) {
    return table.tBodies && table.tBodies.length ? table.tBodies[0] : null;
  }

  function rowsOf(table) {
    var tb = bodyOf(table);
    if (!tb) { return []; }
    var out = [];
    each(tb.rows, function (r) { if (!r.hasAttribute("data-tc-table-note")) { out.push(r); } });
    return out;
  }

  /* Text a sighted reader actually sees. Skips aria-hidden decoration and
   * .tc-sr-only text -- without this, links.js's screen-reader hint
   * "(opens in a new tab)" is in every row that has an external link, and
   * typing "tab" into the search box matches all of them. */
  function visibleText(node) {
    if (node.nodeType === 3) { return node.nodeValue || ""; }
    if (node.nodeType !== 1) { return ""; }
    if (node.getAttribute("aria-hidden") === "true") { return ""; }
    if ((" " + (node.getAttribute("class") || "") + " ").indexOf(" tc-sr-only ") > -1) { return ""; }
    var out = "";
    for (var i = 0; i < node.childNodes.length; i++) { out += visibleText(node.childNodes[i]); }
    return out;
  }

  function cellText(cell) {
    var v = cell.getAttribute("data-tc-sort-value");
    return v !== null ? v : visibleText(cell);
  }

  function cellValue(row, index) {
    var cell = row.cells[index];
    return cell ? cellText(cell) : "";
  }

  function norm(s) {
    return String(s).replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "");
  }

  var NUM_RE = /^-?[$€£]?\s*-?\d[\d,_ ]*(?:\.\d+)?\s*%?$/;

  function toNumber(s) {
    var t = norm(s).replace(/[$€£,%_\s]/g, "");
    var n = parseFloat(t);
    return isNaN(n) ? null : n;
  }

  /* Detect the comparison type from the column's own values rather than making
   * the author declare it. A column is numeric only if every non-empty cell in
   * it parses as a number -- one stray "n/a" and it sorts as text, which is the
   * safe direction to be wrong in. */
  function detectType(table, index) {
    var rows = rowsOf(table);
    var seen = 0, nums = 0, dates = 0;
    for (var i = 0; i < rows.length && i < 200; i++) {
      var raw = norm(cellValue(rows[i], index));
      if (!raw) { continue; }
      seen++;
      if (NUM_RE.test(raw) && toNumber(raw) !== null) { nums++; }
      if (/^\d{4}-\d{2}-\d{2}/.test(raw) && !isNaN(Date.parse(raw))) { dates++; }
    }
    if (!seen) { return "text"; }
    if (dates === seen) { return "date"; }
    if (nums === seen) { return "number"; }
    return "text";
  }

  function comparator(type, index, dir) {
    return function (a, b) {
      var av = cellValue(a.row, index);
      var bv = cellValue(b.row, index);
      var r;
      if (type === "number") {
        var an = toNumber(av), bn = toNumber(bv);
        /* Empty and unparseable cells sort to the bottom in both directions
         * rather than pretending to be zero. */
        if (an === null && bn === null) { r = 0; }
        else if (an === null) { return 1; }
        else if (bn === null) { return -1; }
        else { r = an - bn; }
      } else if (type === "date") {
        var ad = Date.parse(norm(av)), bd = Date.parse(norm(bv));
        if (isNaN(ad) && isNaN(bd)) { r = 0; }
        else if (isNaN(ad)) { return 1; }
        else if (isNaN(bd)) { return -1; }
        else { r = ad - bd; }
      } else {
        r = norm(av).toLowerCase().localeCompare(norm(bv).toLowerCase());
      }
      if (r !== 0) { return dir === "descending" ? -r : r; }
      /* Array.prototype.sort is only guaranteed stable from ES2019, and this
       * has to hold on whatever browser a kiosk is running -- so the original
       * row index is the tiebreaker, explicitly. */
      return a.at - b.at;
    };
  }

  function sortBy(table, index, dir) {
    var tb = bodyOf(table);
    if (!tb) { return; }
    var th = headerCells(table)[index];
    var type = (th && th.getAttribute("data-tc-sort")) || detectType(table, index);

    var decorated = [];
    each(rowsOf(table), function (row, at) { decorated.push({ row: row, at: at }); });
    decorated.sort(comparator(type, index, dir));

    var frag = document.createDocumentFragment();
    for (var i = 0; i < decorated.length; i++) { frag.appendChild(decorated[i].row); }
    tb.appendChild(frag);
    /* Re-append the "no rows match" note so a sort run under an active filter
     * does not leave it stranded above the rows. */
    var note = tb.querySelector("tr[data-tc-table-note]");
    if (note) { tb.appendChild(note); }

    each(headerCells(table), function (cell, i) {
      if (!cell.hasAttribute("data-tc-sortable")) { return; }
      cell.setAttribute("aria-sort", i === index ? dir : "none");
      var m = cell.querySelector(".tc-sort-marker");
      if (m) { m.textContent = i === index ? (dir === "ascending" ? "▲" : "▼") : "↕"; }
    });
  }

  function headerCells(table) {
    var head = table.tHead;
    if (!head || !head.rows.length) { return []; }
    var row = head.rows[head.rows.length - 1];
    var out = [];
    each(row.cells, function (c) { out.push(c); });
    return out;
  }

  /* Cached on a JS property, not a data- attribute: an attribute holding each
   * row's full text would duplicate the entire table into the DOM. Call
   * TC.table.refresh(table) if a row's cells change after load. */
  function rowHaystack(row) {
    if (typeof row.tcHaystack === "string") { return row.tcHaystack; }
    var parts = [];
    each(row.cells, function (c) { parts.push(cellText(c)); });
    row.tcHaystack = norm(parts.join(" ")).toLowerCase();
    return row.tcHaystack;
  }

  function resolve(t) {
    return typeof t === "string" ? document.querySelector(t) : t;
  }

  /* Discard the mutation records this library just produced, so the row
   * observer never answers its own re-sort. */
  function quiet(table) {
    if (table.tcObserver) { table.tcObserver.takeRecords(); }
  }

  /* Put the viewer's view back after rows changed underneath it: clear the
   * cached row text, re-sort by the active column, re-run each bound search
   * box. Takes a table or a selector. Returns the table, or null when nothing
   * matches -- it never throws, because pages call it from a render loop.
   * Before 2026-09-11 it only cleared the cache and took only an element, and
   * agents-live passed it a selector string, so it did nothing at all there. */
  function refresh(t) {
    var table = resolve(t);
    if (!table || !table.tBodies) { return null; }
    if (table.getAttribute("data-tc-table-bound") !== "true") { setupTable(table); }
    each(rowsOf(table), function (row) { row.tcHaystack = null; });
    each(headerCells(table), function (cell, i) {
      var dir = cell.getAttribute("aria-sort");
      if (cell.hasAttribute("data-tc-sortable") && (dir === "ascending" || dir === "descending")) {
        sortBy(table, i, dir);
      }
    });
    var inputs = table.tcFilters || [];
    if (inputs.length) {
      each(inputs, function (input) { filter(table, input.value); });
    } else {
      announce(table, rowsOf(table).length, rowsOf(table).length);
    }
    quiet(table);
    return table;
  }

  /* Only row-level changes count: a <tbody> gaining or losing rows, or the
   * table gaining or losing a <tbody>. Cell-level churn, such as a hovercard
   * adding a span, is ignored. */
  function watch(table) {
    if (table.tcObserver || typeof window.MutationObserver !== "function") { return; }
    var obs = new window.MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var tag = records[i].target && records[i].target.nodeName;
        if (tag === "TBODY" || tag === "TABLE") { refresh(table); return; }
      }
    });
    obs.observe(table, { childList: true, subtree: true });
    table.tcObserver = obs;
  }

  function filter(table, query) {
    var terms = norm(query).toLowerCase().split(" ");
    var real = [];
    for (var i = 0; i < terms.length; i++) { if (terms[i]) { real.push(terms[i]); } }

    var rows = rowsOf(table);
    var shown = 0;
    each(rows, function (row) {
      var hay = rowHaystack(row);
      var ok = true;
      for (var t = 0; t < real.length; t++) {
        if (hay.indexOf(real[t]) === -1) { ok = false; break; }
      }
      if (ok) { row.removeAttribute("data-tc-filtered"); shown++; }
      else { row.setAttribute("data-tc-filtered", "true"); }
    });

    emptyNote(table, shown === 0 && rows.length > 0, real.length);
    announce(table, shown, rows.length);
    return { shown: shown, total: rows.length };
  }

  function emptyNote(table, show, hasQuery) {
    var tb = bodyOf(table);
    if (!tb) { return; }
    var note = tb.querySelector("tr[data-tc-table-note]");
    if (!show) { if (note) { note.parentNode.removeChild(note); } return; }
    if (note) { return; }
    note = document.createElement("tr");
    note.setAttribute("data-tc-table-note", "");
    note.className = "tc-table-empty";
    var td = document.createElement("td");
    td.colSpan = Math.max(1, headerCells(table).length);
    td.appendChild(document.createTextNode(hasQuery ? "No rows match that search." : "No rows."));
    note.appendChild(td);
    tb.appendChild(note);
  }

  function announce(table, shown, total) {
    each(document.querySelectorAll("[data-tc-table-count]"), function (el) {
      var sel = el.getAttribute("data-tc-table-count");
      /* With a selector, the count belongs to whatever it names. Without one,
       * it belongs to the table in its own parent -- the same fallback the
       * filter input uses, so the two agree on a page with several tables. */
      var wants = sel
        ? document.querySelector(sel)
        : (el.parentNode && el.parentNode.querySelector ? el.parentNode.querySelector(TABLE_SEL) : null);
      if (wants !== table) { return; }
      el.textContent = shown === total
        ? total + (total === 1 ? " row" : " rows")
        : shown + " of " + total + " rows";
    });
    var lr = table.getAttribute("data-tc-live-region");
    if (lr) {
      var region = document.getElementById(lr);
      if (region) { region.textContent = shown + " of " + total + " rows match."; }
    }
  }

  function setupTable(table) {
    if (table.getAttribute("data-tc-table-bound") === "true") { return; }
    table.setAttribute("data-tc-table-bound", "true");
    /* A class-bound table takes the attribute too, so the injected CSS and
     * every [data-tc-table] lookup treat it the same as a marked one. */
    if (!table.hasAttribute("data-tc-table")) { table.setAttribute("data-tc-table", ""); }

    each(headerCells(table), function (cell, index) {
      if (cell.hasAttribute("data-tc-nosort")) { return; }
      cell.setAttribute("data-tc-sortable", "");
      cell.setAttribute("aria-sort", "none");
      /* A <th> is not focusable and announces no control, so it is given both
       * -- a sort you can only reach with a mouse is not a sort everyone has. */
      if (!cell.hasAttribute("tabindex")) { cell.setAttribute("tabindex", "0"); }
      if (!cell.hasAttribute("role")) { cell.setAttribute("role", "columnheader"); }
      if (!cell.querySelector(".tc-sort-marker")) {
        var m = document.createElement("span");
        m.className = "tc-sort-marker";
        m.setAttribute("aria-hidden", "true");
        m.appendChild(document.createTextNode("↕"));
        cell.appendChild(m);
      }

      function activate() {
        var dir = cell.getAttribute("aria-sort") === "ascending" ? "descending" : "ascending";
        sortBy(table, index, dir);
        quiet(table);
      }
      cell.addEventListener("click", activate);
      cell.addEventListener("keydown", function (e) {
        var k = e.key;
        if (k === "Enter" || k === " " || k === "Spacebar" || e.keyCode === 13 || e.keyCode === 32) {
          e.preventDefault();
          activate();
        }
      });
    });

    announce(table, rowsOf(table).length, rowsOf(table).length);
    watch(table);
  }

  function setupFilter(input) {
    if (input.getAttribute("data-tc-table-bound") === "true") { return; }
    input.setAttribute("data-tc-table-bound", "true");

    var sel = input.getAttribute("data-tc-table-filter");
    var table = sel ? document.querySelector(sel)
                    : (input.parentNode && input.parentNode.querySelector(TABLE_SEL));
    if (!table) { return; }
    (table.tcFilters = table.tcFilters || []).push(input);

    if (!input.hasAttribute("aria-label") && !input.hasAttribute("aria-labelledby")) {
      input.setAttribute("aria-label", "Search this table");
    }
    if (!input.hasAttribute("autocomplete")) { input.setAttribute("autocomplete", "off"); }

    function run() { filter(table, input.value); quiet(table); }

    /* "input" fires for typing, pasting, clearing, autofill and the search
     * field's own clear button -- one listener covers every path a value can
     * change by. No debounce: the work is a substring scan over rows already
     * in the DOM, and a delay is what makes a search box feel dead. */
    input.addEventListener("input", run);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.keyCode === 27) {
        input.value = "";
        run();
      }
    });
    if (input.value) { run(); }
  }

  function init(root) {
    root = root || document;
    var tables = root.querySelectorAll(TABLE_SEL);
    var inputs = root.querySelectorAll("[data-tc-table-filter]");
    if (!tables.length && !inputs.length) { return; }
    injectStyle();
    each(tables, setupTable);
    each(inputs, setupFilter);
  }

  window.TC = window.TC || {};
  window.TC.table = {
    init: init,
    refresh: refresh,
    sort: function (t, index, dir) {
      var table = resolve(t);
      if (!table) { return null; }
      sortBy(table, index, dir);
      quiet(table);
      return table;
    },
    filter: function (t, query) {
      var table = resolve(t);
      if (!table) { return null; }
      var r = filter(table, query);
      quiet(table);
      return r;
    }
  };

  ready(function () { init(document); });
})(window, document);
