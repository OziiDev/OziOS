#!/usr/bin/env python3
"""Write the OziOS wallpapers (branding/wallpapers/*.svg): flat, anime-style
scenes drawn from shapes, so they are our own work and scale to any screen.

    python3 tools/make-wallpapers.py

The output is deterministic (fixed random seeds); a test checks the files in
the repository match it.
"""
import importlib.util
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


def _mascot():
    spec = importlib.util.spec_from_file_location("mascot", os.path.join(HERE, "mascot.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MASCOT = _mascot()


def waves():
    """Soft bands of colour flowing across, purple through pink to orange."""
    defs = gradient("sky", [(0, "#2B1055"), (1, "#7597DE")])
    colors = ["#5B2A86", "#8E3FA8", "#C04BA6", "#E85D9A", "#FF7B7B", "#FFA45C", "#FFD166"]
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    for i, color in enumerate(colors):
        base = 300 + i * 110
        amp = 70 - i * 4
        phase = i * 0.9
        pts = ["M -20 %d" % H]
        for x in range(-20, W + 61, 60):
            pts.append("L %d %.1f" % (x, base + amp * math.sin(x / 260.0 + phase) + 25 * math.sin(x / 97.0 + phase * 2)))
        pts.append("L %d %d Z" % (W + 40, H))
        body += '<path d="%s" fill="%s" opacity="0.92"/>' % (" ".join(pts), color)
    return svg(body, defs)


def synthwave():
    """A striped sun over a glowing grid, in magenta and cyan."""
    defs = gradient("sky", [(0, "#0B0221"), (0.55, "#2D0B4E"), (1, "#5A1268")])
    defs += gradient("sun", [(0, "#FFE66D"), (0.5, "#FF7AA2"), (1, "#C53DD8")])
    defs += gradient("floor", [(0, "#1A0633"), (1, "#05010F")])
    defs += radial("haze", [(0, "#FF4FD8", 0.45), (1, "#FF4FD8", 0)])
    rng = random.Random(7)
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += stars(rng, 160, 0, 0.45)
    body += '<ellipse cx="960" cy="640" rx="700" ry="260" fill="url(#haze)"/>'
    body += '<circle cx="960" cy="560" r="260" fill="url(#sun)"/>'
    for i in range(7):
        y = 600 + i * 26
        body += '<rect x="680" y="%d" width="560" height="%d" fill="#2D0B4E"/>' % (y, 4 + i * 2)
    body += ridge(rng, 690, 70, 30, "#1C0738") 
    body += '<rect y="700" width="%d" height="380" fill="url(#floor)"/>' % W
    for i in range(1, 14):
        y = 700 + (i ** 1.9) * 2.2
        body += '<line x1="0" y1="%.0f" x2="%d" y2="%.0f" stroke="#FF4FD8" stroke-width="%.1f" opacity="0.8"/>' % (y, W, y, 1 + i * 0.25)
    for i in range(-16, 17):
        body += '<line x1="960" y1="700" x2="%d" y2="%d" stroke="#3FE0FF" stroke-width="2" opacity="0.7"/>' % (960 + i * 260, H + 200)
    body += '<rect y="698" width="%d" height="4" fill="#FF4FD8"/>' % W
    return svg(body, defs)


def bubbles():
    """Big soft circles of colour on a light background."""
    rng = random.Random(8)
    defs = gradient("bg", [(0, "#FDF6FF"), (1, "#EAF4FF")])
    palette = ["#FF8FB1", "#9B7BFF", "#4FB6FF", "#45F582", "#FFD166", "#FF9F68"]
    body = '<rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H)
    for i, color in enumerate(palette):
        defs += radial("b%d" % i, [(0, color, 0.85), (0.7, color, 0.35), (1, color, 0)])
    for _ in range(22):
        i = rng.randrange(len(palette))
        r = rng.uniform(140, 420)
        body += '<circle cx="%.0f" cy="%.0f" r="%.0f" fill="url(#b%d)"/>' % (rng.uniform(-100, W + 100), rng.uniform(-100, H + 100), r, i)
    for _ in range(40):
        body += '<circle cx="%.0f" cy="%.0f" r="%.1f" fill="#FFFFFF" opacity="0.7"/>' % (rng.uniform(0, W), rng.uniform(0, H), rng.uniform(3, 10))
    return svg(body, defs)


def lowpoly():
    """Triangles in a sweep from teal to violet."""
    rng = random.Random(9)
    cols, rows = 17, 10
    pts = {}
    for r in range(rows + 1):
        for c in range(cols + 1):
            jx = 0 if c in (0, cols) else rng.uniform(-40, 40)
            jy = 0 if r in (0, rows) else rng.uniform(-40, 40)
            pts[r, c] = (c * W / cols + jx, r * H / rows + jy)
    stops = [(0x12, 0xC2, 0xE9), (0x45, 0xF5, 0x82), (0x9B, 0x7B, 0xFF), (0xC4, 0x71, 0xED), (0xF6, 0x4F, 0x59)]

    def color_at(t):
        t = min(max(t, 0), 0.999) * (len(stops) - 1)
        i, f = int(t), t - int(t)
        a, b = stops[i], stops[i + 1]
        return "#%02X%02X%02X" % tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))

    body = ""
    for r in range(rows):
        for c in range(cols):
            p = [pts[r, c], pts[r, c + 1], pts[r + 1, c + 1], pts[r + 1, c]]
            for tri in ((p[0], p[1], p[2]), (p[0], p[2], p[3])):
                cx = sum(q[0] for q in tri) / 3
                cy = sum(q[1] for q in tri) / 3
                t = (cx / W) * 0.75 + (cy / H) * 0.25 + rng.uniform(-0.04, 0.04)
                body += '<polygon points="%s" fill="%s" stroke="%s" stroke-width="1"/>' % (
                    " ".join("%.1f,%.1f" % q for q in tri), color_at(t), color_at(t))
    return svg(body)


def rainbow():
    """Pastel ribbons in a slant, with a few sparkles."""
    rng = random.Random(10)
    colors = ["#FFB3C7", "#FFCFA3", "#FFF1A8", "#BFF5C8", "#A8E1FF", "#C7B8FF", "#F3B8FF"]
    body = '<rect width="%d" height="%d" fill="#FFF9FB"/>' % (W, H)
    band = 170
    for i, color in enumerate(colors * 3):
        x = -900 + i * band
        body += '<polygon points="%d,0 %d,0 %d,%d %d,%d" fill="%s"/>' % (x, x + band, x + band + 700, H, x + 700, H, color)
    for _ in range(26):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 26)
        k = r * 0.22
        body += '<path d="M %.0f %.0f L %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="#FFFFFF" opacity="0.9"/>' % (
            x, y - r, x + k, y - k, x + r, y, x + k, y + k, x, y + r, x - k, y + k, x - r, y, x - k, y - k)
    return svg(body)


def rings():
    """Quiet and dark: the OziOS ring glowing in the middle."""
    defs = radial("glow", [(0, "#45F582", 0.35), (0.45, "#45C6F5", 0.12), (1, "#06090C", 0)])
    defs += gradient("ring", [(0, "#45F582"), (1, "#45C6F5")], vertical=False)
    body = '<rect width="%d" height="%d" fill="#06090C"/>' % (W, H)
    body += '<circle cx="960" cy="540" r="560" fill="url(#glow)"/>'
    for i, r in enumerate((420, 330, 250)):
        body += '<circle cx="960" cy="540" r="%d" fill="none" stroke="url(#ring)" stroke-width="%d" opacity="%.2f"/>' % (
            r, 2 + i, 0.15 + i * 0.1)
    body += '<circle cx="960" cy="540" r="150" fill="none" stroke="url(#ring)" stroke-width="34"/>'
    body += '<circle cx="1050" cy="460" r="28" fill="#45F582"/>'
    return svg(body, defs)


def chan_night():
    """Ozi-chan waving on a hill under the moon."""
    rng = random.Random(11)
    defs = gradient("sky", [(0, "#0B1033"), (0.6, "#2A2E6E"), (1, "#5B4B9A")])
    defs += radial("moon", [(0, "#FFF6D6", 0.55), (1, "#FFF6D6", 0)])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += stars(rng, 260, 0, 0.75)
    body += '<circle cx="1480" cy="250" r="260" fill="url(#moon)"/><circle cx="1480" cy="250" r="120" fill="#FFF3C4"/>'
    body += '<circle cx="1440" cy="220" r="20" fill="#F2E2A8"/><circle cx="1520" cy="300" r="14" fill="#F2E2A8"/>'
    body += ridge(rng, 860, 110, 30, "#2B2560") + ridge(rng, 930, 70, 18, "#1D1A45")
    body += '<ellipse cx="560" cy="1040" rx="620" ry="190" fill="#151338"/>'
    body += MASCOT.ozi_chan(370, 380, 1.08, colors={"hoodie": "#9B7BFF", "hoodie_shade": "#7656E0",
                                                    "eyes": "#B394FF", "eyes_dark": "#4B2FA8"})
    for _ in range(30):
        x, y = rng.uniform(80, 1100), rng.uniform(820, 1060)
        body += '<circle cx="%.0f" cy="%.0f" r="%.1f" fill="#FFE66D" opacity="%.2f"/>' % (x, y, rng.uniform(2, 4), rng.uniform(0.5, 0.9))
    return svg(body, defs)


def chan_sakura():
    """Pink Ozi-chan in falling cherry petals."""
    rng = random.Random(12)
    defs = gradient("sky", [(0, "#FFD6E8"), (0.6, "#FFEAF3"), (1, "#FFF8FB")])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += cloud(380, 220, 1.5, "#FFFFFF", 0.8) + cloud(1500, 160, 1.2, "#FFFFFF", 0.75)
    body += '<path d="M %d 60 C 1700 180, 1500 260, 1260 240 S 980 300, 900 380" stroke="#5A3340" stroke-width="22" fill="none" stroke-linecap="round"/>' % (W + 40)
    for _ in range(220):
        t = rng.random()
        x = W + 40 - t * 1000 + rng.gauss(0, 50)
        y = 60 + t * 300 + rng.gauss(0, 55)
        body += '<circle cx="%.0f" cy="%.0f" r="%.1f" fill="%s" opacity="0.9"/>' % (
            x, y, rng.uniform(7, 15), rng.choice(("#FFB7D5", "#FF9CC6", "#FFD1E6", "#FFFFFF")))
    body += '<ellipse cx="760" cy="1060" rx="900" ry="150" fill="#F7C6DA"/>'
    body += MASCOT.ozi_chan(560, 420, 1.12, colors={"hoodie": "#FF7EB6", "hoodie_shade": "#E25A97",
                                                    "eyes": "#FF9CC6", "eyes_dark": "#A0275E"}, wink=True)
    for _ in range(80):
        x, y = rng.uniform(0, W), rng.uniform(200, H)
        body += '<ellipse cx="%.0f" cy="%.0f" rx="8" ry="4.5" fill="#FF9CC6" opacity="%.2f" transform="rotate(%d %.0f %.0f)"/>' % (
            x, y, rng.uniform(0.5, 0.9), rng.randint(0, 180), x, y)
    return svg(body, defs)


def chan_classroom():
    """For the classroom: a green chalkboard with doodles, Ozi-chan at its side."""
    rng = random.Random(13)
    defs = gradient("wall", [(0, "#F5EFE3"), (1, "#E8DFCC")])
    defs += gradient("board", [(0, "#2F5D4A"), (1, "#244A3B")])
    body = '<rect width="%d" height="%d" fill="url(#wall)"/>' % (W, H)
    body += '<rect x="120" y="90" width="1300" height="760" rx="18" fill="#8B5E3C"/>'
    body += '<rect x="146" y="116" width="1248" height="708" rx="8" fill="url(#board)"/>'
    body += '<rect x="140" y="850" width="1260" height="22" rx="6" fill="#7A5134"/>'
    for x, color in ((300, "#FFFFFF"), (360, "#FFE066"), (420, "#FF8FAB")):
        body += '<rect x="%d" y="836" width="40" height="12" rx="5" fill="%s"/>' % (x, color)
    chalk = 'fill="none" stroke="#F4F1E8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"'
    text = 'font-family="Comic Sans MS, Noto Sans, sans-serif" fill="#F4F1E8" opacity="0.92"'
    body += '<text x="220" y="230" font-size="78" %s>Merhaba!</text>' % text
    body += '<text x="220" y="340" font-size="54" %s>2 + 3 = 5</text>' % text
    body += '<text x="220" y="430" font-size="54" %s>a² + b² = c²</text>' % text
    body += '<text x="820" y="230" font-size="46" fill="#FFE066" opacity="0.92" font-family="Comic Sans MS, Noto Sans, sans-serif">H₂O</text>'
    # A triangle with its right angle, a sun and a little plant.
    body += '<path d="M 860 640 L 1160 640 L 860 380 Z" %s/>' % chalk
    body += '<path d="M 860 610 L 890 610 L 890 640" %s/>' % chalk
    body += '<circle cx="1260" cy="230" r="52" fill="none" stroke="#FFE066" stroke-width="5" opacity="0.9"/>'
    for i in range(8):
        a = i * math.pi / 4
        body += '<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#FFE066" stroke-width="5" stroke-linecap="round" opacity="0.9"/>' % (
            1260 + 70 * math.cos(a), 230 + 70 * math.sin(a), 1260 + 92 * math.cos(a), 230 + 92 * math.sin(a))
    body += '<path d="M 300 760 Q 300 640 300 600 M 300 680 q -50 -30 -70 -80 q 50 10 70 80 M 300 650 q 40 -40 80 -50 q -10 50 -80 50" %s/>' % chalk
    body += '<path d="M 260 760 L 340 760 L 330 800 L 270 800 Z" fill="none" stroke="#FF8FAB" stroke-width="5" stroke-linejoin="round" opacity="0.9"/>'
    # Old chalk wiped off, as faint streaks.
    for _ in range(7):
        x, y = rng.uniform(560, 1250), rng.uniform(470, 780)
        body += '<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="20" fill="#F4F1E8" opacity="0.05"/>' % (
            x, y, rng.uniform(120, 260), rng.uniform(26, 50))
    body += '<rect y="960" width="%d" height="120" fill="#C9B79A"/>' % W
    body += MASCOT.ozi_chan(1400, 440, 1.15)
    return svg(body, defs)


def chan_code():
    """Ozi-chan beside a terminal window, on a dark desk-light background."""
    rng = random.Random(14)
    defs = gradient("bg", [(0, "#0A1210"), (1, "#122019")])
    defs += radial("glow", [(0, "#45F582", 0.25), (1, "#45F582", 0)])
    body = '<rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H)
    body += '<circle cx="760" cy="520" r="700" fill="url(#glow)"/>'
    for _ in range(60):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        body += '<text x="%.0f" y="%.0f" font-family="monospace" font-size="%d" fill="#45F582" opacity="%.2f">%s</text>' % (
            x, y, rng.randint(14, 26), rng.uniform(0.05, 0.16), rng.choice(("{ }", "&lt;/&gt;", "fn", "0101", "ls", "&gt;_", "git", "::", "=&gt;")))
    body += '<rect x="300" y="230" width="900" height="560" rx="22" fill="#0E1714" stroke="#2C4A3C" stroke-width="3"/>'
    body += '<rect x="300" y="230" width="900" height="56" rx="22" fill="#16241E"/><rect x="300" y="262" width="900" height="24" fill="#16241E"/>'
    for i, color in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        body += '<circle cx="%d" cy="258" r="9" fill="%s"/>' % (1150 - i * 30, color)
    lines = [("#45F582", "ozi@ozios ~ $ ", "#F2FCF6", "ozi-fetch"),
             ("#45C6F5", "sistem    ", "#F2FCF6", "OziOS"),
             ("#45C6F5", "masaüstü  ", "#F2FCF6", "Öz (oziwm)"),
             ("#45C6F5", "maskot    ", "#FF8FB1", "Ozi-chan ♥"),
             ("#45F582", "ozi@ozios ~ $ ", "#F2FCF6", "ozi update"),
             ("#8DA897", "her şey güncel ✓", "#F2FCF6", ""),
             ("#45F582", "ozi@ozios ~ $ ", "#F2FCF6", "")]
    for i, (c1, a, c2, b) in enumerate(lines):
        y = 345 + i * 56
        # Two pieces, the second placed by character count: spaces in SVG text collapse.
        body += '<text x="340" y="%d" font-family="monospace" font-size="32" fill="%s">%s</text>' % (y, c1, a.strip())
        if b:
            body += '<text x="%d" y="%d" font-family="monospace" font-size="32" fill="%s">%s</text>' % (340 + len(a) * 19.3, y, c2, b)
    body += '<rect x="%d" y="%d" width="18" height="34" fill="#45F582"/>' % (340 + 14 * 19.3, 345 + 6 * 56 - 28)
    body += MASCOT.ozi_chan(1280, 400, 1.2)
    return svg(body, defs)


def chan_space():
    """Blue Ozi-chan floating among planets."""
    rng = random.Random(15)
    defs = gradient("sky", [(0, "#050818"), (1, "#121A44")])
    defs += radial("neb", [(0, "#4FB6FF", 0.35), (1, "#4FB6FF", 0)])
    defs += radial("neb2", [(0, "#FF7EB6", 0.3), (1, "#FF7EB6", 0)])
    defs += gradient("planet", [(0, "#FFD166"), (1, "#FF7B54")])
    defs += gradient("planet2", [(0, "#7CF5C0"), (1, "#22A2E8")])
    body = '<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H)
    body += '<ellipse cx="500" cy="420" rx="600" ry="360" fill="url(#neb)"/><ellipse cx="1500" cy="700" rx="560" ry="340" fill="url(#neb2)"/>'
    body += stars(rng, 320, 0, 1.0)
    body += '<circle cx="1560" cy="260" r="140" fill="url(#planet)"/>'
    body += '<ellipse cx="1560" cy="260" rx="230" ry="38" fill="none" stroke="#FFE9B0" stroke-width="10" opacity="0.8" transform="rotate(-18 1560 260)"/>'
    body += '<circle cx="330" cy="850" r="90" fill="url(#planet2)"/><circle cx="300" cy="830" r="18" fill="#FFFFFF" opacity="0.25"/>'
    body += '<g transform="rotate(-10 960 560)">' + MASCOT.ozi_chan(760, 300, 1.05, colors={
        "hoodie": "#4FB6FF", "hoodie_shade": "#2E8FE0", "eyes": "#57C3FF", "eyes_dark": "#155C9E"}) + "</g>"
    return svg(body, defs)


def chan_paws():
    """A pastel pattern of paws and little Ozi-chan faces."""
    rng = random.Random(16)
    body = '<rect width="%d" height="%d" fill="#EAFBF1"/>' % (W, H)
    colors = ["#45F582", "#9B7BFF", "#FF7EB6", "#4FB6FF", "#FFD166"]
    for row in range(8):
        for col in range(12):
            x = col * 170 + (85 if row % 2 else 0) + rng.uniform(-10, 10)
            y = row * 150 + rng.uniform(-10, 10)
            c = colors[(row + col) % len(colors)]
            a = rng.randint(-25, 25)
            body += ('<g transform="translate(%.0f %.0f) rotate(%d)" fill="%s" opacity="0.55">'
                     '<ellipse cx="0" cy="12" rx="22" ry="18"/><circle cx="-20" cy="-14" r="8"/><circle cx="-7" cy="-24" r="8"/>'
                     '<circle cx="7" cy="-24" r="8"/><circle cx="20" cy="-14" r="8"/></g>') % (x, y, a, c)
    body += '<rect x="560" y="300" width="800" height="480" rx="60" fill="#FFFFFF" opacity="0.75"/>'
    body += MASCOT.ozi_chan(760, 300, 0.92)
    return svg(body)


SCENES = {
    "ozi-gece-sehri.svg": night_city,
    "ozi-gun-batimi.svg": sunset_hills,
    "ozi-sakura.svg": sakura,
    "ozi-kutup-isiklari.svg": aurora,
    "ozi-okyanus.svg": ocean,
    "ozi-tesseract.svg": tesseract,
    "ozi-dalgalar.svg": waves,
    "ozi-neon.svg": synthwave,
    "ozi-baloncuklar.svg": bubbles,
    "ozi-ucgenler.svg": lowpoly,
    "ozi-gokkusagi.svg": rainbow,
    "ozi-halka.svg": rings,
    "ozi-chan-gece.svg": chan_night,
    "ozi-chan-sakura.svg": chan_sakura,
    "ozi-chan-sinif.svg": chan_classroom,
    "ozi-chan-kod.svg": chan_code,
    "ozi-chan-uzay.svg": chan_space,
    "ozi-chan-patiler.svg": chan_paws,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, make in SCENES.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(make())
        print(name)


if __name__ == "__main__":
    main()
