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
"""
import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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
    rgb = ImageDraw.ImageDraw(Image.new("RGBA", (1, 1))).getdraw = None  # noop, keep lints quiet
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


def draw_text(draw, size, text, font_path=None):
    w, h = size
    font_size = int(min(w, h) * 0.42)
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((w / 2 - tw / 2 - bbox[0], h / 2 - th / 2 - bbox[1]), text, font=font, fill=(20, 20, 20, 255))


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
        draw_mark(draw, (w, h), recipe["mark"])
    if recipe.get("badge"):
        draw_badge(draw, (w, h), recipe["badge"])
    text = recipe.get("glyph") or recipe.get("label")
    if text:
        draw_text(draw, (w, h), text, recipe.get("font_path"))

    assert canvas.mode == "RGBA"  # real 32-bit color, always
    return canvas


def main():
    ap = argparse.ArgumentParser(prog="mt-logo-render")
    ap.add_argument("recipe", help="path to recipe .json")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    recipe = json.loads(Path(args.recipe).read_text())
    img = render(recipe)
    img.save(args.out)
    print(f"{args.out} {img.size[0]}x{img.size[1]} {img.mode}")


if __name__ == "__main__":
    main()
