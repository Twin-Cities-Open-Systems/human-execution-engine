#!/usr/bin/env python3
"""mt-logo render -- real Pillow implementation of the recipe schema
vendored in human-execution-engine/library/rrr/upstream/mt-logo-render
(recipe.rs), which only ever defined the data model, never the actual
pixel-rendering code. This is that missing half, matching the same
real schema/constraints already validated in recipe.rs:

  shape:  circle | square | triangle | hex
  size:   WxH, 16..4096 each dimension (recipe.rs's own real limit)
  color:  #RGB / #RRGGBB hex, or a name PIL recognizes
  fill:   solid | pie(deg) [circle only] | split(n) | stripe(n)
  mark:   check | x | dot (overlay, centered)
  badge:  corner_dot | corner_check (small, top-right corner)
  label:  <=4 chars, centered text
  glyph:  unicode string, centered (drawn instead of label if both given)

Output: real RGBA (32-bit color, 8 bits/channel) PNG.

DEPENDENCIES, both imported at module level and therefore required
before even `--help` will run: Pillow and `qrcode` (Debian:
python3-pil, python3-qrcode -- no pip needed). `zbar-tools` is not
needed to render, only to verify a render, which tests/test_rrr_qr.py
does with zbarimg.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import qrcode

MIN_DIM = 16
MAX_DIM = 4096


def parse_color(spec: str, default=(200, 200, 200, 255)):
    if spec is None:
        return default
    if spec.startswith("#"):
        h = spec.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b, 255)
    # named -- let PIL resolve it, real error if it can't
    from PIL import ImageColor
    r, g, b = ImageColor.getrgb(spec)
    return (r, g, b, 255)


def shape_mask(shape: str, size: tuple[int, int]) -> Image.Image:
    """Real alpha mask for the base shape, anti-aliased via 4x
    supersample-then-downscale (cheap, real quality win at every size
    in the 16..4096 range, not just the big ones)."""
    w, h = size
    ss = 4
    big = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(big)
    W, H = w * ss, h * ss
    if shape == "circle":
        d.ellipse([0, 0, W - 1, H - 1], fill=255)
    elif shape == "square":
        d.rectangle([0, 0, W - 1, H - 1], fill=255)
    elif shape == "triangle":
        d.polygon([(W / 2, 0), (W - 1, H - 1), (0, H - 1)], fill=255)
    elif shape == "hex":
        pts = []
        for i in range(6):
            angle = math.pi / 180 * (60 * i - 90)
            pts.append((W / 2 + (W / 2 - 1) * math.cos(angle), H / 2 + (H / 2 - 1) * math.sin(angle)))
        d.polygon(pts, fill=255)
    else:
        raise ValueError(f"unknown shape: {shape}")
    return big.resize((w, h), Image.LANCZOS)


def apply_fill(size, base, accent, fill_spec):
    """fill_spec: 'solid' | 'pie:<deg>' | 'split:<n>' | 'stripe:<n>'."""
    w, h = size
    img = Image.new("RGBA", size, base)
    kind, _, arg = fill_spec.partition(":")

    if kind == "solid" or not accent:
        return img

    d = ImageDraw.Draw(img)
    if kind == "pie":
        deg = int(arg or 180)
        d.pieslice([0, 0, w - 1, h - 1], start=-90, end=-90 + deg, fill=accent)
    elif kind == "split":
        n = max(int(arg or 2), 2)
        for i in range(n):
            if i % 2 == 1:
                x0 = int(w * i / n)
                x1 = int(w * (i + 1) / n)
                d.rectangle([x0, 0, x1, h], fill=accent)
    elif kind == "stripe":
        n = max(int(arg or 4), 2)
        stripe_h = h / n
        for i in range(n):
            if i % 2 == 1:
                y0 = int(stripe_h * i)
                y1 = int(stripe_h * (i + 1))
                d.rectangle([0, y0, w, y1], fill=accent)
    return img


def draw_mark(draw, size, mark, color=(20, 20, 20, 255)):
    w, h = size
    cx, cy = w / 2, h / 2
    r = min(w, h) * 0.18
    lw = max(1, int(min(w, h) * 0.04))
    if mark == "dot":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif mark == "x":
        draw.line([cx - r, cy - r, cx + r, cy + r], fill=color, width=lw)
        draw.line([cx - r, cy + r, cx + r, cy - r], fill=color, width=lw)
    elif mark == "check":
        draw.line([cx - r, cy, cx - r * 0.2, cy + r, cx + r, cy - r * 0.7], fill=color, width=lw, joint="curve")


def draw_badge(draw, size, badge, color=(220, 60, 60, 255)):
    w, h = size
    r = min(w, h) * 0.09
    cx, cy = w - r * 1.6, r * 1.6
    if badge == "corner_dot":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif badge == "corner_check":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        lw = max(1, int(r * 0.25))
        draw.line([cx - r * 0.5, cy, cx - r * 0.1, cy + r * 0.5, cx + r * 0.5, cy - r * 0.4],
                  fill=(255, 255, 255, 255), width=lw, joint="curve")


EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _is_emoji(text: str) -> bool:
    return any(ord(ch) > 0x2000 for ch in text)


def draw_text(draw, size, text, font_path=None):
    """Real fix (2026-08-22): the old fallback was
    ImageFont.load_default() -- a tiny bitmap font that CANNOT render
    emoji at all, so a glyph like the tux penguin came out as an ugly
    missing-glyph box, not a design failure ("supa ugg" was a real
    bug report, not taste). NotoColorEmoji (confirmed installed) with
    embedded_color=True renders real color emoji; DejaVuSans-Bold is a
    real, much better default for plain text labels too, instead of
    the bitmap font."""
    w, h = size
    font_size = int(min(w, h) * 0.42)
    use_emoji = _is_emoji(text) and not font_path
    emoji_mode = False

    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        elif use_emoji:
            # NotoColorEmoji is a fixed-strike bitmap-color font --
            # real size comes from its own strike, not the requested
            # pixel size, so ask big and let PIL scale the bitmap.
            font = ImageFont.truetype(EMOJI_FONT, 109)
            emoji_mode = True
        else:
            font = ImageFont.truetype(FALLBACK_FONT, font_size)
    except Exception:
        font = ImageFont.load_default()

    kwargs = {"embedded_color": True} if emoji_mode else {}
    bbox = draw.textbbox((0, 0), text, font=font, **kwargs)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (w / 2 - tw / 2 - bbox[0], h / 2 - th / 2 - bbox[1])
    if emoji_mode:
        draw.text(pos, text, font=font, embedded_color=True)
    else:
        draw.text(pos, text, font=font, fill=(20, 20, 20, 255))


def render(recipe: dict) -> Image.Image:
    w, h = map(int, recipe["size"].split("x"))
    if not (MIN_DIM <= w <= MAX_DIM and MIN_DIM <= h <= MAX_DIM):
        raise ValueError(f"size must be {MIN_DIM}..{MAX_DIM} per dimension, got {w}x{h}")

    shape = recipe.get("shape", "circle")
    base = parse_color(recipe.get("base_color"), default=(90, 140, 220, 255))
    accent = parse_color(recipe.get("accent_color")) if recipe.get("accent_color") else None
    fill_spec = recipe.get("fill", "solid")

    mask = shape_mask(shape, (w, h))
    body = apply_fill((w, h), base, accent, fill_spec)

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(body, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)
    if recipe.get("mark"):
        if accent:
            draw_mark(draw, (w, h), recipe["mark"], color=accent)
        else:
            draw_mark(draw, (w, h), recipe["mark"])
    if recipe.get("badge"):
        if accent:
            draw_badge(draw, (w, h), recipe["badge"], color=accent)
        else:
            draw_badge(draw, (w, h), recipe["badge"])
    text = recipe.get("glyph") or recipe.get("label")
    if text:
        draw_text(draw, (w, h), text, recipe.get("font_path"))

    assert canvas.mode == "RGBA"  # real 32-bit color, always
    return canvas



def canonical_json_and_id(recipe: dict) -> tuple[str, str]:
    """Real 'hee-key hole' anchor -- the exact same canonicalization
    rrr.py already does (steps=[] present, sorted keys, indent=2,
    trailing newline), so the recipe-id embedded in the image matches
    what rrr.py would independently compute from the recipe file.
    Not a second, competing hash scheme -- the same one."""
    canon = dict(recipe)
    canon.setdefault("steps", [])
    canon_json = json.dumps(canon, indent=2, sort_keys=True) + "\n"
    rid = hashlib.sha256(canon_json.encode("utf-8")).hexdigest()
    return canon_json, rid


def embed_anchor(img: Image.Image, recipe: dict) -> PngInfo:
    """Real, honest reverse path: SHA256 is one-way by design --
    finding a recipe from a hash is not possible, and guessing shape/
    color/label back out of pixels via computer vision is unreliable,
    not proof. So the image carries its own real receipt instead: the
    exact canonical recipe JSON and its id, written as standard PNG
    text chunks (tEXt) -- metadata, not pixel data, so it survives
    regardless of color mode/bit depth as long as chunks are preserved
    on re-save (2026-08-22, real ask: "even 8bit")."""
    canon_json, rid = canonical_json_and_id(recipe)
    info = PngInfo()
    info.add_text("hee-recipe", canon_json)
    info.add_text("hee-recipe-id", rid)
    return info


def read_anchor(png_path: str) -> dict:
    """The actual reverse operation: read the real embedded receipt
    back out of a rendered PNG. No guessing, no inversion -- just
    reading metadata that was written at render time."""
    img = Image.open(png_path)
    text = getattr(img, "text", {})
    if "hee-recipe-id" not in text:
        return {"anchor": None, "note": "no hee-key hole anchor found in this PNG"}
    return {
        "recipe_id": text.get("hee-recipe-id"),
        "recipe": json.loads(text.get("hee-recipe", "{}")),
    }



QR_BORDER = 2          # quiet-zone modules the qrcode library itself draws
CORNER_FRACTION = 0.22  # QR as a corner badge: fraction of the short side
BADGE_FRACTION = 0.22   # --qr-primary: the logo, shrunk to a corner badge
                        # (the QR then gets everything the badge strip leaves)
# Measured on flippy with zbarimg 0.23.93 (2026-09-19): at one pixel per
# module a decode is a coin flip -- a 45-module payload read at a 128px
# canvas while a 33-module one did not, and the same 33-module payload
# failed at 256 and passed at 192. Two pixels per module decoded at every
# size tried. So two is the floor, and a QR is allowed to take more of the
# canvas than its nominal fraction rather than become unscannable.
MIN_MODULE_PX = 2


def build_qr(payload: str, target_px: int, border: int = QR_BORDER,
             min_module_px: int = MIN_MODULE_PX) -> Image.Image:
    """A QR drawn at an exact integer number of pixels per module, and
    NEVER resampled.

    The bug this replaces (issue 774): the old code picked
    `box_size = max(1, qr_px // 25)` from a magic divisor, drew a QR
    of whatever size that produced, and then `.resize()`d it to the
    target with NEAREST. The scale factor was never an integer, so
    NEAREST -- which only preserves hard module edges at integer
    factors -- dropped roughly one module row in three, unevenly.
    The PNG still looked like a QR and simply did not decode, and
    whether it decoded was not even monotonic in canvas size: 320
    scanned while 384 and 448 did not.

    So: size from the real module count, draw once, return it at its
    natural size. The caller PADS to the target inside the white
    quiet-zone box; nothing is ever scaled. That means the returned
    image can be LARGER than `target_px` on a small canvas (one pixel
    per module is the floor) -- a slightly bigger QR that scans beats
    an exactly-sized one that does not."""
    sized = qrcode.QRCode(border=border, box_size=1)
    sized.add_data(payload)
    sized.make(fit=True)
    modules = sized.modules_count + 2 * border
    box = max(min_module_px, target_px // modules)

    # Built a second time at the real box_size rather than mutating the
    # first one's box_size after make() -- that works on the qrcode
    # release here but is not contract, and this must not depend on it.
    qr = qrcode.QRCode(version=sized.version, border=border, box_size=box)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    # make_image draws modules * box px exactly -- no resize, ever. Checked,
    # because the whole bug was an image that was not the size it claimed.
    if img.size != (modules * box, modules * box):
        raise RuntimeError(f"qrcode drew {img.size}, expected "
                           f"{modules * box}x{modules * box} -- refusing to resample")
    return img


def quiet_box(qr_img: Image.Image, target_px: int) -> Image.Image:
    """The QR's own white box: the library's quiet zone plus a real
    white margin, so the code keeps its contrast whatever it lands on
    -- a QR composited straight onto a busy fill stops decoding, which
    is how the format works, not a hypothetical.

    The QR is PADDED out to `target_px` inside this box rather than
    being resized to it, which is the whole fix. The box never shrinks
    below the QR plus its margin, so a QR that had to grow to keep one
    pixel per module keeps its white surround."""
    qr_px = qr_img.width
    pad = max(1, int(qr_px * 0.08))
    side = max(qr_px + pad * 2, target_px)
    box = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    box.paste(qr_img, ((side - qr_px) // 2, (side - qr_px) // 2))
    return box


def fit_qr_box(payload: str, target_px: int, max_w: int, max_h: int):
    """The largest honest QR box that fits: two pixels per module if the
    canvas allows, one if it must (and it says so, because that is the
    size zbarimg reads only by luck), None if not even that fits."""
    for min_px in (MIN_MODULE_PX, 1):
        box = quiet_box(build_qr(payload, target_px, min_module_px=min_px), target_px)
        if box.width <= max_w and box.height <= max_h:
            if min_px < MIN_MODULE_PX:
                print("mt-logo-render: this canvas only fits one pixel per QR "
                      "module -- it may not scan; render larger", file=sys.stderr)
            return box
    return None


def draw_qr(canvas: Image.Image, payload: str) -> bool:
    """Real, scannable QR -- survives any format/bit-depth change
    since it's pixels, not metadata (2026-08-22, real ask: "qr code
    inspired", "even 8bit"). Corner badge, bottom-right, over its own
    white quiet-zone box. Returns False and says so on stderr if even
    a one-pixel-per-module QR will not fit the canvas, rather than
    compositing something that cannot be scanned."""
    w, h = canvas.size
    target = max(int(min(w, h) * CORNER_FRACTION), 21)
    box = fit_qr_box(payload, target, w, h)
    if box is None:
        print(f"mt-logo-render: no scannable QR for this payload fits a "
              f"{w}x{h} canvas -- QR omitted", file=sys.stderr)
        return False
    x = max(0, w - box.width - int(w * 0.03))
    y = max(0, h - box.height - int(h * 0.03))
    canvas.alpha_composite(box, (x, y))
    return True


def draw_qr_primary(canvas: Image.Image, payload: str) -> Image.Image:
    """The inverse layout: the QR is the main element and the rendered
    logo becomes the corner badge. A customer-facing pickup token is
    scanned off a phone, where a 22%-of-canvas corner QR is not a
    usable target; the keyhole payload in fleet-ops#109 needs this.

    The badge sits BELOW the QR's white box, never on top of it. A
    logo composited over live modules is damage the error correction
    may or may not absorb, which is the same coin-flip this change
    exists to remove.

    Returns a NEW canvas -- the logo is consumed as the badge -- so the
    default layout above is untouched."""
    w, h = canvas.size
    margin = max(2, int(min(w, h) * 0.03))
    badge_px = max(int(min(w, h) * BADGE_FRACTION), 8)
    # Reserve the badge strip first, so the QR is sized into what is left.
    # 0.84 leaves room for the box's own white margin, which quiet_box adds
    # around the QR -- ask for the full space and the box overflows it.
    avail = min(w - 2 * margin, h - badge_px - 3 * margin)
    box = fit_qr_box(payload, max(int(avail * 0.84), 21), avail, avail)
    if box is None:
        # No QR fits beside a badge. Try the whole canvas instead; the
        # overlap check below then drops the badge and says so.
        room = min(w, h) - 2 * margin
        box = fit_qr_box(payload, max(int(room * 0.84), 21), w, h)
    if box is None:
        print(f"mt-logo-render: --qr-primary has no scannable QR that fits a "
              f"{w}x{h} canvas -- left as the plain logo", file=sys.stderr)
        return canvas

    out = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    qr_y = margin if box.height + margin <= h else max(0, (h - box.height) // 2)
    out.alpha_composite(box, (max(0, (w - box.width) // 2), qr_y))

    badge_y = h - badge_px - margin
    if badge_y >= qr_y + box.height:
        # LANCZOS, not NEAREST: this is the logo artwork, not QR modules.
        badge = canvas.resize((badge_px, badge_px), Image.LANCZOS)
        out.alpha_composite(badge, (max(0, w - badge_px - margin), badge_y))
    else:
        print(f"mt-logo-render: --qr-primary at {w}x{h} has no room for the "
              f"logo badge beside the QR -- badge omitted", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser(prog="mt-logo-render")
    ap.add_argument("recipe", nargs="?", help="path to recipe .json")
    ap.add_argument("-o", "--out", help="output PNG path")
    ap.add_argument("--read-anchor", metavar="PNG", help="read the real embedded recipe/hash back out of a rendered PNG")
    ap.add_argument("--no-qr", action="store_true", help="skip the scannable QR corner badge")
    ap.add_argument("--qr-payload", metavar="TEXT",
                    help="put TEXT in the QR instead of the recipe's anchor URL "
                         "(default: https://spencer.blog.tcos.us/?hash=RECIPE_ID)")
    ap.add_argument("--qr-primary", action="store_true",
                    help="inverse layout -- the QR is the main element and the logo "
                         "becomes the corner badge (for a scanned-off-a-phone token)")
    args = ap.parse_args()

    if args.read_anchor:
        result = read_anchor(args.read_anchor)
        print(json.dumps(result, indent=2))
        return

    if not args.recipe or not args.out:
        ap.error("recipe and -o/--out are required unless using --read-anchor")

    recipe = json.loads(Path(args.recipe).read_text())
    img = render(recipe)
    anchor = embed_anchor(img, recipe)
    _canon_json, rid = canonical_json_and_id(recipe)
    if not args.no_qr:
        qr_payload = args.qr_payload or f"https://spencer.blog.tcos.us/?hash={rid}"
        if args.qr_primary:
            img = draw_qr_primary(img, qr_payload)
        else:
            draw_qr(img, qr_payload)
    img.save(args.out, pnginfo=anchor)
    print(f"{args.out} {img.size[0]}x{img.size[1]} {img.mode}")


if __name__ == "__main__":
    main()
