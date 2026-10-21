#!/usr/bin/env python3
"""
Build the Group 16 case-study PDF from report.html.

Fills the template with the C-- source, the C-- program output, the benchmark
kernels and two SVG figures, then prints it with headless Chromium.

Usage:  python3 case_studies/simd_masked_vectorization/report/build_pdf.py
        (set CHROME=/path/to/chrome if Chromium is not found automatically)
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
OUT_PDF = STUDY / "Group16_Case_Study_AVX512_Masked_Vectorization.pdf"

# ---------------------------------------------------------------- cover details (edit as needed)
MEMBERS = [
    ("Ronit Mexson", "24BAI0036"),
    ("Mit Kumar Raju Panchal", "24BAI0279"),
    ("Garv Gupta", "24BDS0169"),
]
SUPERVISOR = "Prof. Hariharan R L"
INSTITUTION = "School of Computer Science &amp; Engineering (SCOPE)"
DATE = "October 2026"

# ---------------------------------------------------------------- measured data (typical values, see README / Table 5)
DATASETS = ["Random sign", "90% positive", "Alternating", "Sorted", "All positive"]
SCALAR = [13.7, 4.4, 2.3, 2.47, 2.47]
AVX512 = [0.725] * 5
AVX2 = [0.618] * 5

S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3
INK, INK2, INK3, GRID = "#111114", "#3d3d45", "#6b6b75", "#e4e4e8"
FONT = "Inter Report, Helvetica, Arial, sans-serif"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


# ---------------------------------------------------------------- figure 1: grouped bars
def figure_bars() -> str:
    w, h = 640, 300
    left, right, top, bottom = 44, 12, 40, 44
    plot_w, plot_h = w - left - right, h - top - bottom
    y_max = 14.0
    y = lambda v: top + plot_h - v / y_max * plot_h
    group_w = plot_w / len(DATASETS)
    bar_w, gap = 22, 2
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']

    # legend (top)
    lx = left
    for color, label in ((S1, "Scalar with branch"), (S2, "AVX-512 masked (zmm, k1/k2)"), (S3, "AVX2 compare + blend (ymm)")):
        parts.append(f'<rect x="{lx}" y="10" width="10" height="10" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{lx + 15}" y="19" font-size="10.5" fill="{INK2}">{esc(label)}</text>')
        lx += 15 + len(label) * 5.6 + 22

    # grid + y axis
    for v in range(0, 15, 2):
        yy = y(v)
        parts.append(f'<line x1="{left}" x2="{w - right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GRID}" stroke-width="{1.2 if v == 0 else 0.8}"/>')
        parts.append(f'<text x="{left - 6}" y="{yy + 3.5:.1f}" font-size="9.5" fill="{INK3}" text-anchor="end">{v}</text>')
    parts.append(f'<text x="12" y="{top + plot_h / 2:.0f}" font-size="9.5" fill="{INK3}" text-anchor="middle" '
                 f'transform="rotate(-90 12 {top + plot_h / 2:.0f})">TSC ticks per element</text>')

    def bar(x: float, value: float, color: str) -> str:
        y0, y1 = y(0), y(value)
        height = max(y0 - y1, 1.0)
        r = min(4.0, height / 2, bar_w / 2)
        # rounded top corners only, anchored to the baseline
        return (f'<path d="M{x:.1f},{y0:.1f} V{y0 - height + r:.1f} Q{x:.1f},{y0 - height:.1f} {x + r:.1f},{y0 - height:.1f} '
                f'H{x + bar_w - r:.1f} Q{x + bar_w:.1f},{y0 - height:.1f} {x + bar_w:.1f},{y0 - height + r:.1f} V{y0:.1f} Z" fill="{color}"/>')

    for i, name in enumerate(DATASETS):
        cx = left + group_w * i + group_w / 2
        x0 = cx - (3 * bar_w + 2 * gap) / 2
        parts.append(bar(x0, SCALAR[i], S1))
        parts.append(bar(x0 + bar_w + gap, AVX512[i], S2))
        parts.append(bar(x0 + 2 * (bar_w + gap), AVX2[i], S3))
        parts.append(f'<text x="{x0 + bar_w / 2:.1f}" y="{y(SCALAR[i]) - 5:.1f}" font-size="10" font-weight="600" '
                     f'fill="{INK}" text-anchor="middle">{SCALAR[i]:g}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{h - bottom + 16}" font-size="10" fill="{INK2}" text-anchor="middle">{esc(name)}</text>')

    # one annotation for the constant vector results
    ax = left + group_w * 2 - 10
    ay = y(11.5)
    parts.append(f'<text x="{ax:.1f}" y="{ay:.1f}" font-size="10" fill="{INK2}">Vector versions: 0.725 (AVX-512) and 0.618 (AVX2)</text>')
    parts.append(f'<text x="{ax:.1f}" y="{ay + 13:.1f}" font-size="10" fill="{INK2}">on every dataset: run time no longer depends on the data</text>')
    parts.append(f'<text x="{left}" y="{h - 8}" font-size="9" fill="{INK3}">N = 65 537 floats; typical values over more than ten runs (ranges in Table 5).</text>')
    parts.append("</svg>")
    return ('<figure>' + "".join(parts) +
            '<figcaption><b>Figure 1.</b> Time per element for the branchy scalar loop and the two predicated vector loops. '
            'The scalar cost is set by the branch predictor; the vector cost is constant.</figcaption></figure>')


# ---------------------------------------------------------------- figure 2: frequency timeline
def frequency_data() -> tuple[float, list[tuple[float, float]]]:
    text = (STUDY / "results" / "bench_output.txt").read_text()
    cold = float(re.search(r"after 50 ms of scalar code only:\s+([0-9.]+)", text).group(1))
    points = [(float(a), float(b)) for a, b in re.findall(r"^\s+([0-9.]+) ms\s+([0-9.]+)$", text, re.M)]
    return cold, points


def figure_frequency() -> str:
    cold, points = frequency_data()
    w, h = 640, 250
    left, right, top, bottom = 48, 150, 18, 40
    plot_w, plot_h = w - left - right, h - top - bottom
    y_lo, y_hi, x_hi = 0.55, 0.90, 6.0
    x = lambda v: left + v / x_hi * plot_w
    y = lambda v: top + plot_h - (v - y_lo) / (y_hi - y_lo) * plot_h
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    for v in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90):
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="0.8"/>')
        parts.append(f'<text x="{left - 6}" y="{y(v) + 3.5:.1f}" font-size="9.5" fill="{INK3}" text-anchor="end">{v:.2f}</text>')
    for t in range(0, 7):
        parts.append(f'<text x="{x(t):.1f}" y="{top + plot_h + 15}" font-size="9.5" fill="{INK3}" text-anchor="middle">{t}</text>')
    parts.append(f'<text x="{left + plot_w / 2:.0f}" y="{h - 6}" font-size="9.5" fill="{INK3}" text-anchor="middle">'
                 f'time since the end of a 30 ms burst of 512-bit vsqrtps (ms)</text>')
    parts.append(f'<text x="13" y="{top + plot_h / 2:.0f}" font-size="9.5" fill="{INK3}" text-anchor="middle" '
                 f'transform="rotate(-90 13 {top + plot_h / 2:.0f})">TSC ticks per element</text>')
    # reference lines
    for value, label in ((cold, f"cool core: {cold:.3f}"), (0.725, "512-bit kernel: 0.725")):
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y(value):.1f}" y2="{y(value):.1f}" stroke="{INK3}" '
                     f'stroke-width="1" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{left + plot_w + 6}" y="{y(value) + 3.5:.1f}" font-size="9.5" fill="{INK2}">{label}</text>')
    path = " ".join(f'{"M" if i == 0 else "L"}{x(t):.1f},{y(v):.1f}' for i, (t, v) in enumerate(points))
    parts.append(f'<path d="{path}" fill="none" stroke="{S1}" stroke-width="2" stroke-linejoin="round"/>')
    for t, v in points:
        parts.append(f'<circle cx="{x(t):.1f}" cy="{y(v):.1f}" r="4" fill="{S1}" stroke="#ffffff" stroke-width="2"/>')
    parts.append("</svg>")
    rows = "".join(f'<td class="r">{t:g}</td>' for t, _ in points)
    vals = "".join(f'<td class="r">{v:.3f}</td>' for _, v in points)
    table = (f'<table class="small"><thead><tr><th>ms after burst</th>{rows}</tr></thead>'
             f'<tbody><tr><td>ticks / element</td>{vals}</tr></tbody></table>')
    return ('<figure>' + "".join(parts) +
            '<figcaption><b>Figure 2.</b> The identical 256-bit masked kernel runs at '
            f'{cold:.3f} ticks per element on a cool core, slows to about the 512-bit speed for roughly the first millisecond '
            'after 512-bit work, then recovers (later fluctuations are VM noise). Data from results/bench_output.txt:</figcaption>'
            + table + '</figure>')


# ---------------------------------------------------------------- listings
CMM_KEYWORDS = {"module", "fn", "main", "let", "mut", "if", "else", "while", "do", "for", "print", "true", "false",
                "return", "switch", "case", "default"}
CMM_TYPES = {"int", "float", "bool", "string", "array", "list", "stack", "queue"}
C_KEYWORDS = {"for", "if", "else", "return", "const", "void", "int", "float", "unsigned", "typedef", "struct", "static"}
TOKEN_RE = re.compile(r'(//[^\n]*|/\*[\s\S]*?\*/)|("(?:[^"\\\n]|\\.)*")|(\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[uUfF]?\b)|([A-Za-z_]\w*)')


def highlight(code: str, keywords: set[str], types: set[str]) -> str:
    out, last = [], 0
    for m in TOKEN_RE.finditer(code):
        out.append(esc(code[last:m.start()]))
        text = m.group(0)
        if m.group(1):
            out.append(f'<span class="c">{esc(text)}</span>')
        elif m.group(2):
            out.append(f'<span class="s">{esc(text)}</span>')
        elif m.group(3):
            out.append(f'<span class="n">{esc(text)}</span>')
        elif text in keywords:
            out.append(f'<span class="k">{esc(text)}</span>')
        elif text in types or text.startswith("__m"):
            out.append(f'<span class="t">{esc(text)}</span>')
        else:
            out.append(esc(text))
        last = m.end()
    out.append(esc(code[last:]))
    return "".join(out)


def extract_function(source: str, name: str) -> str:
    """Return the C function `name` including the attribute line above it."""
    m = re.search(r"(__attribute__\(\([^\n]*\)\)\n)?void " + re.escape(name) + r"\(", source)
    start = m.start()
    depth, i = 0, source.index("{", m.end())
    while True:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1


def kernels_listing() -> str:
    bench = (STUDY / "bench_avx512.c").read_text()
    blocks = [extract_function(bench, n) for n in ("avx512_masked", "avx512_max", "avx512vl_ymm")]
    avx2 = (STUDY / "avx2_blend.c").read_text()
    blocks.append("/* avx2_blend.c (compiled with -march=haswell) */\n" + extract_function(avx2, "avx2_blend"))
    return highlight("\n\n".join(blocks), C_KEYWORDS, {"__mmask16", "__mmask8"})


def cmm_output_parts() -> tuple[str, str]:
    lines = [("-" * 40 if set(l) == {"-"} else l)       # fit separators in the two-column layout
             for l in (STUDY / "results" / "cmm_output.txt").read_text().splitlines()]
    second = next(i for i, l in enumerate(lines) if l.startswith("Dataset 2"))
    part_a = lines[:second - 1]
    trace = next(i for i, l in enumerate(lines) if l.startswith("Lane trace"))
    part_b = lines[trace - 1:]
    return esc("\n".join(part_a)), esc("\n".join(part_b))


# ---------------------------------------------------------------- build
def find_chrome() -> str:
    candidates = [os.environ.get("CHROME", ""), "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
                  shutil.which("chromium") or "", shutil.which("chromium-browser") or "", shutil.which("google-chrome") or ""]
    candidates += sorted(str(p) for p in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("Chromium not found; set CHROME=/path/to/chrome")


INTER_VARIABLE = STUDY.parent.parent / "web" / "fonts" / "inter-latin-wght-normal.woff2"
INTER_SYSTEM = {400: "Inter-Regular.otf", 600: "Inter-SemiBold.otf", 700: "Inter-Bold.otf"}


def otf_to_ttf(src: Path, dst: Path) -> None:
    """Convert a CFF-flavoured OpenType font to TrueType outlines (fontTools cu2qu)."""
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTFont, newTable

    font = TTFont(str(src))
    glyph_set = font.getGlyphSet()
    glyphs = {}
    for name in font.getGlyphOrder():
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=1.0, reverse_direction=True))
        glyphs[name] = pen.glyph()
    font["loca"] = newTable("loca")
    font["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = font.getGlyphOrder()
    glyf.glyphs = glyphs
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]
    font["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    for attr in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs",
                 "maxStackElements", "maxSizeOfInstructions", "maxComponentElements"):
        setattr(maxp, attr, 0)
    maxp.maxZones = 1
    font["post"].formatType = 2.0
    font["post"].extraNames = []
    font["post"].mapping = {}
    font["head"].glyphDataFormat = 0
    font.sfntVersion = "\x00\x01\x00\x00"
    font.save(str(dst))


def find_system_inter() -> dict:
    found = {}
    for weight, name in INTER_SYSTEM.items():
        matches = sorted(Path("/usr/share/fonts").rglob(name)) if Path("/usr/share/fonts").exists() else []
        if matches:
            found[weight] = matches[0]
    return found if len(found) == len(INTER_SYSTEM) else {}


def inter_font_faces(tmp: Path) -> str:
    """@font-face rules for Inter as static TrueType fonts.

    Chromium embeds CFF and variable fonts as Type 3 glyphs. Converting the full
    system Inter (all symbols) to TrueType gives properly embedded text; without
    it, the website's Latin-subset variable font is used as a fallback.
    """
    rule = '  @font-face {{ font-family: "Inter Report"; font-style: normal; font-weight: {w}; src: url("{u}") format("{f}"); }}'
    try:
        system = find_system_inter()
        if system:
            rules = []
            for weight, src in system.items():
                dst = tmp / f"Inter-{weight}.ttf"
                otf_to_ttf(src, dst)
                rules.append(rule.format(w=weight, u=dst.as_uri(), f="truetype"))
            return "\n".join(rules)
    except ImportError:
        print("note: pip install fonttools for TrueType-embedded text", file=sys.stderr)
    return rule.format(w="100 900", u=INTER_VARIABLE.as_uri(), f="woff2")


def main() -> None:
    template = (HERE / "report.html").read_text()
    tmp_dir = tempfile.TemporaryDirectory()
    tmp = Path(tmp_dir.name)
    font_faces = inter_font_faces(tmp)
    out_a, out_b = cmm_output_parts()
    members = "".join(f'<tr><td>{esc(n)}</td><td class="reg">{esc(r)}</td></tr>' for n, r in MEMBERS)
    filled = (template
              .replace("{{MEMBERS}}", members)
              .replace("{{SUPERVISOR}}", SUPERVISOR)
              .replace("{{INSTITUTION}}", INSTITUTION)
              .replace("{{DATE}}", DATE)
              .replace("{{INTER_FONT_FACES}}", font_faces)
              .replace("{{FIG1}}", figure_bars())
              .replace("{{FIG2}}", figure_frequency())
              .replace("{{CMM_SOURCE}}", highlight((STUDY / "masked_sqrt.cmm").read_text().rstrip(), CMM_KEYWORDS, CMM_TYPES))
              .replace("{{CMM_OUTPUT_A}}", out_a)
              .replace("{{CMM_OUTPUT_B}}", out_b)
              .replace("{{KERNELS}}", kernels_listing()))
    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", filled)
    if leftover:
        sys.exit(f"unfilled placeholders: {leftover}")

    try:
        page = tmp / "report.html"
        page.write_text(filled, encoding="utf-8")
        subprocess.run([find_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT_PDF}", page.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        tmp_dir.cleanup()
    print(f"wrote {OUT_PDF.relative_to(STUDY.parent.parent)} ({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
