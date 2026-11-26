"""Desktop colours taken from the wallpaper (the "auto" theme).

The most colourful hue of the picture becomes the accent, the next one far
enough from it the second accent, and the dark surfaces lean slightly toward
the accent so the bar, dock and window frames sit on the picture instead of
on top of it. The desktop stays dark whatever the picture: text must be
readable everywhere.

    colors_for(path)   -> {"ink": "#RRGGBB", ...} or None
    pick(pixels)       -> the same from (r, g, b) tuples; no Qt, so it is tested alone
"""
import colorsys
import math

BINS = 24                 # 15 degrees of hue each
SAMPLE = 64               # the picture is read at most this wide and high

# Used for a picture without colour (black and white, grey) and for the tesseract.
DEFAULT_HUE = 187 / 360   # OziOS cyan
DEFAULT_HUE2 = 252 / 360


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return (round(r * 255), round(g * 255), round(b * 255))


def _luminance(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _bright(hue, saturation, ink):
    """The accent at this hue: vivid, yet at least 6:1 against the dark ink
    (blue and violet need some white mixed in for that)."""
    s = max(0.45, min(0.72, saturation))
    rgb = _hsv(hue, s, 0.96)
    while _contrast(rgb, ink) < 6.0 and s > 0.2:
        s -= 0.05
        rgb = _hsv(hue, s, 0.96)
    return rgb


def _hue_distance(a, b):
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def hues(pixels):
    """The two hues the picture is most coloured with, and how saturated the
    first is: (hue, hue2, saturation), hues in 0..1; None for a grey picture."""
    weight = [0.0] * BINS
    sin_sum = [0.0] * BINS
    cos_sum = [0.0] * BINS
    sat_sum = [0.0] * BINS
    total = 0
    for r, g, b in pixels:
        total += 1
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.18 or v < 0.1:
            continue
        w = s * v
        i = int(h * BINS) % BINS
        weight[i] += w
        sin_sum[i] += math.sin(h * 2 * math.pi) * w
        cos_sum[i] += math.cos(h * 2 * math.pi) * w
        sat_sum[i] += s * w
    if total == 0 or sum(weight) / total < 0.004:
        return None
    # A hue spread over two neighbouring bins still counts as one.
    smooth = [weight[i - 1] * 0.5 + weight[i] + weight[(i + 1) % BINS] * 0.5 for i in range(BINS)]

    def centre(i):
        js = (i - 1, i, (i + 1) % BINS)
        s = sum(sin_sum[j] for j in js)
        c = sum(cos_sum[j] for j in js)
        return (math.atan2(s, c) / (2 * math.pi)) % 1.0

    first = max(range(BINS), key=lambda i: smooth[i])
    hue = centre(first)
    saturation = sum(sat_sum[j] for j in (first - 1, first, (first + 1) % BINS)) / max(
        1e-9, sum(weight[j] for j in (first - 1, first, (first + 1) % BINS)))
    others = [i for i in range(BINS) if _hue_distance((i + 0.5) / BINS, hue) >= 50 / 360]
    second = max(others, key=lambda i: smooth[i], default=None)
    if second is not None and smooth[second] >= smooth[first] * 0.12:
        hue2 = centre(second)
    else:
        # One colour only: the second accent leans toward violet, like the rest of OziOS.
        hue2 = (hue + 55 / 360) % 1.0
    return hue, hue2, saturation


def palette(hue, hue2, saturation=0.7):
    ink = _hsv(hue, 0.45, 0.065)
    accent = _bright(hue, saturation, ink)
    return {
        "ink": ink,
        "raised": _hsv(hue, 0.38, 0.105),
        "control": _hsv(hue, 0.30, 0.15),
        "text": _hsv(hue, 0.04, 0.99),
        "muted": _hsv(hue, 0.16, 0.66),
        "accent": accent,
        "accent2": _bright(hue2, saturation, ink),
        "onAccent": _hsv(hue, 0.6, 0.08),
    }


def pick(pixels):
    found = hues(pixels)
    if found is None:
        return palette(DEFAULT_HUE, DEFAULT_HUE2, 1.0)
    return palette(*found)


def to_hex(colors):
    return {k: "#%02X%02X%02X" % v for k, v in colors.items()}


def read_pixels(path):
    """The picture, made small, as (r, g, b) tuples; [] if it cannot be read."""
    try:
        from PyQt6.QtCore import QSize, Qt
        from PyQt6.QtGui import QImage, QImageReader
    except ImportError:
        return []
    reader = QImageReader(path)
    size = reader.size()
    if size.isValid() and size.width() > 0 and size.height() > 0:
        reader.setScaledSize(size.scaled(QSize(SAMPLE, SAMPLE), Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return []
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    pixels = []
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixel(x, y)
            pixels.append(((c >> 16) & 255, (c >> 8) & 255, c & 255))
    return pixels


def colors_for(path):
    """The palette for a wallpaper ("tesseract" or a picture path) as #RRGGBB strings."""
    if not path or path == "tesseract":
        return to_hex(palette(DEFAULT_HUE, DEFAULT_HUE2, 1.0))
    pixels = read_pixels(path)
    if not pixels:
        return None
    return to_hex(pick(pixels))
