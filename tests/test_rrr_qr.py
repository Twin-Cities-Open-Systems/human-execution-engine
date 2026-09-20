"""mt-logo-render's QR must actually decode, at every canvas size.

This is the regression test for issue 774: `draw_qr()` drew the QR at a
size derived from a magic divisor and then resized it to the target with
NEAREST. The factor was never an integer, so module rows were dropped
unevenly and the PNG looked like a QR while refusing to scan -- and not
monotonically, either: measured on flippy, a 320px canvas scanned while
384 and 448 did not.

So the assertion here is not "a QR was drawn". It is "zbarimg reads back
exactly the bytes that went in", at a spread of canvas sizes, for the
default payload, for a --qr-payload of the keyhole shape the store will
carry, and for --qr-primary.

Needs `qrcode` + Pillow (Debian: python3-qrcode, python3-pil) to render
and `zbarimg` (zbar-tools) to read. Missing either, the whole module
skips and says which -- a silently green run would be a lie about the one
thing this file exists to check.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "library" / "rrr" / "src" / "render.py"
RECIPE = ROOT / "library" / "rrr" / "examples" / "hee-recipe.json"

# Canvas sizes: the six from the bug report plus the small end, where a
# 22%-of-canvas QR is tightest.
SIZES = (128, 192, 256, 320, 384, 448, 512, 640, 1024)

# The payload shape the keyhole contract puts in a customer's QR:
# HK1:<kid>:<half_a>, 26 chars each from the no-0/O/1/I alphabet.
KEYHOLE = "HK1:ABCDEFGHJKLMNPQRSTUVWXYZ23:456789ABCDEFGHJKLMNPQRSTUV"

ANCHOR_URL = "https://spencer.blog.tcos.us/?hash="


def _interpreter():
    """An interpreter that can actually import what render.py imports at
    module level. `sys.executable` is not a given: pytest installed with
    pipx runs in its own venv with no system site-packages, so the
    system python3 is the one that has python3-qrcode."""
    for candidate in (sys.executable, shutil.which("python3")):
        if not candidate:
            continue
        probe = subprocess.run([candidate, "-c", "import qrcode, PIL"],
                               capture_output=True)
        if probe.returncode == 0:
            return candidate
    return None


PY = _interpreter()
ZBAR = shutil.which("zbarimg")
WHY = []
if PY is None:
    WHY.append("no python3 that can import qrcode + PIL (Debian: python3-qrcode python3-pil)")
if ZBAR is None:
    WHY.append("zbarimg not installed (Debian: zbar-tools)")


# Where the ink is, measured in a subprocess for the same reason the
# renders are: the interpreter running pytest may have no PIL. Everything
# is flattened onto white first, so a transparent logo background cannot
# read as dark.
BBOX = """
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("RGBA")
bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
bg.alpha_composite(im)
g = bg.convert("L").point(lambda v: 255 if v < 100 else 0)
print(g.size[0], g.size[1], *(g.getbbox() or (0, 0, 0, 0)))
"""

# A logo with no dark ink in it, so the dark bounding box of a
# --qr-primary render is the QR's module grid and nothing else. #F2A900
# has luminance 171 of 255; the shipped hee-recipe.json would not do,
# its #8B1E3F body and near-black label are both below the threshold.
PALE_LOGO = {"shape": "hex", "base_color": "#F2A900", "fill": "solid"}


def decode(png: Path) -> str:
    """What a scanner actually gets out of the pixels, or "" if nothing.
    zbarimg exits 4 when it finds no barcode at all -- the exact failure
    mode of the bug, so it is a normal result here, not an error."""
    r = subprocess.run([ZBAR, "--raw", "-q", str(png)], capture_output=True, text=True)
    return r.stdout.rstrip("\n") if r.returncode == 0 else ""


@unittest.skipUnless(not WHY, "; ".join(WHY))
class QrRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.recipe = json.loads(RECIPE.read_text())
        self.n = 0

    def render(self, size, *args, recipe=None):
        recipe = dict(recipe or self.recipe, size=f"{size}x{size}")
        path = self.dir / f"r-{size}-{self.n}.json"
        path.write_text(json.dumps(recipe))
        self.n += 1
        out = self.dir / f"o-{size}-{self.n}.png"
        r = subprocess.run([PY, str(RENDER), str(path), "-o", str(out), *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"render failed at {size}: {r.stderr}")
        return out

    def recipe_id(self, png):
        """The tool's own reverse path, rather than a second copy of the
        canonicalization here that could drift away from render.py's."""
        r = subprocess.run([PY, str(RENDER), "--read-anchor", str(png)],
                           capture_output=True, text=True, check=True)
        return json.loads(r.stdout)["recipe_id"]

    def test_default_payload_scans_at_every_size(self):
        bad = []
        for size in SIZES:
            png = self.render(size)
            want = ANCHOR_URL + self.recipe_id(png)
            got = decode(png)
            if got != want:
                bad.append(f"{size}: {got!r} != {want!r}")
        self.assertEqual(bad, [], "sizes whose QR did not round-trip")

    def test_custom_qr_payload_scans_at_every_size(self):
        bad = []
        for size in SIZES:
            png = self.render(size, "--qr-payload", KEYHOLE)
            got = decode(png)
            if got != KEYHOLE:
                bad.append(f"{size}: {got!r}")
        self.assertEqual(bad, [], f"sizes whose --qr-payload did not round-trip to {KEYHOLE!r}")

    def test_qr_primary_scans_at_every_size(self):
        bad = []
        for size in SIZES:
            png = self.render(size, "--qr-primary", "--qr-payload", KEYHOLE)
            got = decode(png)
            if got != KEYHOLE:
                bad.append(f"{size}: {got!r}")
        self.assertEqual(bad, [], f"sizes whose --qr-primary did not round-trip to {KEYHOLE!r}")

    def test_qr_payload_absent_means_the_anchor_url_unchanged(self):
        png = self.render(512)
        self.assertEqual(decode(png), ANCHOR_URL + self.recipe_id(png))

    def test_qr_primary_is_a_different_image_from_the_default_layout(self):
        """Not just "both scan" -- the flag has to change the layout, or a
        future refactor could quietly make --qr-primary a no-op."""
        default = self.render(512, "--qr-payload", KEYHOLE)
        primary = self.render(512, "--qr-primary", "--qr-payload", KEYHOLE)
        self.assertNotEqual(default.read_bytes(), primary.read_bytes())
        self.assertEqual(decode(default), decode(primary))

    def dark_bbox(self, png):
        """(canvas_w, canvas_h, left, top, right, bottom) of the dark ink."""
        r = subprocess.run([PY, "-c", BBOX, str(png)],
                           capture_output=True, text=True, check=True)
        return tuple(int(v) for v in r.stdout.split())

    def test_qr_primary_is_centred_on_both_axes(self):
        """Measured, not eyeballed. The first cut of --qr-primary pinned
        the QR to the top margin and it took a human opening the PNG to
        notice: at 512 the block sat at y 55..320 of 512. A layout
        regression has to fail here, not at a counter."""
        off = []
        for size in SIZES:
            png = self.render(size, "--qr-primary", "--qr-payload", KEYHOLE,
                              recipe=PALE_LOGO)
            w, h, left, top, right, bottom = self.dark_bbox(png)
            margins = (left, w - right, top, h - bottom)
            # 2px: the box is centred with integer division, and its own
            # white quiet zone is symmetric, so nothing here can drift more.
            if abs(margins[0] - margins[1]) > 2 or abs(margins[2] - margins[3]) > 2:
                off.append(f"{size}: left {margins[0]} right {margins[1]} "
                           f"top {margins[2]} bottom {margins[3]}")
        self.assertEqual(off, [], "sizes whose --qr-primary QR is not centred")

    def test_qr_primary_fills_a_real_share_of_the_canvas(self):
        """The point of the mode: not the default 22% corner badge."""
        small = []
        for size in SIZES:
            png = self.render(size, "--qr-primary", "--qr-payload", KEYHOLE,
                              recipe=PALE_LOGO)
            w, h, left, top, right, bottom = self.dark_bbox(png)
            share = (right - left) / w
            if share < 0.40:
                small.append(f"{size}: {share:.0%}")
        self.assertEqual(small, [], "sizes where --qr-primary's QR is under 40% of the canvas")

    def test_no_qr_draws_none(self):
        self.assertEqual(decode(self.render(512, "--no-qr")), "")


if __name__ == "__main__":
    unittest.main()
