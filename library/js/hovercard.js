/* hovercard.js -- GitHub-style hover preview for any [data-tc-profile] link.
 *
 * section: 3
 *
 * Promotion of ~/git/tcos-www/shell/tc-hovercard.js, which was itself ported
 * verbatim from view.lab.tcos.us/contracts.html (2026-08-28). That file's own
 * header names this generalization as the plan: view.lab.tcos.us/plan.html
 * describes "tc-hovercard.js: GitHub-style hover preview for any
 * data-tc-profile link". The original was hardcoded to .contract-item; this is
 * the same component with the hardcoding removed. Kept from the original: the
 * per-URL cache, the hover AND focus triggers, the first-N-lines preview.
 *
 * MARKUP
 *   <a href="..." data-tc-profile="https://raw.example/file.yaml">name</a>
 *
 * Optional attributes on the trigger:
 *   data-tc-profile-lines="14"     lines of a text preview to show
 *   data-tc-profile-target="#sel"  render into this element instead of the
 *                                  floating panel (the host page owns show/hide)
 *   data-tc-profile-title="text"   heading above the preview
 *
 * A GitHub issue or pull-request URL in data-tc-profile is recognized and
 * rendered as a real issue card (state, title, author) instead of raw text.
 *
 * LEGACY SHAPE, still supported so this file is a drop-in replacement for
 * shell/tc-hovercard.js on contracts.html:
 *   <div class="contract-item">
 *     <a class="contract-link" href="...">name</a>
 *     <div class="file-preview" data-raw="https://raw.../file.yaml">...</div>
 *   </div>
 * There the host page's own CSS does the showing and hiding; this script only
 * fills the .file-preview in place.
 *
 * Zero dependencies. No build step. Does nothing if no matching markup exists.
 */
(function (window, document) {
  "use strict";

  if (!document.querySelectorAll || !window.fetch) { return; }

  var STYLE_ID = "tc-hovercard-style";
  var PANEL_ID = "tc-hovercard";
  var SHOW_DELAY = 120;
  var HIDE_DELAY = 160;
  var DEFAULT_LINES = 14;

  var CSS = [
    ":root{",
    "--tc-hc-bg:var(--surface,#ffffff);--tc-hc-fg:var(--ink,#16181d);",
    "--tc-hc-dim:var(--ink-dim,#4a5061);--tc-hc-faint:var(--ink-faint,#6b7280);",
    "--tc-hc-line:var(--line,#d8dbe2);--tc-hc-accent:var(--accent,#2f6feb)}",
    "@media (prefers-color-scheme:dark){:root{",
    "--tc-hc-bg:var(--surface,#16181d);--tc-hc-fg:var(--ink,#e8eaf0);",
    "--tc-hc-dim:var(--ink-dim,#b6bcc9);--tc-hc-faint:var(--ink-faint,#8b93a3);",
    "--tc-hc-line:var(--line,#2c313c);--tc-hc-accent:var(--accent,#6aa1ff)}}",
    ".tc-hovercard{position:fixed;top:0;left:0;z-index:2147483000;",
    "min-width:280px;max-width:520px;padding:10px 12px;border-radius:8px;",
    "background:var(--tc-hc-bg);color:var(--tc-hc-fg);",
    "border:1px solid var(--tc-hc-line);box-shadow:0 8px 24px rgba(0,0,0,.28);",
    "font:12px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;",
    "opacity:0;visibility:hidden;pointer-events:none}",
    ".tc-hovercard[data-tc-open='true']{opacity:1;visibility:visible;pointer-events:auto}",
    "@media (prefers-reduced-motion:no-preference){",
    ".tc-hovercard{transition:opacity .12s ease}}",
    ".tc-hc-pre{margin:0;max-height:15em;overflow:auto;",
    "font-family:ui-monospace,'JetBrains Mono',Menlo,Consolas,monospace;",
    "font-size:11px;line-height:1.5;color:var(--tc-hc-dim);",
    "white-space:pre-wrap;word-break:break-word}",
    ".tc-hc-status{font-size:11px;color:var(--tc-hc-faint);font-style:italic}",
    ".tc-hc-title{display:block;margin:0 0 4px;font-size:12px;font-weight:600;",
    "color:var(--tc-hc-fg)}",
    ".tc-hc-meta{display:block;margin-top:6px;font-size:11px;color:var(--tc-hc-faint)}",
    ".tc-hc-state{display:inline-block;margin-right:6px;padding:1px 7px;",
    "border-radius:999px;border:1px solid var(--tc-hc-line);font-size:11px;",
    "font-weight:600;color:var(--tc-hc-dim)}"
  ].join("");

  /* url -> HTML string. Every value in here was escaped by this file. */
  var cache = {};
  var inflight = {};
  var panel = null;
  var openFor = null;
  var showTimer = null;
  var hideTimer = null;

  function each(list, fn) {
    if (!list) { return; }
    for (var i = 0; i < list.length; i++) { fn(list[i], i); }
  }

  function ready(fn) {
    /* readyState guard, not a bare DOMContentLoaded listener: a deferred or
     * dynamically appended script can load after that event has already
     * fired, and the original silently did nothing in that case. */
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

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function statusHtml(text) {
    return '<span class="tc-hc-status">' + esc(text) + "</span>";
  }

  /* ---- GitHub issue / pull-request rendering ------------------------- */

  var GH_RE = /^https?:\/\/(?:www\.)?github\.com\/([^/]+)\/([^/]+)\/(issues|pull)\/(\d+)/;

  function githubApiUrl(url) {
    var m = GH_RE.exec(url);
    if (!m) { return null; }
    /* /issues/N serves pull requests too -- one endpoint for both. */
    return "https://api.github.com/repos/" + m[1] + "/" + m[2] + "/issues/" + m[4];
  }

  /* Icon AND label, never color alone -- shape-distinct glyphs so the state
   * survives a monochrome terminal screenshot or a color-blind reader. */
  function githubState(data) {
    var pr = data.pull_request;
    if (pr && pr.merged_at) { return { icon: "◆", label: "merged" }; }
    if (data.state === "closed") {
      if (data.state_reason === "not_planned") {
        return { icon: "✖", label: "closed (not planned)" };
      }
      return { icon: "✖", label: "closed" };
    }
    if (pr && data.draft) { return { icon: "○", label: "draft" }; }
    return { icon: "●", label: "open" };
  }

  function renderGithub(data) {
    var st = githubState(data);
    var kind = data.pull_request ? "PR" : "issue";
    var who = data.user && data.user.login ? data.user.login : "unknown";
    var html = '<span class="tc-hc-title">' + esc(data.title || "(no title)") + "</span>";
    html += '<span class="tc-hc-state">' + esc(st.icon + " " + st.label) + "</span>";
    html += '<span class="tc-hc-status">' + esc(kind + " #" + data.number + " by " + who) + "</span>";
    if (data.body) {
      var body = String(data.body).split("\n").slice(0, 6).join("\n");
      html += '<pre class="tc-hc-pre">' + esc(body) + "</pre>";
    }
    var comments = typeof data.comments === "number" ? data.comments : 0;
    html += '<span class="tc-hc-meta">' + esc(comments + (comments === 1 ? " comment" : " comments")) + "</span>";
    return html;
  }

  function renderText(text, lines, title) {
    var head = String(text).split("\n").slice(0, lines).join("\n");
    var html = title ? '<span class="tc-hc-title">' + esc(title) + "</span>" : "";
    return html + '<pre class="tc-hc-pre">' + esc(head) + "\n…</pre>";
  }

  /* ---- fetching ------------------------------------------------------ */

  function load(url, lines, title) {
    /* Keyed by URL AND by the options that change the render, not by URL
     * alone. Two triggers can point at one file and ask for different line
     * counts or a different heading; a URL-only key hands the second one
     * whatever the first one rendered. Caught by the test page, which has
     * exactly that pair. */
    var key = url + "\n" + lines + "\n" + (title || "");
    if (cache[key]) { return Promise.resolve(cache[key]); }
    if (inflight[key]) { return inflight[key]; }

    var api = githubApiUrl(url);
    var target = api || url;

    var p = window.fetch(target, api ? { headers: { Accept: "application/vnd.github+json" } } : undefined)
      .then(function (r) {
        if (r.ok) { return api ? r.json() : r.text(); }
        if (api && r.status === 403 && r.headers.get("X-RateLimit-Remaining") === "0") {
          throw new Error("GitHub API rate limit reached (unauthenticated: 60/hr) -- try again later");
        }
        throw new Error("HTTP " + r.status);
      })
      .then(function (payload) {
        var html = api ? renderGithub(payload) : renderText(payload, lines, title);
        cache[key] = html;
        delete inflight[key];
        return html;
      })
      .catch(function (err) {
        /* Not cached: a transient failure must not poison the URL forever.
         * The original had this same property via its `loaded = false` reset. */
        delete inflight[key];
        return statusHtml("no live preview: " + (err && err.message ? err.message : "request failed"));
      });

    inflight[key] = p;
    return p;
  }

  /* ---- floating panel ------------------------------------------------ */

  function getPanel() {
    if (panel) { return panel; }
    panel = document.createElement("div");
    panel.className = "tc-hovercard";
    panel.id = PANEL_ID;
    panel.setAttribute("role", "tooltip");
    panel.setAttribute("data-tc-open", "false");
    panel.addEventListener("mouseenter", function () {
      if (hideTimer) { window.clearTimeout(hideTimer); hideTimer = null; }
    });
    panel.addEventListener("mouseleave", scheduleHide);
    document.body.appendChild(panel);
    return panel;
  }

  function position(trigger) {
    var p = getPanel();
    var r = trigger.getBoundingClientRect();
    var pr = p.getBoundingClientRect();
    var gap = 6;
    var left = Math.max(8, Math.min(r.left, window.innerWidth - pr.width - 8));
    var top = r.bottom + gap;
    if (top + pr.height > window.innerHeight - 8 && r.top - gap - pr.height > 8) {
      top = r.top - gap - pr.height;
    }
    p.style.left = Math.round(left) + "px";
    p.style.top = Math.round(top) + "px";
  }

  function show(trigger, html) {
    var p = getPanel();
    p.innerHTML = html;
    p.setAttribute("data-tc-open", "true");
    openFor = trigger;
    trigger.setAttribute("aria-describedby", PANEL_ID);
    /* Size is only known once the content is in, so position after the fill. */
    position(trigger);
  }

  function hide() {
    if (!panel) { return; }
    panel.setAttribute("data-tc-open", "false");
    if (openFor) { openFor.removeAttribute("aria-describedby"); }
    openFor = null;
  }

  function scheduleHide() {
    if (hideTimer) { window.clearTimeout(hideTimer); }
    hideTimer = window.setTimeout(function () { hideTimer = null; hide(); }, HIDE_DELAY);
  }

  /* ---- binding ------------------------------------------------------- */

  function targetFor(trigger) {
    var sel = trigger.getAttribute("data-tc-profile-target");
    if (sel) { return document.querySelector(sel); }
    return null;
  }

  function bind(trigger, url, inPlace, lines, title) {
    if (trigger.getAttribute("data-tc-hovercard-bound") === "true") { return; }
    trigger.setAttribute("data-tc-hovercard-bound", "true");

    /* A hover-only affordance is unreachable from a keyboard, so anything
     * that hovers is made focusable too. */
    if (!trigger.hasAttribute("tabindex") && !/^(a|button|input|select|textarea)$/i.test(trigger.tagName)) {
      trigger.setAttribute("tabindex", "0");
    }

    function open(immediate) {
      if (showTimer) { window.clearTimeout(showTimer); showTimer = null; }
      if (hideTimer) { window.clearTimeout(hideTimer); hideTimer = null; }
      var go = function () {
        showTimer = null;
        load(url, lines, title).then(function (html) {
          if (inPlace) { inPlace.innerHTML = html; return; }
          show(trigger, html);
        });
      };
      if (immediate) { go(); } else { showTimer = window.setTimeout(go, SHOW_DELAY); }
    }

    function close() {
      if (showTimer) { window.clearTimeout(showTimer); showTimer = null; }
      if (!inPlace) { scheduleHide(); }
    }

    trigger.addEventListener("mouseenter", function () { open(false); });
    trigger.addEventListener("focus", function () { open(true); });
    trigger.addEventListener("mouseleave", close);
    trigger.addEventListener("blur", function () {
      if (showTimer) { window.clearTimeout(showTimer); showTimer = null; }
      if (!inPlace) { hide(); }
    });
    trigger.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.keyCode === 27) { hide(); }
    });
  }

  function init(root) {
    root = root || document;
    injectStyle();

    each(root.querySelectorAll("[data-tc-profile]"), function (trigger) {
      var url = trigger.getAttribute("data-tc-profile");
      if (!url) { return; }
      var lines = parseInt(trigger.getAttribute("data-tc-profile-lines"), 10);
      if (!(lines > 0)) { lines = DEFAULT_LINES; }
      bind(trigger, url, targetFor(trigger), lines, trigger.getAttribute("data-tc-profile-title"));
    });

    /* Legacy contracts.html shape -- the page's own CSS shows the preview,
     * this only fills it. Kept so promoting the component out of tcos-www
     * does not break its one real existing consumer. */
    each(root.querySelectorAll(".contract-item"), function (item) {
      var link = item.querySelector(".contract-link");
      var preview = item.querySelector(".file-preview");
      if (!link || !preview) { return; }
      var url = preview.getAttribute("data-raw");
      if (!url) { return; }
      bind(link, url, preview, DEFAULT_LINES, null);
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" || e.keyCode === 27) { hide(); }
  });
  window.addEventListener("scroll", function () { if (openFor) { position(openFor); } }, true);
  window.addEventListener("resize", function () { if (openFor) { position(openFor); } });

  window.TC = window.TC || {};
  window.TC.hovercard = { init: init, hide: hide, cache: cache };

  ready(function () { init(document); });
})(window, document);
