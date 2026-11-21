#!/usr/bin/env python3
"""VELDARIS -- a travel poster for a place that isn't there.

Entry for make.fun "The Poster for a Place That Isn't There"
(the-poster-for-a-place-that-i-2-20261121-0539).

Draws one 1024x1536 (2:3 portrait) PNG to $MAKEFUN_OUTPUT_DIR/entry.png
using only the Python 3.13 standard library. Deterministic: two runs
write byte-identical PNGs. No network, no fonts, no external files --
the lettering is a hand-built stroke font drawn with the same
rasterizer as the picture.

Layout v3 (21 Nov 2026, from AT's second reference -- flat vector
minimalist, same concept, new graphic layout): a deep-navy night sky
with smooth teal aurora ribbons, a crescent moon and two meteors; the
Starlight Observatory on a hilltop sends one clean beam up into the
aurora; a row of flat houses with warm lit windows steps down the
hill to a slatted pier at the shoreline; below, a still lagoon carries
a cream-sailed boat, a wooden jetty with a lantern, and a column of
gold reflection dashes; the name VELDARIS is set large in thin gold
line letters at the bottom, with a small star and divider rules,
inside a hairline frame. Every pixel is drawn by this program from
scratch; no external image is used -- the reference was only looked
at for composition, palette and mood.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1536
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
SEED = 20261121

# ---------------------------------------------------------------- canvas

img = bytearray(W * H * 3)


def _i(x, y):
    return (y * W + x) * 3


def blend(x, y, col, a):
    """Blend colour (r, g, b) over pixel (x, y) with opacity a (0..1)."""
    if a <= 0.0 or x < 0 or x >= W or y < 0 or y >= H:
        return
    i = _i(x, y)
    if a >= 1.0:
        img[i] = col[0]
        img[i + 1] = col[1]
        img[i + 2] = col[2]
        return
    inv = 1.0 - a
    img[i] = int(img[i] * inv + col[0] * a + 0.5)
    img[i + 1] = int(img[i + 1] * inv + col[1] * a + 0.5)
    img[i + 2] = int(img[i + 2] * inv + col[2] * a + 0.5)


def fill_row(y, col):
    img[y * W * 3:(y + 1) * W * 3] = bytes(col) * W


def lerp_col(c0, c1, t):
    return (int(c0[0] + (c1[0] - c0[0]) * t + 0.5),
            int(c0[1] + (c1[1] - c0[1]) * t + 0.5),
            int(c0[2] + (c1[2] - c0[2]) * t + 0.5))


def gradient_rows(y0, y1, stops):
    """Fill rows y0..y1 with a vertical gradient through (pos, colour)."""
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, y1 - y0)
        for k in range(len(stops) - 1):
            p0, c0 = stops[k]
            p1, c1 = stops[k + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                fill_row(y, lerp_col(c0, c1, f))
                break


def soft_disc(cx, cy, rad, col, a):
    """A disc with a smooth (quadratic) falloff edge."""
    r = int(rad) + 1
    x0 = max(0, int(cx) - r)
    x1 = min(W - 1, int(cx) + r)
    y0 = max(0, int(cy) - r)
    y1 = min(H - 1, int(cy) + r)
    rr = rad * rad
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        for xx in range(x0, x1 + 1):
            dx = xx - cx
            d2 = (dx * dx + dy * dy) / rr
            if d2 < 1.0:
                w = (1.0 - d2)
                blend(xx, yy, col, a * w * w)


def disc(cx, cy, rad, col, a=1.0):
    r = int(rad) + 1
    x0 = max(0, int(cx) - r)
    x1 = min(W - 1, int(cx) + r)
    y0 = max(0, int(cy) - r)
    y1 = min(H - 1, int(cy) + r)
    rr = rad * rad
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        for xx in range(x0, x1 + 1):
            dx = xx - cx
            if dx * dx + dy * dy <= rr:
                blend(xx, yy, col, a)


def thick_line(x0, y0, x1, y1, width, col, a=1.0):
    """A line with round caps, drawn as a chain of soft discs."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    steps = max(1, int(length))
    rad = width / 2.0
    for s in range(steps + 1):
        t = s / steps
        soft_disc(x0 + dx * t, y0 + dy * t, rad, col, a)


def fill_poly(points, col, a=1.0):
    """Scanline polygon fill."""
    ys = [p[1] for p in points]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(H - 1, int(math.ceil(max(ys))))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x0, y0p = points[k]
            x1, y1p = points[(k + 1) % n]
            if (y0p <= y < y1p) or (y1p <= y < y0p):
                t = (y - y0p) / (y1p - y0p)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(math.ceil(xs[k])))
            xb = min(W - 1, int(math.floor(xs[k + 1])))
            for x in range(xa, xb + 1):
                blend(x, y, col, a)


def rect(x, y, w, h, col, a=1.0):
    for yy in range(max(0, y), min(H, y + h)):
        for xx in range(max(0, x), min(W, x + w)):
            blend(xx, yy, col, a)


# ---------------------------------------------------------------- scene

WATERLINE = 860
CREAM = (247, 235, 201)
GOLD = (255, 196, 107)
PALE_GOLD = (242, 216, 160)
INK = (10, 17, 34)


def draw_sky():
    gradient_rows(0, WATERLINE, [
        (0.00, (7, 10, 36)),
        (0.50, (14, 22, 58)),
        (0.85, (24, 30, 74)),
        (1.00, (36, 38, 88)),
    ])


def draw_stars(rng):
    for _ in range(170):
        x = rng.uniform(30, W - 30)
        y = rng.uniform(30, 820)
        # keep the moon clear
        if math.hypot(x - 828, y - 178) < 95:
            continue
        r = rng.uniform(0.7, 1.8)
        bright = rng.uniform(0.30, 0.85)
        col = (255, 244, 214) if rng.random() < 0.7 else (190, 210, 255)
        soft_disc(x, y, r, col, bright)


def draw_aurora():
    # smooth flat ribbons: a soft halo pass, then a brighter core,
    # each following a slow sine wave across the top of the sky
    ribbons = [
        (120, 34, 430, 0.6, 20, (16, 190, 180), 0.60),
        (165, 40, 520, 2.1, 24, (40, 120, 225), 0.52),
        (205, 30, 380, 4.0, 16, (30, 200, 165), 0.48),
        (250, 38, 470, 1.2, 22, (60, 150, 235), 0.42),
        (295, 26, 340, 5.3, 14, (20, 180, 190), 0.38),
    ]
    for base, amp, wave, phase, width, col, a in ribbons:
        pts = []
        x = -20.0
        while x <= W + 20:
            pts.append((x, base + amp * math.sin((x / wave) * 6.28318 + phase)))
            x += 20.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            thick_line(x0, y0, x1, y1, width * 2.2, col, a * 0.30)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            thick_line(x0, y0, x1, y1, width, col, a)


def draw_moon():
    # glow, then a crescent carved by two overlapping circles
    soft_disc(828, 178, 110, (220, 205, 170), 0.20)
    soft_disc(828, 178, 78, (240, 228, 196), 0.12)
    cx, cy, r = 828, 178, 58
    ox, oy, r2 = 858, 156, 52
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d1 = (xx - cx) ** 2 + (yy - cy) ** 2
            d2 = (xx - ox) ** 2 + (yy - oy) ** 2
            if d1 <= r * r and d2 > r2 * r2:
                blend(xx, yy, (242, 224, 178), 1.0)


def draw_meteors():
    for (x0, y0, x1, y1) in [(200, 240, 320, 330), (700, 300, 820, 395)]:
        steps = 24
        for s in range(steps):
            t0 = s / steps
            t1 = (s + 1) / steps
            a = 0.85 * (1.0 - t0)
            thick_line(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0,
                       x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1,
                       2.5, (255, 246, 220), a)
        soft_disc(x0, y0, 4, (255, 250, 230), 0.9)


# hill surface, defined by control points and linear interpolation
_HILL = [(0, 720), (120, 660), (260, 580), (380, 545), (470, 560),
         (580, 650), (680, 760), (760, 820), (840, 850), (900, 858),
         (1024, 860)]


def hill_y(x):
    for (x0, y0), (x1, y1) in zip(_HILL, _HILL[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return _HILL[-1][1]


def draw_ridge():
    # a distant mountain on the far right, behind the main hill
    fill_poly([(700, WATERLINE), (820, 745), (940, 790), (W, 750),
               (W, WATERLINE)], (18, 26, 52))


def draw_hill():
    pts = [(x, hill_y(x)) for x in range(0, W + 1, 32)]
    fill_poly(pts + [(W, WATERLINE), (0, WATERLINE)], (13, 19, 40))
    # one faint rim-light line along the top edge so the hill reads
    # against the sky
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        thick_line(x0, y0, x1, y1, 2.0, (30, 40, 70), 0.35)


def draw_sea():
    gradient_rows(WATERLINE, H - 1, [
        (0.00, (16, 34, 66)),
        (0.50, (11, 24, 50)),
        (1.00, (8, 18, 40)),
    ])


def draw_beam():
    # one clean beam from the observatory dome up into the aurora
    thick_line(300, 440, 520, 110, 12.0, (90, 220, 215), 0.22)
    thick_line(300, 440, 520, 110, 5.0, (110, 230, 220), 0.80)


def draw_observatory():
    # small and flat: a trapezoid tower, a light dome, three lit
    # windows -- the one landmark, kept quiet on the hilltop
    fill_poly([(280, 575), (320, 575), (310, 472), (290, 472)], (20, 28, 54))
    disc(300, 464, 26, (100, 120, 150))
    rect(272, 464, 56, 7, (16, 24, 48))
    for wx in (289, 297, 305):
        rect(wx, 498, 6, 14, GOLD)
    disc(300, 436, 3, (200, 225, 255))


def _windows(rng, x, y, w, h):
    cols = 4 if w >= 64 else 3
    rows = 4 if h >= 80 else 3
    for r in range(rows):
        wy = int(y + 9 + r * (h - 18) / max(1, rows - 1))
        for c in range(cols):
            wx = int(x + 8 + c * (w - 21) / max(1, cols - 1))
            if rng.random() < 0.22:
                rect(wx, wy, 5, 7, (10, 14, 26))  # unlit window
            else:
                soft_disc(wx + 2, wy + 3, 5, GOLD, 0.30)
                rect(wx, wy, 5, 7, GOLD)


def draw_town(rng):
    # a stepped row of flat houses descending the hill to the shore;
    # each has a dark maroon pitched roof and a grid of warm windows.
    # The row leaves a gap around the observatory (x ~274-326) so the
    # dome is never hidden behind a roof.
    houses = [(30, 66, 86), (104, 70, 90), (182, 66, 82),
              (360, 68, 88), (428, 62, 80), (492, 58, 74), (554, 54, 68),
              (612, 50, 62), (664, 46, 56), (712, 44, 50)]
    for (x, w, h) in houses:
        base = int(hill_y(x + w / 2) + 6)
        rect(x, base - h, w, h, (18, 26, 50))
        fill_poly([(x - 3, base - h), (x + w // 2, base - h - 16),
                   (x + w + 3, base - h)], (58, 32, 36))
        _windows(rng, x, base - h, w, h)


def draw_bridge():
    # a slatted pier at the shoreline, where the hill meets the water
    thick_line(820, 858, 985, 858, 5.0, (120, 90, 60), 1.0)
    for x in range(826, 980, 9):
        thick_line(x, 860, x, 906, 2.0, (96, 72, 48), 0.9)
    for px in (830, 975):
        thick_line(px, 858, px, 894, 4.0, (80, 60, 40), 1.0)


def draw_reflections(rng):
    # scattered dashes across the lagoon, plus one column of gold
    # dashes widening downward under the middle of the sky
    for _ in range(240):
        x = rng.uniform(30, W - 30)
        y = rng.uniform(WATERLINE + 20, H - 40)
        ln = rng.uniform(8, 60)
        col = rng.choice([(255, 200, 120), (120, 180, 200),
                          (200, 220, 240), (140, 170, 200)])
        thick_line(x, y, x + ln, y, 2.0, col, rng.uniform(0.08, 0.28))
    y = WATERLINE + 25
    while y < 1250:
        half = 25 + (y - WATERLINE) * 0.35
        for _ in range(rng.randint(1, 2)):
            cx = 560 + rng.uniform(-half, half)
            ln = rng.uniform(16, 60)
            a = rng.uniform(0.20, 0.40) * (1.0 - (y - WATERLINE) / 480.0)
            thick_line(cx - ln / 2, y, cx + ln / 2, y, 2.0, GOLD,
                       max(0.0, a))
        y += 14


def draw_boat():
    # a cream-sailed boat at anchor, right of centre
    for yy, a in ((1240, 0.18), (1256, 0.12), (1272, 0.07)):
        thick_line(660, yy, 840, yy, 2.5, GOLD, a)
    fill_poly([(628, 1182), (872, 1182), (842, 1228), (658, 1228)],
              (42, 32, 26))
    thick_line(628, 1182, 872, 1182, 3.0, (150, 115, 70), 0.9)
    thick_line(712, 955, 712, 1182, 4.0, (30, 24, 20))
    fill_poly([(717, 962), (717, 1172), (802, 1172)], (238, 228, 198))
    fill_poly([(707, 982), (707, 1172), (638, 1172)], (226, 214, 182))
    rect(700, 1166, 26, 14, (16, 22, 38))
    rect(708, 1169, 5, 7, GOLD)


def draw_dock():
    # a wooden jetty in the lower-left corner, with a lit lantern
    # on a post -- clear of the name, which starts at x ~229
    for (y0, y1) in ((1320, 1295), (1347, 1322), (1374, 1349)):
        thick_line(0, y0, 250, y1, 5.0, (110, 80, 50), 1.0)
    for px in range(12, 250, 28):
        t = px / 250.0
        y = 1347 - t * 25
        rect(px, int(y) - 8, 7, 55, (80, 58, 36))
    thick_line(92, 1320, 92, 1240, 4.0, (30, 22, 16))
    soft_disc(92, 1228, 42, (255, 190, 100), 0.35)
    rect(80, 1212, 24, 30, (20, 14, 10))
    rect(84, 1218, 16, 18, (255, 205, 120))
    thick_line(80, 1212, 104, 1212, 2.0, (20, 14, 10))


def draw_frame():
    col = (160, 145, 100)
    thick_line(26, 26, W - 26, 26, 2.0, col, 0.5)
    thick_line(26, H - 26, W - 26, H - 26, 2.0, col, 0.5)
    thick_line(26, 26, 26, H - 26, 2.0, col, 0.5)
    thick_line(W - 26, 26, W - 26, H - 26, 2.0, col, 0.5)


# ---------------------------------------------------------------- lettering

# Stroke font on a 10 x 14 grid: each glyph is a list of polylines.
GLYPHS = {
    "V": [[(0, 0), (5, 14), (10, 0)]],
    "E": [[(10, 0), (0, 0), (0, 14), (10, 14)], [(0, 7), (7, 7)]],
    "L": [[(0, 0), (0, 14), (10, 14)]],
    "D": [[(0, 0), (0, 14), (7, 14), (10, 11), (10, 3), (7, 0), (0, 0)]],
    "A": [[(0, 14), (5, 0), (10, 14)], [(2.8, 8.4), (7.2, 8.4)]],
    "R": [[(0, 0), (0, 14)],
          [(0, 0), (6, 0), (9.5, 2.5), (9.5, 5.5), (6, 8), (0, 8)],
          [(5.5, 7.5), (10, 14)]],
    "I": [[(2, 0), (8, 0)], [(5, 0), (5, 14)], [(2, 14), (8, 14)]],
    "S": [[(9, 2.5), (7, 0), (3, 0), (1, 2), (1, 5), (3, 7),
           (8, 7), (10, 9), (10, 12), (8, 14), (4, 14), (1, 11.5)]],
}


def draw_text(text, x0, y0, scale, col, a=1.0, width_units=1.7):
    """Draw text with the stroke font; returns the width used."""
    x = x0
    adv = 11.0 * scale
    for ch in text:
        for poly in GLYPHS[ch]:
            pts = [(x + px * scale, y0 + py * scale) for (px, py) in poly]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                thick_line(ax, ay, bx, by, width_units * scale, col, a)
        x += adv
    return x - x0 - scale  # width without the trailing advance


def draw_name():
    # thin gold line letters, as in the reference -- no shadow, no
    # bold stroke; a small asterisk with divider rules below
    text = "VELDARIS"
    scale = 6.5
    width = 8 * 11.0 * scale - scale
    x0 = (W - width) / 2.0
    y0 = 1385.0
    draw_text(text, x0, y0, scale, PALE_GOLD, 1.0, 0.8)
    thick_line(250, 1502, 470, 1502, 1.5, PALE_GOLD, 0.6)
    thick_line(554, 1502, 774, 1502, 1.5, PALE_GOLD, 0.6)
    cx, cy = 512, 1502
    for ang in (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4):
        dx = math.cos(ang) * 9
        dy = math.sin(ang) * 9
        thick_line(cx - dx, cy - dy, cx + dx, cy + dy, 1.8, PALE_GOLD, 0.9)


# ---------------------------------------------------------------- PNG output

def png_bytes():
    raw = bytearray()
    for y in range(H):
        row = img[y * W * 3:(y + 1) * W * 3]
        filt = bytearray(len(row))
        for i in range(len(row)):
            left = row[i - 3] if i >= 3 else 0
            filt[i] = (row[i] - left) & 0xFF
        raw.append(1)  # Sub filter
        raw += filt

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    rng = random.Random(SEED)
    draw_sky()
    draw_stars(rng)
    draw_aurora()
    draw_moon()
    draw_meteors()
    draw_ridge()
    draw_hill()
    draw_sea()
    draw_beam()
    draw_observatory()
    draw_town(rng)
    draw_bridge()
    draw_reflections(rng)
    draw_boat()
    draw_dock()
    draw_frame()
    draw_name()
    os.makedirs(OUT_DIR, exist_ok=True)
    data = png_bytes()
    path = os.path.join(OUT_DIR, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
