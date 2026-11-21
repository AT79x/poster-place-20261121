#!/usr/bin/env python3
"""VELDARIS -- a travel poster for a place that isn't there.

Entry for make.fun "The Poster for a Place That Isn't There"
(the-poster-for-a-place-that-i-2-20261121-0539).

Draws one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png using only the
Python 3.13 standard library. Deterministic: two runs write byte-identical
PNGs. No network, no fonts, no external files -- the lettering is a
hand-built stroke font drawn with the same rasterizer as the picture.

The place: VELDARIS, a cliff town above a still lagoon where the sky
falls in ribbons of green light and the Starlight Observatory keeps
watch -- a stone viaduct, a waterfall, a lantern boat and a lamplit
jetty below. One landmark (the observatory tower), one promise (a quiet
night under falling stars), the name set large across the bottom so
the eye travels name -> tower -> horizon. Every pixel is drawn by
this program from scratch; no external image is used.
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
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

HORIZON = 620
CREAM = (247, 235, 201)
GOLD = (255, 196, 107)
INK = (10, 17, 34)


def draw_sky():
    gradient_rows(0, HORIZON, [
        (0.00, (7, 11, 38)),
        (0.45, (20, 30, 76)),
        (0.75, (48, 58, 116)),
        (0.92, (122, 82, 116)),
        (1.00, (214, 128, 84)),
    ])


def draw_stars(rng):
    for _ in range(260):
        x = rng.uniform(10, W - 10)
        y = rng.uniform(8, 590)
        # keep the moon clear
        if math.hypot(x - 820, y - 150) < 95:
            continue
        r = rng.uniform(0.7, 2.4)
        bright = rng.uniform(0.35, 1.0)
        col = (255, 244, 214) if rng.random() < 0.7 else (190, 210, 255)
        soft_disc(x, y, r, col, bright)
        if r > 2.0 and rng.random() < 0.5:
            thick_line(x - 6, y, x + 6, y, 1.0, col, bright * 0.5)
            thick_line(x, y - 6, x, y + 6, 1.0, col, bright * 0.5)


def draw_moon():
    # glow, then a crescent carved by two overlapping circles
    soft_disc(820, 150, 110, (220, 205, 170), 0.20)
    soft_disc(820, 150, 78, (240, 228, 196), 0.12)
    cx, cy, r = 820, 150, 58
    ox, oy, r2 = 848, 132, 52
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d1 = (xx - cx) ** 2 + (yy - cy) ** 2
            d2 = (xx - ox) ** 2 + (yy - oy) ** 2
            if d1 <= r * r and d2 > r2 * r2:
                blend(xx, yy, (244, 234, 205), 1.0)
    # faint craters on the lit sliver
    soft_disc(806, 138, 7, (214, 200, 168), 0.5)
    soft_disc(812, 168, 5, (214, 200, 168), 0.5)


def draw_aurora(rng):
    # layered ribbons: bright cores, a soft halo and a violet fringe,
    # plus short vertical curtain streaks for texture
    ribbons = [
        (90, 52, 540, (70, 235, 185), 0.16, 34),
        (150, 60, 480, (110, 175, 255), 0.11, 38),
        (210, 46, 580, (95, 245, 205), 0.13, 26),
        (260, 58, 460, (150, 110, 235), 0.09, 30),
        (330, 40, 620, (60, 215, 165), 0.10, 20),
    ]
    for base, amp, wave, col, a, rad in ribbons:
        phase = rng.uniform(0, 6.28)
        x = 0.0
        while x < W:
            y = base + amp * math.sin((x / wave) * 6.28318 + phase)
            soft_disc(x, y, rad, col, a)
            # curtain streak: a short vertical wisp under the ribbon
            if int(x) % 27 == 0:
                thick_line(x, y, x + 4, y + rng.uniform(26, 52), 3.0, col, a * 0.55)
            x += 9.0


def draw_meteors():
    for (x0, y0, x1, y1) in [(180, 90, 300, 190), (620, 60, 720, 150)]:
        steps = 24
        for s in range(steps):
            t0 = s / steps
            t1 = (s + 1) / steps
            a = 0.85 * (1.0 - t0)
            thick_line(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0,
                       x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1,
                       2.2, (255, 246, 220), a)
        soft_disc(x0, y0, 4, (255, 250, 230), 0.9)


def draw_mountains_and_clouds(rng):
    # distant mountains on the right, under the sunset
    fill_poly([(560, HORIZON), (660, 548), (760, 590), (860, 540),
               (960, 596), (W, 560), (W, HORIZON)], (26, 34, 66))
    fill_poly([(700, HORIZON), (800, 566), (900, 600), (W, 570),
               (W, HORIZON)], (18, 24, 50))
    # snow on the far peaks
    for (px, py) in ((660, 548), (860, 540)):
        soft_disc(px, py, 14, (210, 200, 220), 0.35)
    # orange sunset clouds, low and slow
    for _ in range(46):
        x = rng.uniform(620, W - 10)
        y = rng.uniform(430, 600)
        r = rng.uniform(18, 55)
        col = rng.choice([(255, 150, 90), (255, 120, 110), (250, 180, 120)])
        soft_disc(x, y, r, col, rng.uniform(0.05, 0.12))
    # a few high violet wisps on the left
    for _ in range(12):
        x = rng.uniform(0, 420)
        y = rng.uniform(180, 300)
        soft_disc(x, y, rng.uniform(20, 44), (150, 110, 200), rng.uniform(0.04, 0.08))


def draw_sea():
    gradient_rows(HORIZON, H - 1, [
        (0.00, (150, 112, 86)),
        (0.12, (72, 74, 84)),
        (0.40, (20, 48, 66)),
        (1.00, (8, 26, 40)),
    ])
    rng = random.Random(SEED + 7)
    # moonlight column under the moon
    for _ in range(70):
        x = 820 + rng.uniform(-46, 46)
        y = HORIZON + rng.uniform(4, 190)
        ln = rng.uniform(8, 42)
        a = rng.uniform(0.10, 0.30) * (1.0 - (y - HORIZON) / 220.0)
        thick_line(x, y, x + ln, y, 2.0, (240, 210, 160), max(0.0, a))
    # warm shimmer in the open water, where the town lights reach
    for _ in range(50):
        x = rng.uniform(480, 760)
        y = HORIZON + rng.uniform(4, 150)
        ln = rng.uniform(6, 30)
        a = rng.uniform(0.08, 0.26) * (1.0 - (y - HORIZON) / 180.0)
        thick_line(x, y, x + ln, y, 2.0, GOLD, max(0.0, a))


CLIFF = [(0, H), (0, 760), (60, 700), (150, 620), (230, 545),
         (320, 505), (400, 540), (455, 600), (480, 700), (525, H)]


def draw_cliff():
    fill_poly(CLIFF, (10, 17, 34))
    # rock facets: slightly different dark tones catch the dusk light
    fill_poly([(60, 700), (150, 620), (230, 545), (200, 640), (120, 720)],
              (16, 26, 50), 0.8)
    fill_poly([(320, 505), (400, 540), (455, 600), (380, 620), (340, 560)],
              (14, 22, 44), 0.8)
    fill_poly([(0, 760), (60, 700), (120, 760), (40, 860), (0, 900)],
              (8, 13, 28), 0.8)
    # cracks down the face
    for (x0, y0, x1, y1) in [(180, 640, 220, 720), (340, 560, 380, 660),
                             (90, 720, 140, 800)]:
        thick_line(x0, y0, x1, y1, 2.0, (6, 10, 22), 0.9)
    # tiny lit windows carved into the cliff face
    for (wx, wy) in [(70, 722), (110, 690), (160, 650), (200, 610),
                     (250, 575), (300, 535), (340, 545), (380, 570),
                     (420, 600), (450, 640), (90, 760), (140, 720),
                     (220, 660), (280, 600), (360, 600), (410, 640)]:
        soft_disc(wx + 2, wy + 2, 5, GOLD, 0.35)
        rect(wx, wy, 4, 5, GOLD)
    # faint rim light along the top edge
    rim = [(0, 760), (60, 700), (150, 620), (230, 545),
           (320, 505), (400, 540), (455, 600), (480, 700)]
    for (x0, y0), (x1, y1) in zip(rim, rim[1:]):
        thick_line(x0, y0, x1, y1, 3.0, (38, 56, 92), 0.8)


def draw_bridge():
    # a stone viaduct leaves the cliff toward the far rock
    deck = [(470, 600), (560, 590), (660, 582), (780, 578)]
    for (x0, y0), (x1, y1) in zip(deck, deck[1:]):
        thick_line(x0, y0, x1, y1, 7.0, (40, 54, 92), 1.0)
        thick_line(x0, y0 - 3, x1, y1 - 3, 2.0, (74, 96, 140), 0.8)
    # solid arches under the deck, rim-lit so they read against the
    # dark mountains behind them
    for (ax, ay, ar) in ((540, 596, 34), (650, 586, 40), (730, 580, 26)):
        prev = None
        for s in range(25):
            t = s / 24.0
            px = ax + math.cos(math.pi * t) * ar
            py = ay + math.sin(math.pi * t) * ar * 0.8
            if prev is not None:
                thick_line(prev[0], prev[1], px, py, 5.0, (56, 72, 112), 0.95)
            prev = (px, py)
    # lamps along the deck
    for (lx, ly) in ((520, 592), (600, 586), (680, 580), (740, 578)):
        soft_disc(lx, ly - 6, 8, GOLD, 0.5)
        disc(lx, ly - 6, 2, GOLD)


def draw_waterfall(rng):
    # a fall from a sea-stack rock into the misty lagoon
    fill_poly([(862, 640), (918, 638), (912, 712), (868, 712)], (22, 30, 56))
    for _ in range(14):
        x = rng.uniform(874, 904)
        y0 = rng.uniform(664, 680)
        y1 = rng.uniform(760, 800)
        thick_line(x, y0, x + rng.uniform(-2, 2), y1,
                   rng.uniform(1.5, 3.5), (215, 230, 245),
                   rng.uniform(0.18, 0.38))
    soft_disc(888, 782, 34, (200, 215, 235), 0.18)
    soft_disc(888, 796, 48, (200, 215, 235), 0.20)
    soft_disc(872, 806, 40, (190, 205, 230), 0.14)
    soft_disc(906, 806, 40, (190, 205, 230), 0.14)


def draw_town(rng):
    # terraced houses on the cliff face; each has warm lit windows
    terraces = [
        (560, 200, 400, 9),
        (600, 130, 440, 11),
        (650, 70, 460, 12),
        (700, 30, 470, 8),
    ]
    for (ty, xa, xb, count) in terraces:
        for _ in range(count):
            x = rng.uniform(xa, xb)
            y = ty + rng.uniform(-8, 8)
            w = rng.uniform(16, 30)
            h = rng.uniform(12, 20)
            rect(int(x), int(y - h), int(w), int(h), (13, 22, 44))
            # pitched roof
            fill_poly([(int(x) - 2, int(y - h)),
                       (int(x + w / 2), int(y - h - 7)),
                       (int(x + w + 2), int(y - h))], (9, 15, 30))
            for _ in range(rng.randint(1, 3)):
                wx = int(x + rng.uniform(3, max(4, w - 7)))
                wy = int(y - h + rng.uniform(3, max(4, h - 8)))
                soft_disc(wx + 2, wy + 2, 5, GOLD, 0.35)
                rect(wx, wy, 4, 5, GOLD)
    # a lower terrace of bigger houses along the cliff base
    for _ in range(9):
        x = rng.uniform(50, 420)
        y = 730 + rng.uniform(-10, 10)
        w = rng.uniform(24, 40)
        h = rng.uniform(16, 26)
        rect(int(x), int(y - h), int(w), int(h), (15, 24, 48))
        fill_poly([(int(x) - 2, int(y - h)),
                   (int(x + w / 2), int(y - h - 9)),
                   (int(x + w + 2), int(y - h))], (10, 17, 34))
        rect(int(x + w - 9), int(y - h - 8), 5, 9, (12, 20, 40))
        for _ in range(rng.randint(2, 4)):
            wx = int(x + rng.uniform(3, max(4, w - 7)))
            wy = int(y - h + rng.uniform(3, max(4, h - 8)))
            soft_disc(wx + 2, wy + 2, 5, GOLD, 0.35)
            rect(wx, wy, 4, 5, GOLD)
    # a slender bell tower on the cliff shoulder
    fill_poly([(418, 562), (438, 562), (434, 442), (422, 442)], (14, 23, 46))
    fill_poly([(416, 442), (440, 442), (428, 402)], (10, 16, 32))
    rect(422, 458, 5, 10, GOLD)
    rect(429, 458, 5, 10, GOLD)
    soft_disc(428, 398, 10, GOLD, 0.6)
    disc(428, 398, 3, GOLD)


def draw_tower():
    # The Starlight Observatory on the cliff peak -- the one landmark.
    # glow where the beam leaves the dome
    soft_disc(330, 318, 62, (190, 220, 255), 0.10)
    # light beam rising from the dome
    fill_poly([(318, 318), (342, 318), (398, 40), (262, 40)],
              (190, 220, 255), 0.10)
    fill_poly([(322, 318), (338, 318), (372, 60), (288, 60)],
              (200, 228, 255), 0.08)
    # shaft, slightly tapered, on a stone terrace
    fill_poly([(314, 505), (346, 505), (340, 336), (320, 336)], (12, 20, 40))
    rect(296, 498, 68, 8, (18, 28, 56))
    rect(292, 506, 76, 6, (14, 22, 46))
    # balcony ring
    rect(312, 330, 36, 8, (16, 26, 52))
    # dome
    disc(330, 322, 27, (16, 26, 52))
    rect(303, 322, 54, 6, (16, 26, 52))
    # dome ribs fanning from the crown
    for ang in (-0.9, -0.45, 0.0, 0.45, 0.9):
        thick_line(330, 296, 330 + math.sin(ang) * 24, 322, 1.5,
                   (30, 44, 78), 0.8)
    # lit slit windows on the dome
    rect(324, 306, 4, 18, GOLD)
    rect(334, 304, 4, 20, GOLD)
    # drum under the dome, ringed with lit windows
    rect(306, 328, 48, 12, (16, 26, 52))
    for wx in (310, 320, 330, 340, 350):
        rect(wx, 331, 4, 7, GOLD)
    # spire + beacon star
    thick_line(330, 296, 330, 268, 3.0, (16, 26, 52))
    soft_disc(330, 262, 16, (255, 233, 168), 0.7)
    disc(330, 262, 5, (255, 240, 190))
    thick_line(322, 262, 338, 262, 2.0, (255, 240, 190), 0.9)
    thick_line(330, 254, 330, 270, 2.0, (255, 240, 190), 0.9)


def draw_boat():
    # a two-sail lantern boat on the lagoon, for scale and for the
    # promise of a quiet evening afloat
    # reflection under the hull
    for yy, a in ((736, 0.28), (748, 0.18), (762, 0.10), (776, 0.06)):
        thick_line(668, yy, 748, yy, 2.5, GOLD, a)
    # hull
    fill_poly([(648, 700), (772, 700), (752, 722), (668, 722)], (10, 16, 30))
    fill_poly([(648, 700), (772, 700), (766, 706), (654, 706)], (30, 22, 16))
    # mast
    thick_line(712, 700, 712, 596, 3.5, (46, 38, 28))
    # main sail, warm from the town lights
    fill_poly([(716, 604), (716, 696), (766, 696)], (238, 226, 198))
    fill_poly([(716, 604), (716, 696), (766, 696)], (255, 200, 120), 0.18)
    # jib
    fill_poly([(708, 612), (708, 696), (664, 696)], (228, 216, 190))
    # cabin with lit windows, and a stern lantern
    rect(700, 688, 22, 12, (14, 20, 36))
    rect(704, 691, 4, 6, GOLD)
    rect(714, 691, 4, 6, GOLD)
    soft_disc(724, 686, 10, GOLD, 0.6)
    disc(724, 686, 3, (255, 210, 130))


def draw_foreground():
    fill_poly([(0, H), (0, 950), (90, 920), (150, 960), (120, H)],
              (7, 12, 26))
    fill_poly([(W, H), (W, 958), (950, 928), (890, 968), (920, H)],
              (7, 12, 26))
    # two pines on the left rock
    for (px, py, s) in ((52, 940, 1.0), (88, 952, 0.7)):
        fill_poly([(px, py - 58 * s), (px - 16 * s, py), (px + 16 * s, py)],
                  (6, 11, 24))
        fill_poly([(px, py - 78 * s), (px - 11 * s, py - 28 * s),
                   (px + 11 * s, py - 28 * s)], (6, 11, 24))


def draw_reflections(rng):
    # gold shimmer where the town lights meet the lagoon, in front of
    # the cliff base, plus a few wave strokes across the open water
    for _ in range(70):
        x = rng.uniform(480, 780)
        y = rng.uniform(HORIZON + 130, H - 40)
        ln = rng.uniform(8, 44)
        a = rng.uniform(0.08, 0.26) * (1.0 - (y - HORIZON) / 420.0)
        thick_line(x, y, x + ln, y, 2.0, GOLD, max(0.0, a))
    for _ in range(90):
        x = rng.uniform(530, W - 10)
        y = rng.uniform(HORIZON + 6, H - 20)
        ln = rng.uniform(14, 70)
        col = (140, 170, 200) if rng.random() < 0.5 else (10, 22, 38)
        thick_line(x, y, x + ln, y, 1.5, col, rng.uniform(0.10, 0.28))


def draw_dock():
    # wooden jetty in the lower-left corner, with a lit lantern
    # (clear of the name, which starts at x ~120)
    for i, px in enumerate(range(0, 120, 26)):
        rect(px, 956 + (i % 2) * 3, 24, 10, (44, 32, 22))
    for px in (8, 62, 106):
        rect(px, 946, 8, 40, (36, 26, 18))
    # lantern post
    thick_line(70, 956, 70, 862, 4.0, (30, 22, 16))
    soft_disc(70, 850, 38, (255, 190, 100), 0.40)
    rect(59, 834, 22, 30, (20, 14, 10))
    rect(63, 840, 14, 16, (255, 205, 120))
    thick_line(57, 834, 81, 834, 2.0, (20, 14, 10))
    # barrels on the jetty
    for (bx, by) in ((12, 930), (38, 936)):
        rect(bx, by, 22, 26, (52, 38, 24))
        thick_line(bx, by + 8, bx + 22, by + 8, 2.0, (30, 22, 14), 0.8)
        thick_line(bx, by + 18, bx + 22, by + 18, 2.0, (30, 22, 14), 0.8)


def draw_branches(rng):
    # dark branches framing the top-left corner
    col = (8, 12, 26)
    thick_line(0, 40, 120, 90, 7.0, col, 0.95)
    thick_line(60, 60, 150, 30, 5.0, col, 0.95)
    thick_line(40, 70, 90, 150, 5.0, col, 0.95)
    thick_line(120, 90, 190, 70, 4.0, col, 0.9)
    for _ in range(36):
        t = rng.uniform(0, 1)
        bx = t * 190
        by = 40 + t * 60 + rng.uniform(-24, 24)
        soft_disc(bx, by, rng.uniform(6, 13), (10, 18, 30), 0.9)


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
    text = "VELDARIS"
    scale = 9.0
    cap = 14 * scale
    width = 8 * 11.0 * scale - scale
    x0 = (W - width) / 2.0
    y0 = 830.0
    # divider rule with a four-point star, above the name
    thick_line(300, 800, 486, 800, 2.0, CREAM, 0.75)
    thick_line(538, 800, 724, 800, 2.0, CREAM, 0.75)
    fill_poly([(512, 786), (516, 796), (526, 800), (516, 804),
               (512, 814), (508, 804), (498, 800), (508, 796)], GOLD, 0.95)
    # soft shadow, then the name itself in gold
    draw_text(text, x0 + 5, y0 + 6, scale, (8, 13, 30), 0.6, 2.4)
    draw_text(text, x0, y0, scale, (255, 204, 118), 1.0, 2.4)


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
    draw_aurora(rng)
    draw_stars(rng)
    draw_moon()
    draw_meteors()
    draw_mountains_and_clouds(rng)
    draw_sea()
    draw_cliff()
    draw_bridge()
    draw_waterfall(rng)
    draw_town(rng)
    draw_tower()
    draw_boat()
    draw_reflections(rng)
    draw_foreground()
    draw_dock()
    draw_branches(rng)
    draw_name()
    os.makedirs(OUT_DIR, exist_ok=True)
    data = png_bytes()
    path = os.path.join(OUT_DIR, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
