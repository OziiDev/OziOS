#!/usr/bin/env python3
"""Write the OziOS wallpapers (branding/wallpapers/*.svg): flat, anime-style
scenes drawn from shapes, so they are our own work and scale to any screen.

    python3 tools/make-wallpapers.py

The output is deterministic (fixed random seeds); a test checks the files in
the repository match it.
"""
import math
import os
import random

W, H = 1920, 1080
HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "..", "branding", "wallpapers")


def svg(body, defs=""):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n'
        "<defs>%s</defs>\n%s\n</svg>\n" % (W, H, W, H, defs, body)
    )


def gradient(gid, stops, vertical=True, x1=0, y1=0, x2=0, y2=1):
    if not vertical:
        x2, y2 = 1, 0
    parts = "".join('<stop offset="%s" stop-color="%s"/>' % (o, c) for o, c in stops)
    return '<linearGradient id="%s" x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>' % (gid, x1, y1, x2, y2, parts)


def radial(gid, stops, cx=0.5, cy=0.5, r=0.5):
    parts = "".join('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % s for s in stops)
    return '<radialGradient id="%s" cx="%s" cy="%s" r="%s">%s</radialGradient>' % (gid, cx, cy, r, parts)


def stars(rng, n, top=0.0, bottom=0.6, color="#ffffff"):
    out = []
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(H * top, H * bottom)
        r = rng.choice((0.8, 1.0, 1.3, 1.8, 2.4))
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"/>' % (x, y, r, color, rng.uniform(0.3, 0.95)))
    return "".join(out)


def ridge(rng, base, height, rough, color, step=40, opacity=1.0):
    """A mountain or hill line across the screen, filled down to the bottom."""
    pts = []
    y = base
    for x in range(-step, W + 2 * step, step):
        y = max(base - height, min(base + height * 0.3, y + rng.uniform(-rough, rough)))
        pts.append("%d,%.1f" % (x, y))
    return '<polygon points="%s %d,%d %d,%d" fill="%s" opacity="%.2f"/>' % (" ".join(pts), W + 2 * step, H, -step, H, color, opacity)


def cloud(cx, cy, scale, color, opacity):
    blobs = [(0, 0, 60), (55, -25, 70), (120, -5, 58), (175, 10, 45), (-55, 12, 45), (60, 20, 60)]
    return "".join(
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"/>' % (cx + dx * scale, cy + dy * scale, r * scale, color, opacity)
        for dx, dy, r in blobs
    )


def night_city():
    rng = random.Random(1)
    defs = gradient("sky", [(0, "#0B0820"), (0.55, "#2A1650"), (1, "#6B2D6E")])
    defs += radial("moon", [(0, "#FFF3FB", 1), (0.35, "#FFD6F2", 0.55), (1, "#FF8BD0", 0)])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += stars(rng, 180, 0, 0.55)
    body += '<circle cx="1450" cy="260" r="330" fill="url(#moon)"/><circle cx="1450" cy="260" r="110" fill="#FFF6FC"/>'
    # Three layers of buildings, far to near, with lit windows.
    for layer, (color, lo, hi, win) in enumerate((("#2B1B4F", 380, 620, "#7C5CFF"), ("#1C1238", 460, 760, "#00E5FF"), ("#0D0920", 600, 900, "#FF5EAF"))):
        x = -20
        while x < W:
            w = rng.randint(60, 150)
            h = rng.randint(lo, hi) - layer * 40
            top = H - h
            body += '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x, top, w, h, color)
            if rng.random() < 0.35:
                body += '<rect x="%d" y="%d" width="4" height="40" fill="%s"/>' % (x + w // 2, top - 40, color)
            for wy in range(top + 18, H - 20, 26):
                for wx in range(x + 10, x + w - 14, 22):
                    if rng.random() < 0.18 + 0.1 * layer:
                        body += '<rect x="%d" y="%d" width="9" height="12" fill="%s" opacity="%.2f"/>' % (wx, wy, win, rng.uniform(0.35, 0.9))
            x += w + rng.randint(4, 18)
    return svg(body, defs)


def sunset_hills():
    rng = random.Random(2)
    defs = gradient("sky", [(0, "#2D1B69"), (0.45, "#C2417E"), (0.75, "#FF8A5B"), (1, "#FFD27F")])
    defs += gradient("sun", [(0, "#FFF1A8"), (1, "#FF6F61")])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += stars(rng, 60, 0, 0.25)
    # A big striped sun, cut by bands like old posters.
    body += '<circle cx="960" cy="640" r="300" fill="url(#sun)"/>'
    for i in range(7):
        y = 600 + i * 34
        body += '<rect x="640" y="%d" width="640" height="%d" fill="#C2417E" opacity="0.85"/>' % (y, 4 + i * 2)
    for i, (color, base, height) in enumerate((("#7A2E6E", 700, 120), ("#55205F", 780, 110), ("#3A1650", 860, 90), ("#22103A", 950, 70))):
        body += ridge(rng, base, height, 26 - i * 3, color)
    for _ in range(9):
        x, y = rng.uniform(300, 1600), rng.uniform(250, 520)
        body += '<path d="M%.0f %.0f q 12 -10 24 0 q 12 -10 24 0" stroke="#2D1B69" stroke-width="3" fill="none"/>' % (x, y)
    return svg(body, defs)


def sakura():
    rng = random.Random(3)
    defs = gradient("sky", [(0, "#9FD3FF"), (0.6, "#FFD9EC"), (1, "#FFF3F8")])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += cloud(420, 260, 1.4, "#FFFFFF", 0.8) + cloud(1300, 180, 1.1, "#FFFFFF", 0.7)
    # A snow-capped mountain far away.
    body += '<polygon points="560,820 960,330 1360,820" fill="#8FA6D9"/>'
    body += '<polygon points="880,428 960,330 1040,428 1005,415 980,440 955,412 925,440" fill="#FFFFFF"/>'
    body += ridge(rng, 880, 60, 14, "#B5D8A8") + ridge(rng, 960, 40, 10, "#8CC084")
    # A cherry branch from the top left, covered in blossoms.
    body += '<path d="M-40 140 C 300 160, 520 260, 820 210 S 1150 120, 1260 60" stroke="#4A2B33" stroke-width="22" fill="none" stroke-linecap="round"/>'
    body += '<path d="M380 190 C 430 300, 520 340, 600 360" stroke="#4A2B33" stroke-width="10" fill="none" stroke-linecap="round"/>'
    for _ in range(260):
        t = rng.random()
        x = -40 + t * 1300 + rng.gauss(0, 60)
        y = 150 + math.sin(t * 3.0) * 60 - t * 60 + rng.gauss(0, 55)
        color = rng.choice(("#FFB7D5", "#FF9CC6", "#FFD1E6", "#FFFFFF"))
        body += '<circle cx="%.0f" cy="%.0f" r="%.1f" fill="%s" opacity="0.9"/>' % (x, y, rng.uniform(7, 16), color)
    for _ in range(90):
        x, y = rng.uniform(0, W), rng.uniform(250, H)
        body += '<ellipse cx="%.0f" cy="%.0f" rx="7" ry="4" fill="#FF9CC6" opacity="%.2f" transform="rotate(%d %.0f %.0f)"/>' % (
            x, y, rng.uniform(0.5, 0.9), rng.randint(0, 180), x, y)
    return svg(body, defs)


def aurora():
    rng = random.Random(4)
    defs = gradient("sky", [(0, "#020814"), (0.6, "#0A1E3A"), (1, "#123B55")])
    defs += gradient("a1", [(0, "#3CE6A0"), (0.5, "#00E5FF"), (1, "#7C5CFF")], vertical=False)
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += stars(rng, 220, 0, 0.7)
    for i in range(4):
        y0 = 260 + i * 60
        d = "M -100 %d " % y0 + " ".join(
            "Q %d %d %d %d" % (x + 120, y0 + rng.randint(-160, 40), x + 240, y0 + rng.randint(-60, 60))
            for x in range(-100, W + 100, 240))
        body += '<path d="%s" stroke="url(#a1)" stroke-width="%d" fill="none" opacity="%.2f" stroke-linecap="round"/>' % (d, 90 - i * 16, 0.22 + i * 0.08)
    body += ridge(rng, 760, 140, 40, "#1B2B44") + ridge(rng, 860, 90, 25, "#E8F4FF", opacity=0.95)
    body += '<rect y="900" width="%d" height="180" fill="#0E2A40"/>' % W
    body += '<rect y="900" width="%d" height="3" fill="#3CE6A0" opacity="0.5"/>' % W
    return svg(body, defs)


def ocean():
    rng = random.Random(5)
    defs = gradient("sky", [(0, "#3E8BFF"), (0.55, "#8EC9FF"), (1, "#DDF1FF")])
    defs += gradient("sea", [(0, "#1E6FD9"), (1, "#0B3B8C")])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    for cx, cy, s in ((300, 360, 2.0), (900, 300, 2.6), (1500, 380, 2.2), (1200, 520, 1.3)):
        body += cloud(cx, cy, s, "#FFFFFF", 0.95)
        body += cloud(cx + 10, cy + 30, s * 0.9, "#D6E9FF", 0.6)
    body += '<rect y="700" width="%d" height="380" fill="url(#sea)"/>' % W
    for _ in range(140):
        x, y = rng.uniform(0, W), rng.uniform(710, H)
        body += '<rect x="%.0f" y="%.0f" width="%.0f" height="3" rx="1.5" fill="#FFFFFF" opacity="%.2f"/>' % (x, y, rng.uniform(20, 90), rng.uniform(0.2, 0.7))
    return svg(body, defs)


def tesseract():
    defs = radial("glow", [(0, "#00E5FF", 0.35), (0.5, "#7C5CFF", 0.15), (1, "#080B10", 0)])
    body = '<rect width="%d" height="%d" fill="#080B10"/><circle cx="960" cy="540" r="620" fill="url(#glow)"/>' % (W, H)
    outer = [(660, 240), (1260, 240), (1260, 840), (660, 840)]
    inner = [(820, 400), (1100, 400), (1100, 680), (820, 680)]
    pairs = [(outer[i], outer[(i + 1) % 4]) for i in range(4)] + [(inner[i], inner[(i + 1) % 4]) for i in range(4)] + list(zip(outer, inner))
    for (x1, y1), (x2, y2) in pairs:
        body += '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#00E5FF" stroke-width="4" opacity="0.85"/>' % (x1, y1, x2, y2)
    for x, y in outer + inner:
        body += '<circle cx="%d" cy="%d" r="9" fill="#F4FCFF"/>' % (x, y)
    return svg(body, defs)


SCENES = {
    "ozi-gece-sehri.svg": night_city,
    "ozi-gun-batimi.svg": sunset_hills,
    "ozi-sakura.svg": sakura,
    "ozi-kutup-isiklari.svg": aurora,
    "ozi-okyanus.svg": ocean,
    "ozi-tesseract.svg": tesseract,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, make in SCENES.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(make())
        print(name)


if __name__ == "__main__":
    main()
