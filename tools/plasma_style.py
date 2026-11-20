"""Draw the OziOS Plasma style's frames the way Plasma does, outside Plasma.

Plasma (KSvg) cuts each frame SVG into nine named pieces, keeps the corners at
their size, stretches the edges and the middle, and swaps the stylesheet colours
for the colour scheme's. This does the same with Qt's own SVG renderer, which is
also what KSvg uses underneath, so the pictures and tests show the frames as a
session would draw them (without the blur behind them).

    frame(painter, "widgets/panel-background", rect, theme_id)
    frame(painter, "dialogs/background", rect, theme_id, borders=("top", "bottom", "left", "right"))
"""
import os
import re

from PyQt6.QtCore import QByteArray, QRectF
from PyQt6.QtSvg import QSvgRenderer

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STYLE = os.path.join(ROOT, "desktop", "plasma-style", "ozios")
ALL = ("top", "bottom", "left", "right")

import sys  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "python"))
from ozipkg import themes  # noqa: E402

_cache = {}


def recoloured(text, theme_id):
    """The SVG with its stylesheet set to a theme's colours, as KSvg does for the scheme in use."""
    theme = themes.BY_ID[theme_id]
    colours = {"ColorScheme-Background": theme.ink, "ColorScheme-Text": theme.text, "ColorScheme-Highlight": theme.accent}
    for name, rgb in colours.items():
        text = re.sub(r"(\.%s\s*\{\s*color:)\s*#[0-9a-fA-F]{6}" % name, r"\g<1>#%02x%02x%02x" % rgb, text)
    return text


def renderer(name, theme_id, variant=""):
    key = (name, theme_id, variant)
    if key not in _cache:
        with open(os.path.join(STYLE, *(variant.split("/") if variant else []), *(name + ".svg").split("/")), encoding="utf-8") as fh:
            _cache[key] = QSvgRenderer(QByteArray(recoloured(fh.read(), theme_id).encode("utf-8")))
    return _cache[key]


def margins(name, theme_id, variant=""):
    """(left, top, right, bottom): how far the content stays from the frame's edge."""
    svg = renderer(name, theme_id, variant)
    return (svg.boundsOnElement("hint-left-margin").width(), svg.boundsOnElement("hint-top-margin").height(),
            svg.boundsOnElement("hint-right-margin").width(), svg.boundsOnElement("hint-bottom-margin").height())


def frame(painter, name, rect, theme_id, borders=ALL, variant=""):
    """Draw a frame into `rect` (QRectF); `borders` are the edges that have a border, as for a panel at a screen edge."""
    svg = renderer(name, theme_id, variant)
    size = {piece: svg.boundsOnElement(piece) for piece in ("topleft", "topright", "bottomleft", "bottomright")}
    left = size["topleft"].width() if "left" in borders else 0
    right = size["topright"].width() if "right" in borders else 0
    top = size["topleft"].height() if "top" in borders else 0
    bottom = size["bottomleft"].height() if "bottom" in borders else 0
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    middle_w, middle_h = w - left - right, h - top - bottom
    pieces = [("center", QRectF(x + left, y + top, middle_w, middle_h))]
    if "top" in borders:
        pieces.append(("top", QRectF(x + left, y, middle_w, top)))
    if "bottom" in borders:
        pieces.append(("bottom", QRectF(x + left, y + h - bottom, middle_w, bottom)))
    if "left" in borders:
        pieces.append(("left", QRectF(x, y + top, left, middle_h)))
    if "right" in borders:
        pieces.append(("right", QRectF(x + w - right, y + top, right, middle_h)))
    if "top" in borders and "left" in borders:
        pieces.append(("topleft", QRectF(x, y, left, top)))
    if "top" in borders and "right" in borders:
        pieces.append(("topright", QRectF(x + w - right, y, right, top)))
    if "bottom" in borders and "left" in borders:
        pieces.append(("bottomleft", QRectF(x, y + h - bottom, left, bottom)))
    if "bottom" in borders and "right" in borders:
        pieces.append(("bottomright", QRectF(x + w - right, y + h - bottom, right, bottom)))
    for piece, target in pieces:
        if target.width() > 0 and target.height() > 0:
            svg.render(painter, piece, target)
