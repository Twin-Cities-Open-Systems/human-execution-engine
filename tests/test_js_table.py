"""library/js/table.js in a real browser: every column of every org table sorts,
and a page that re-renders rows on a poll keeps the viewer's sort and search.

Operator, 2026-09-11: "make sure all columns are sortable, the scorecard is not".
The scorecard on agents-live carried class tc-table without data-tc-table, so it
never got sort controls. Every live page also re-rendered its rows on a poll,
which silently undid the viewer's sort, and agents-live's refresh call passed a
selector the library did not accept.

Runs headless Chrome with --dump-dom. Waits use promise callbacks, which run
after the row observer's. --virtual-time-budget and --user-data-dir both hung Chrome 148 here, 2026-09-11. Set HEE_CHROME to pick a binary; with no
browser on the host the test is skipped and says so."""
import glob, html, json, os, re, shutil, subprocess, tempfile, unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "library" / "js" / "table.js"


def find_chrome():
    cands = [os.environ.get("HEE_CHROME", "")]
    cands += [shutil.which(b) or "" for b in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    cands += sorted(glob.glob(os.path.expanduser("~/.cache/puppeteer/chrome/*/chrome-linux64/chrome")), reverse=True)
    for c in cands:
        if c and os.access(c, os.X_OK):
            return c
    return None


PAGE = r"""<!doctype html><html><body>
<input type="search" data-tc-table-filter="#t" id="q">
<table class="tc-table" id="t"><thead><tr><th>name</th><th data-tc-sort="number">cost</th><th data-tc-sort="number">wall</th></tr></thead><tbody>
<tr><td>bravo</td><td>10</td><td data-tc-sort-value="200">3m20s</td></tr>
<tr><td>alpha keep</td><td>&ndash;</td><td data-tc-sort-value="5">0m05s</td></tr>
<tr><td>charlie keep</td><td>1.5</td><td data-tc-sort-value="61">1m01s</td></tr>
</tbody></table>
<pre id="result">not run</pre>
<script src="table.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  var out = {}, t = document.getElementById("t"), q = document.getElementById("q");
  function names() {
    return Array.prototype.map.call(t.tBodies[0].rows, function (r) {
      return r.cells[0].textContent + (r.getAttribute("data-tc-filtered") === "true" ? " (hidden)" : "");
    });
  }
  function th(i) { return t.tHead.rows[0].cells[i]; }
  out.bound_by_class = [0, 1, 2].every(function (i) { return th(i).hasAttribute("data-tc-sortable"); });
  out.attribute_added = t.hasAttribute("data-tc-table");
  th(1).click(); out.cost_asc = names();
  th(1).click(); out.cost_desc = names();
  th(2).click(); out.wall_asc = names();
  th(2).click(); out.wall_desc = names();
  q.value = "keep"; q.dispatchEvent(new Event("input")); out.filtered = names();
  t.tBodies[0].innerHTML =
    '<tr><td>alpha keep</td><td>2</td><td data-tc-sort-value="5">0m05s</td></tr>' +
    '<tr><td>delta</td><td>4</td><td data-tc-sort-value="900">15m00s</td></tr>' +
    '<tr><td>echo keep</td><td>3</td><td data-tc-sort-value="400">6m40s</td></tr>';
  Promise.resolve().then(function () {
    out.after_poll = names();
    out.after_poll_aria = th(2).getAttribute("aria-sort");
    var alpha = t.tBodies[0].rows[t.tBodies[0].rows.length - 1];
    alpha.cells[2].setAttribute("data-tc-sort-value", "1000");
    out.refresh_returns_table = TC.table.refresh("#t") === t;
    out.after_refresh = names();
    out.refresh_missing_is_null = TC.table.refresh("#no-such-table") === null;
    var nb = document.createElement("tbody");
    nb.innerHTML = '<tr><td>fox keep</td><td>1</td><td data-tc-sort-value="1">0m01s</td></tr>' +
                   '<tr><td>golf keep</td><td>1</td><td data-tc-sort-value="9999">166m39s</td></tr>';
    t.replaceChild(nb, t.tBodies[0]);
    Promise.resolve().then(function () {
      out.after_tbody_swap = names();
      q.value = ""; q.dispatchEvent(new Event("input")); out.cleared = names();
      document.getElementById("result").textContent = JSON.stringify(out);
    });
  });
});
</script></body></html>"""


class TableInBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chrome = find_chrome()
        if not chrome:
            raise unittest.SkipTest("no Chrome or Chromium on this host (set HEE_CHROME)")
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(LIB, Path(d) / "table.js")
            (Path(d) / "page.html").write_text(PAGE)
            r = subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu",
                                "--dump-dom", "file://" + str(Path(d) / "page.html")],
                               capture_output=True, text=True, timeout=90)
        m = re.search(r'<pre id="result">(.*?)</pre>', r.stdout, re.S)
        if not m or m.group(1) == "not run":
            raise AssertionError("page script did not finish: " + r.stdout[-400:] + r.stderr[-400:])
        cls.out = json.loads(html.unescape(m.group(1)))

    def test_class_alone_makes_every_column_sortable(self):
        self.assertTrue(self.out["bound_by_class"])
        self.assertTrue(self.out["attribute_added"])

    def test_number_column_with_a_dash_keeps_the_dash_last_both_ways(self):
        self.assertEqual(self.out["cost_asc"], ["charlie keep", "bravo", "alpha keep"])
        self.assertEqual(self.out["cost_desc"], ["bravo", "charlie keep", "alpha keep"])

    def test_sort_value_orders_durations_not_their_text(self):
        self.assertEqual(self.out["wall_asc"], ["alpha keep", "charlie keep", "bravo"])
        self.assertEqual(self.out["wall_desc"], ["bravo", "charlie keep", "alpha keep"])

    def test_search_hides_non_matching_rows(self):
        self.assertEqual(self.out["filtered"], ["bravo (hidden)", "charlie keep", "alpha keep"])

    def test_poll_rerender_keeps_sort_and_search(self):
        self.assertEqual(self.out["after_poll"], ["delta (hidden)", "echo keep", "alpha keep"])
        self.assertEqual(self.out["after_poll_aria"], "descending")

    def test_refresh_takes_a_selector_and_reapplies(self):
        self.assertTrue(self.out["refresh_returns_table"])
        self.assertEqual(self.out["after_refresh"], ["alpha keep", "delta (hidden)", "echo keep"])
        self.assertTrue(self.out["refresh_missing_is_null"])

    def test_replaced_tbody_is_sorted_too(self):
        self.assertEqual(self.out["after_tbody_swap"], ["golf keep", "fox keep"])
        self.assertEqual(self.out["cleared"], ["golf keep", "fox keep"])


if __name__ == "__main__":
    unittest.main()
