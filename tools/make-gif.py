#!/usr/bin/env python3
"""Render the looping OziOS tesseract animation used on the download page.

    python tools/make-gif.py [output.gif] [--size 480] [--frames 72]

Needs Pillow. The loop is seamless: a tesseract maps onto itself after a
quarter turn, so one quarter turn in two planes is a full cycle.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

INK = (8, 11, 16)
CYAN = (0, 229, 255)
ICE = (244, 252, 255)

VERTS = [(x, y, z, w) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1) for w in (-1, 1)]
EDGES = [(a, b) for a in range(16) for b in range(a + 1, 16) if bin(a ^ b).count("1") == 1]


def rotate(a, b, angle):
    c, s = math.cos(angle), math.sin(angle)
    return a * c - b * s, a * s + b * c


def project(phase, size, centre_y):
    turn = phase * math.pi / 2
    unit = size / 3.5
    points = []
    for x, y, z, w in VERTS:
        x, w = rotate(x, w, 0.45 + turn)
        y, z = rotate(y, z, 0.30 + turn)
        x, y = rotate(x, y, 0.35)
        k = 2.6 / (3.4 - w)
        x, y, z = x * k, y * k, z * k
        k = 3.2 / (4.6 - z)
        depth = max(0.0, min(1.0, (w + 1.5) / 3.0 * 0.6 + (z + 2.0) / 4.0 * 0.4))
        points.append((size / 2 + x * k * unit, centre_y + y * k * unit, depth))
    return points


def background(size):
    image = Image.new("RGB", (size, size), INK)
    glow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glow).ellipse((size * 0.18, size * 0.12, size * 0.82, size * 0.76), fill=46)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.14))
    image.paste(Image.new("RGB", (size, size), CYAN), mask=glow)
    return image


def title(size):
    """The wordmark on a transparent layer, or None without a usable font."""
    for name in ("segoeuil.ttf", "segoeui.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.075))
            break
        except OSError:
            continue
    else:
        return None
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    letters, gap = "OziOS", size * 0.035
    width = sum(draw.textlength(ch, font=font) for ch in letters) + gap * (len(letters) - 1)
    x = (size - width) / 2
    for ch in letters:
        draw.text((x, size * 0.83), ch, font=font, fill=ICE + (255,))
        x += draw.textlength(ch, font=font) + gap
    return layer


def frame(phase, size, base, text):
    points = project(phase, size, size * 0.44)
    lines = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(lines)
    for a, b in sorted(EDGES, key=lambda e: points[e[0]][2] + points[e[1]][2]):
        (x0, y0, d0), (x1, y1, d1) = points[a], points[b]
        d = (d0 + d1) / 2
        shade = tuple(int(c * (0.25 + d * 0.75)) for c in CYAN)
        draw.line((x0, y0, x1, y1), fill=shade, width=max(2, round((1.2 + d * 2.2) * size / 480)))
    for x, y, d in points:
        r = (2.0 + d * 3.0) * size / 480
        draw.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * (0.5 + d * 0.5)) for c in ICE))

    halo = lines.filter(ImageFilter.GaussianBlur(size / 80)).point(lambda v: int(v * 0.8))
    image = ImageChops.add(ImageChops.add(base, halo), lines)
    if text:
        image.paste(text, mask=text)
    return image


def main():
    args = sys.argv[1:]
    size, count = 480, 72
    out = Path(__file__).resolve().parent.parent / "branding" / "ozios.gif"
    while args:
        arg = args.pop(0)
        if arg == "--size":
            size = int(args.pop(0))
        elif arg == "--frames":
            count = int(args.pop(0))
        else:
            out = Path(arg)

    scale = 2                       # draw large, shrink for smooth edges
    big = size * scale
    base, text = background(big), title(big)
    frames = [frame(i / count, big, base, text).resize((size, size), Image.LANCZOS) for i in range(count)]

    # One shared palette keeps the file small and stops colours from flickering.
    palette = frames[count // 3].quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE)
    frames = [f.quantize(palette=palette, dither=Image.NONE) for f in frames]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=50, loop=0, optimize=True)
    print("%s  %d frames  %.0f KB" % (out, count, out.stat().st_size / 1024))


if __name__ == "__main__":
    main()
