#!/usr/bin/env python3
"""Render the still images the installer and boot loaders need.

    python tools/make-art.py

Writes into branding/calamares/ozios (logo, icon, welcome banner) and
branding/boot (background for the boot menu and the boot loader splash). The
images are committed; this only needs running when the artwork changes.
Needs Pillow.
"""
import importlib.util
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("make_gif", Path(__file__).with_name("make-gif.py"))
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)

INK, CYAN, ICE = art.INK, art.CYAN, art.ICE
PHASE = 0.22                         # a pleasing pose of the figure


def font(size):
    for name in ("segoeuil.ttf", "segoeui.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def figure(size, transparent=False):
    """The tesseract on an ink square (or on nothing, for logos)."""
    big = size * 2
    base = art.background(big) if not transparent else Image.new("RGB", (big, big), (0, 0, 0))
    image = art.frame(PHASE, big, base, None).resize((size, size), Image.LANCZOS)
    if transparent:
        # Dark pixels become see-through, the lines keep their brightness.
        alpha = image.convert("L").point(lambda v: min(255, int(v * 2.2)))
        image = image.convert("RGBA")
        image.putalpha(alpha)
    return image


def wordmark(draw, xy, text, size, fill=ICE, gap=0.06):
    f = font(size)
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + size * gap


def background(width, height):
    """Ink with the figure on the right and a faint glow behind it."""
    image = Image.new("RGB", (width, height), INK)
    glow = Image.new("L", (width, height), 0)
    ImageDraw.Draw(glow).ellipse((width * 0.52, height * 0.05, width * 0.98, height * 0.95), fill=40)
    glow = glow.filter(ImageFilter.GaussianBlur(height * 0.12))
    image.paste(Image.new("RGB", (width, height), CYAN), mask=glow)
    fig = figure(int(height * 0.9), transparent=True)
    image.paste(fig, (int(width * 0.55), int(height * 0.05)), fig)
    draw = ImageDraw.Draw(image)
    wordmark(draw, (int(width * 0.07), int(height * 0.42)), "OziOS", int(height * 0.12))
    return image


def main():
    cal = ROOT / "branding" / "calamares" / "ozios"
    boot = ROOT / "branding" / "boot"
    cal.mkdir(parents=True, exist_ok=True)
    boot.mkdir(parents=True, exist_ok=True)

    logo = figure(256, transparent=True)
    logo.save(cal / "logo.png", optimize=True)
    figure(128, transparent=True).save(cal / "icon.png", optimize=True)

    banner = Image.new("RGB", (900, 260), INK)
    fig = figure(240, transparent=True)
    banner.paste(fig, (620, 10), fig)
    wordmark(ImageDraw.Draw(banner), (40, 82), "OziOS", 86)
    banner.save(cal / "welcome.png", optimize=True)

    background(1920, 1080).save(boot / "background.png", optimize=True)
    background(1920, 1080).save(boot / "limine-splash.png", optimize=True)
    for path in sorted(list(cal.glob("*.png")) + list(boot.glob("*.png"))):
        print("%-48s %6.1f KB" % (path.relative_to(ROOT), path.stat().st_size / 1024))


if __name__ == "__main__":
    main()
