#!/usr/bin/env python3
"""
Generate the static images used for search and social previews:

  assets/og-image.png          1200x630 Open Graph / Twitter card
  assets/apple-touch-icon.png  180x180 iOS home-screen icon
  assets/cmm-icon-192.png      192x192 web app manifest icon

Development-time tool only: requires Pillow (pip install pillow). The web
server itself has no third-party dependencies.

Usage:  python3 scripts/generate_seo_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - dev tool
    sys.exit("Pillow is required: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = (9, 9, 11)
SURFACE = (23, 23, 27)
LINE = (42, 42, 49)
TEXT = (244, 244, 245)
MUTED = (161, 161, 170)
ACCENT = (124, 156, 255)

FONT_DIRS = [
    Path("/usr/share/fonts"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("C:/Windows/Fonts"),
]


def find_font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        if not directory.exists():
            continue
        for name in names:
            matches = sorted(directory.rglob(name))
            if matches:
                return ImageFont.truetype(str(matches[0]), size)
    print(f"warning: none of {names} found, using default font", file=sys.stderr)
    return ImageFont.load_default(size)


def og_image() -> None:
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Subtle grid texture
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(14, 14, 17))
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(14, 14, 17))

    title = find_font(["Inter-Bold.otf", "Inter-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 76)
    body = find_font(["Inter-Regular.otf", "Inter-Regular.ttf", "DejaVuSans.ttf", "Arial.ttf"], 32)
    mono = find_font(["JetBrainsMono-Medium.ttf", "JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf"], 26)
    mono_big = find_font(["JetBrainsMono-Bold.ttf", "JetBrainsMono-ExtraBold.ttf", "DejaVuSansMono-Bold.ttf"], 44)

    margin = 80
    logo = Image.open(ASSETS / "cmm-icon-512.png").convert("RGBA").resize((96, 96), Image.LANCZOS)
    img.paste(logo, (margin, 78), logo)
    draw.text((margin + 120, 98), "C", font=mono_big, fill=TEXT)
    c_width = draw.textlength("C", font=mono_big)
    draw.text((margin + 120 + c_width, 98), "--", font=mono_big, fill=ACCENT)
    pill_x = margin + 120 + c_width + draw.textlength("--", font=mono_big) + 22
    draw.rounded_rectangle([pill_x, 106, pill_x + 112, 146], radius=8, fill=SURFACE, outline=LINE)
    draw.text((pill_x + 18, 111), "v0.2.0", font=mono, fill=MUTED)

    label = find_font(["Inter-SemiBold.otf", "Inter-SemiBold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], 34)
    draw.text((margin, 238), "C Minus Minus — a memory-safe programming language", font=label, fill=MUTED)
    draw.text((margin, 300), "Memory safety by removal,", font=title, fill=TEXT)
    draw.text((margin, 388), "not by runtime.", font=title, fill=ACCENT)

    draw.line([(margin, 530), (width - margin, 530)], fill=LINE, width=2)
    draw.text((margin, 552), "No pointers \u00b7 No null \u00b7 Immutable by default \u00b7 ISO C99 transpiler",
              font=body, fill=MUTED)

    out = ASSETS / "og-image.png"
    img.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def icon(size: int, name: str, padded: bool) -> None:
    logo = Image.open(ASSETS / "cmm-icon-512.png").convert("RGBA")
    canvas = Image.new("RGBA", (size, size), BG + (255,) if padded else (0, 0, 0, 0))
    inner = int(size * 0.78) if padded else size
    resized = logo.resize((inner, inner), Image.LANCZOS)
    offset = (size - inner) // 2
    canvas.paste(resized, (offset, offset), resized)
    out = ASSETS / name
    canvas.save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    og_image()
    icon(180, "apple-touch-icon.png", padded=True)
    icon(192, "cmm-icon-192.png", padded=False)
