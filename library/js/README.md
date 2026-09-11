# library/js

Shared browser components for TCOS's static surfaces -- `view.lab.tcos.us`,
`tcos.us`, and anything else served off a static tree by busybox httpd.

**Zero dependencies.** No framework, no bundler, no CDN, no build step, no
`node_modules`. Each file is one plain script that a `<script>` tag loads
directly. This is a hard constraint, not a preference: these pages are served
by busybox httpd out of a directory, and there is nothing there to run a build.

Every file also holds to the same four rules:

- **It works alone.** No file needs any other file in this directory. Include
  one, include all six, in any order.
- **It does nothing if its markup is absent.** A page that includes `table.js`
  but has no `[data-tc-table]` or `table.tc-table` pays for one `querySelectorAll`
  and stops.
- **Hover is never the only way in.** Anything that responds to a mouse
  responds to a keyboard, because a hover-only affordance does not exist for
  someone who does not use a mouse.
- **`prefers-reduced-motion` is respected.** Every transition sits inside
  `@media (prefers-reduced-motion: no-preference)`, so the reduced-motion
  setting gets no animation at all rather than a faster one.

## The components

| File | What it does | Markup it looks for |
| --- | --- | --- |
| `library/js/hovercard.js` | GitHub-style hover preview of a file or an issue | `[data-tc-profile]` |
| `library/js/collapse.js` | Collapse and expand a card, remembered per card | `[data-tc-collapse]` |
| `library/js/arrange.js` | Drag cards into a new order, remembered | `[data-tc-arrange]` |
| `library/js/table.js` | Sort any column, filter across every field as you type | `[data-tc-table]`, `table.tc-table` |
| `library/js/links.js` | External links open a new tab, safely | every `a[href]` |
| `library/js/freshness.js` | How old a page's source is, as a pill and a hue; stale after 12h by default | `[data-tc-epoch]` |

### freshness.js

```html
<script src="js/freshness.js" defer></script>
```

```html
<section class="card" data-tc-epoch="1789024938" data-tc-stale-hours="12">
  <header><h2>Freshness</h2></header>
  ...
</section>
```

`data-tc-epoch` is the source's commit time in unix seconds -- `view/build.sh`
already writes it into every page's freshness card. The component sets
`data-tc-fresh="ok|stale|unknown"` on the element (and on `<html>` for the
page's first one), adds a pill to the element's header reading `● OK · 3h` or
`▲ STALE · 2d 4h` (icon and label, never a color alone), colors the left
border with the host page's `--good`/`--warning` tokens, and re-evaluates once
a minute so a page left open turns stale by itself. `data-tc-stale-hours`
overrides the 12-hour default per element. The epoch is also written as a date
in the reader's own locale and zone: in the pill's title, and as a `local` row
appended to the element's `<dl>` when it has one (the build stamps UTC; the
reader's zone is only known in the reader's browser). An empty epoch (a source not yet
committed) reads `○ UNKNOWN · not committed`.

Operator brief, 2026-09-10: "standardize on a freshness that works, changes
color (hue) when stale (12h is stale, default)".

### hovercard.js

```html
<script src="js/hovercard.js" defer></script>
```

```html
<a href="https://github.com/owner/repo/blob/main/x.yaml"
   data-tc-profile="https://raw.githubusercontent.com/owner/repo/main/x.yaml">x.yaml</a>
```

Fetches on hover **and on focus**, shows the first 14 lines, caches per URL so a
second hover costs nothing. A GitHub issue or pull-request URL is recognized and
rendered as a real issue card instead -- state, title, author, first lines of
the body -- which is the "gh issue/pr should have a hover just like in gh app"
part of the brief. The state carries an icon **and** a text label
(`◆ merged`, `✖ closed`, `○ draft`, `● open`), never a color on its own, per the
org's status-output rule.

Options on the trigger: `data-tc-profile-lines`, `data-tc-profile-title`,
`data-tc-profile-target` (render into an element you supply instead of the
floating panel).

Provenance: this is a promotion, not an invention. It began as
`shell/tc-hovercard.js` in `tcos-www`
(https://github.com/Twin-Cities-Open-Systems/tcos-www/blob/main/shell/tc-hovercard.js),
itself ported verbatim from `view.lab.tcos.us/contracts.html` on 2026-08-28.
That file's own header names this generalization as the plan already written
down at `view.lab.tcos.us/plan.html`: *"tc-hovercard.js: GitHub-style hover
preview for any `data-tc-profile` link."* The original was hardcoded to
`.contract-item`; that hardcoding is what this file removes.

It still handles the original `.contract-item` / `.contract-link` /
`.file-preview[data-raw]` shape, so it drops into `contracts.html` in place of
`shell/tc-hovercard.js` with no markup change. Promoting a component out of the
page that grew it should not break that page.

### collapse.js

```html
<script src="js/collapse.js" defer></script>
```

```html
<section data-tc-collapse="hosts">
  <h2 data-tc-collapse-toggle>Hosts</h2>
  <div data-tc-collapse-body> ... </div>
</section>
```

Click or Enter/Space on the heading collapses the card. State is stored in
`localStorage` under `tc.collapse.<path>.<id>`, so it survives a reload.

The toggle and the body are both optional. Without `data-tc-collapse-toggle`
the first direct-child heading, `<summary>` or `.tc-card-head` is used, and if
there is none a button is created. Without `data-tc-collapse-body` every child
except the toggle is hidden. `data-tc-collapse-default="collapsed"` starts a
card closed the first time it is seen; stored state wins after that.

A card with neither `data-tc-collapse="id"` nor an `id` still collapses but is
**not** remembered -- there is no stable name to store it under, and a
position-derived name would silently reattach state to a different card as soon
as the page reordered, which `arrange.js` exists to do.

`TC.collapse.collapseAll()` / `TC.collapse.expandAll()` are there for a
page-level control.

### arrange.js

```html
<script src="js/arrange.js" defer></script>
```

```html
<div data-tc-arrange="dashboard">
  <section data-tc-arrange-item="hosts">
    <h2 data-tc-arrange-handle>Hosts</h2>
    ...
  </section>
</div>
```

Drag to reorder, using the browser's own HTML5 drag-and-drop API. Order is
stored under `tc.arrange.<path>.<key>` as a list of item ids; an item that has
since been removed is skipped on restore and a newly added one keeps its place
in the markup, so the saved order degrades instead of breaking.

`data-tc-arrange-handle` is optional but recommended: with a handle, a drag
starts only from the handle, so text inside a card stays selectable and links
inside it stay clickable.

**Keyboard.** Drag-and-drop is mouse-only, so this is a real path rather than a
courtesy: Tab to a handle, **Space** or **Enter** picks the card up, the
**arrow keys** move it, **Space** drops it, **Escape** cancels and puts it back
where it started. Every step is announced through an `aria-live` region.

As with `collapse.js`, an item with no id means the container's order is not
persisted -- reported once to the console rather than passing in silence.

### table.js

```html
<script src="js/table.js" defer></script>
```

```html
<input type="search" data-tc-table-filter="#hosts">
<span data-tc-table-count="#hosts"></span>
<table id="hosts" data-tc-table>
  <thead><tr><th>Host</th><th data-tc-sort="number">Uptime</th></tr></thead>
  <tbody> ... </tbody>
</table>
```

Click (or focus and press Enter) any column heading to sort; click again to
reverse. The comparison type is detected from the column's own values and can be
forced with `data-tc-sort="text|number|date"`. `data-tc-nosort` opts a column
out. `data-tc-sort-value` on a cell gives it a sort and filter key different
from its text -- the way to sort a status icon or a "3 days ago".

The search box is a real text input filtering on every keystroke, across every
column at once, with no debounce -- the work is a substring scan over rows
already in the DOM, and a delay is what makes a search box feel dead. Words are
ANDed, so `pve down` narrows to rows mentioning both, in any column, in any
order. Escape clears the box. Everything is client-side over already-rendered
rows; nothing is fetched and no row is re-created.

Two details worth knowing:

- Sorting is **stable**. `Array.prototype.sort` is only guaranteed stable from
  ES2019, which is not a guarantee a kiosk browser makes, so the original row
  index is the explicit tiebreaker.
- Filtering matches **visible** text only. `aria-hidden` decoration and
  `.tc-sr-only` text are excluded, so `links.js`'s screen-reader hint does not
  make every row with an external link match a search for "tab".

Every `table.tc-table` is bound too, marked or not. A table styled as the
org's table is a sortable table, so no page can ship one without sort controls.
That gap is what left the scorecard on agents-live unsortable, 2026-09-11.

**Live pages keep the viewer's sort and search.** When a page replaces a bound
table's rows, on a poll for example, the rows are re-sorted by the active column
and re-filtered by the bound search box. The page calls nothing. Before this,
every poll on agents-live and tickets undid the viewer's sort while the heading
still showed it.

If a row's cells change in place after load, call
`TC.table.refresh(tableOrSelector)`. It drops the cached row text and re-applies
the sort and the search. It takes a table or a selector, and returns null rather
than throwing when nothing matches, because pages call it from a render loop.

`tests/test_js_table.py` checks all of this in headless Chrome.

### links.js

```html
<script src="js/links.js" defer></script>
```

No markup needed. Every `http:`/`https:` link to another origin gets
`target="_blank"` and `rel="noopener noreferrer"`.

The `rel` is the point. `target="_blank"` on its own is a real vulnerability:
without `noopener` the opened page receives a `window.opener` handle back to the
page that opened it and can navigate this tab somewhere else -- tab-nabbing.
Current browsers imply `noopener` for `target="_blank"`, but "a current browser"
is not a guarantee a kiosk makes, so it is written out. `noreferrer` goes with it
so the destination is not handed this page's URL.

Left alone: same-origin links, fragments, `mailto:`, `tel:`, any other scheme,
anything with `download`, anything with an author-set `target` (its `rel` is
still repaired, because the opener handle is handed over either way), any link
marked `data-tc-external="keep"`, and anything inside a `[data-tc-links-skip]`
subtree.

Each rewritten link also gets visually-hidden "(opens in a new tab)" text, since
an unannounced context switch is disorienting and WCAG 3.2.5 asks for the
warning. `data-tc-links-nohint` suppresses it on one link.

## Including them

Load order does not matter and `defer` is safe:

```html
<script src="js/links.js" defer></script>
<script src="js/hovercard.js" defer></script>
<script src="js/collapse.js" defer></script>
<script src="js/arrange.js" defer></script>
<script src="js/table.js" defer></script>
```

Each file checks `document.readyState` rather than only listening for
`DOMContentLoaded`, so a deferred or dynamically appended script still
initializes -- the original `tc-hovercard.js` used a bare `DOMContentLoaded`
listener and silently did nothing when it loaded after that event had fired.

## Re-running after the DOM changes

Each component registers itself on a shared `window.TC` namespace and can be
re-run over a subtree it has not seen:

```js
TC.links.init(newlyAddedElement);
TC.hovercard.init(newlyAddedElement);
TC.collapse.init(newlyAddedElement);
TC.arrange.init(newlyAddedElement);
TC.table.init(newlyAddedElement);
```

Re-initializing is safe: already-bound elements are skipped. No component
installs a `MutationObserver` -- watching the whole document forever to catch a
case most pages never hit is a cost every page would pay.

## Theming

Each component styles itself from the host page's CSS custom properties where
they exist, falling back to its own light and dark values where they do not:
`--surface`, `--ink`, `--ink-dim`, `--ink-faint`, `--line`, `--accent`. A page
that already defines those (as `contracts.html` does) gets components in its own
palette with no extra CSS.

## Testing

`library/js/test.html` exercises every component with fixture markup and runs
real assertions against the live DOM, reporting each with an icon and a text
label. Serve it rather than opening it as `file://` -- browsers block `fetch`
on `file://`, which the hovercard needs:

```sh
cd library/js && python3 -m http.server 8080
# or, matching production:  busybox httpd -f -p 8080
```

Then open `http://127.0.0.1:8080/test.html`.

## Where this fits

`library/` is this repo's home for shared, reusable implementation --
`library/bash/`, `library/py/`, `library/sh/`, `library/regex/`. `library/js/`
is the same idea for the browser: components live here once, and the pages that
use them stop each growing their own copy. That is the failure this directory
exists to prevent, and it is a failure with a measured history in this org --
three diverged copies of one file across three repos, recorded in
`prompts/PROMPTING_RULES.md` rule 16.
