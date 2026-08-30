// tc-freshness: generic "last updated" header component -- a real
// timestamp + a live-ticking delta ("updated 22h ago"), plus an
// honest sync button for pages with no live data connection yet.
// Extracted from the Roadmap Coverage dashboard (2026-08-24) into a
// shared component per Spencer's ask: "a common theme for any page
// that would benefit from that header component."
//
// Markup contract -- drop this anywhere on the page:
//   <div class="freshness" data-generated="2026-08-25T17:00:00Z">
//     <div class="fr-left">
//       <span class="fr-dot"></span>
//       <span class="fr-text">updated just now</span>
//     </div>
//     <button class="sync-btn" type="button">
//       <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3.5H10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
//       Sync
//     </button>
//   </div>
//   <p class="sync-note">Static snapshot -- ...</p>   (optional, right after)
//
// Multiple .freshness widgets on one page are supported (each is
// wired independently) -- no hardcoded IDs, this queries by class.
(function () {
  var STALE_AFTER_MS = 24 * 60 * 60 * 1000; // real policy: flag stale past 24h, not a guess

  function renderDelta(wrap, generated, textEl) {
    var ms = Date.now() - generated.getTime();
    var mins = Math.floor(ms / 60000);
    var label;
    if (mins < 1) label = "updated just now";
    else if (mins < 60) label = "updated " + mins + "m ago";
    else if (mins < 60 * 24) label = "updated " + Math.floor(mins / 60) + "h" + (mins % 60) + "m ago";
    else label = "updated " + Math.floor(mins / (60 * 24)) + "d ago";
    textEl.textContent = label;
    wrap.dataset.stale = String(ms > STALE_AFTER_MS);
  }

  function wireOne(wrap) {
    var textEl = wrap.querySelector(".fr-text");
    var generated = new Date(wrap.dataset.generated);
    if (!textEl || isNaN(generated.getTime())) return;

    renderDelta(wrap, generated, textEl);
    setInterval(function () { renderDelta(wrap, generated, textEl); }, 30000); // 30s tick -- a delta label, not a stopwatch

    var btn = wrap.querySelector(".sync-btn");
    if (!btn) return;
    var note = wrap.nextElementSibling && wrap.nextElementSibling.classList.contains("sync-note")
      ? wrap.nextElementSibling : null;

    btn.addEventListener("click", function () {
      // Real, honest state: unless a page overrides this by setting
      // data-sync-url, there's no live data connection to hit. Show
      // the real "not connected" outcome, not a fake success spin.
      var syncUrl = wrap.dataset.syncUrl;
      if (!syncUrl) {
        btn.classList.add("spinning");
        btn.disabled = true;
        setTimeout(function () {
          btn.classList.remove("spinning");
          btn.classList.add("err");
          btn.disabled = false;
          wrap.dataset.syncState = "error";
          if (note) {
            note.textContent = "Sync failed: no live data source is connected on this page. Ask Claude to regenerate it with fresh data instead.";
            note.classList.add("err");
          }
        }, 500);
        return;
      }
      // A page that DOES have a real sync endpoint sets data-sync-url;
      // this component doesn't know that endpoint's shape, so it just
      // fires a fetch and reports success/failure honestly.
      btn.classList.add("spinning");
      btn.disabled = true;
      fetch(syncUrl, { method: "POST" }).then(function (r) {
        btn.classList.remove("spinning");
        btn.disabled = false;
        if (r.ok) {
          wrap.dataset.generated = new Date().toISOString();
          generated = new Date(wrap.dataset.generated);
          renderDelta(wrap, generated, textEl);
          wrap.dataset.syncState = "ok";
        } else {
          throw new Error("sync endpoint returned " + r.status);
        }
      }).catch(function () {
        btn.classList.add("err");
        wrap.dataset.syncState = "error";
        if (note) {
          note.textContent = "Sync failed: could not reach the live data source.";
          note.classList.add("err");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".freshness[data-generated]").forEach(wireOne);
  });
})();
