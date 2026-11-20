"""Write the OziOS Plasma style: the frames of the bar, the dock, popups and tool tips.

    python3 tools/make-plasma-style.py

Every frame is a rounded sheet of the colour scheme's background with a one
pixel rim. The colours are not fixed here: Plasma replaces the stylesheet
classes with the colours of the scheme in use, so each OziOS theme (and any
other colour scheme) gives the frames its own colours.

Three sets are written: the normal one, `translucent/` (used when the
compositor can blur what is behind) and `opaque/` (used when compositing is
off, for example in game mode).
"""
import json
import math
import os

root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
OUT = os.path.join(root, "desktop", "plasma-style", "ozios")

CENTER = 16          # size of the middle tile; it is stretched
PIECES = ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright")

# name: radius, rim class, rim opacity, content margin, fill opacity (normal, translucent)
# The normal set is drawn when nothing blurs what is behind (KWin's blur is off, or the
# machine renders in software, as a virtual machine without 3D does). A popup or a tool tip
# that lets the window behind it show through is hard to read there, so those are solid;
# measured in a Plasma session, even 0.97 left the text behind a menu readable.
FRAMES = {
    "widgets/panel-background": (12, "ColorScheme-Highlight", 0.30, 4, (0.94, 0.74)),
    "dialogs/background": (12, "ColorScheme-Highlight", 0.22, 8, (1.0, 0.82)),
    "widgets/tooltip": (8, "ColorScheme-Text", 0.12, 6, (1.0, 0.86)),
    "widgets/background": (12, "ColorScheme-Text", 0.10, 8, (0.86, 0.66)),
}
SETS = {"": 0, "translucent/": 1, "opaque/": None}

# Soft shadows under popups, tool tips and the floating bar and dock, which make them
# float above what is behind. Each is the frame's own rounded sheet moved down a
# little (the light comes from above) and blurred. KWin draws it from the eight
# "shadow-*" pieces, placed around the frame by the "shadow-hint-*-margin" sizes.
# name: how far the blur reaches, how far down it is moved, darkest opacity
SHADOWS = {
    "dialogs/background": (22, 6, 0.5),
    "widgets/tooltip": (12, 3, 0.4),
    "widgets/panel-background": (16, 4, 0.45),
}
SHADOW_X = 170       # the shadow pieces are laid out right of the frame and its mask
SHADOW_STOPS = 13    # gradient stops per piece; enough for the curve to look smooth

STYLE = """<style type="text/css" id="current-color-scheme">
.ColorScheme-Background { color:#080b10; }
.ColorScheme-Text { color:#f4fcff; }
.ColorScheme-Highlight { color:#00e5ff; }
</style>"""


def n(value):
    return ("%.3f" % value).rstrip("0").rstrip(".")


def shape(d, cls, opacity):
    return '<path class="%s" style="fill:currentColor;fill-opacity:%s" d="%s"/>' % (cls, n(opacity), d)


def rect(x, y, w, h):
    return "M %s,%s H %s V %s H %s Z" % (n(x), n(y), n(x + w), n(y + h), n(x))


def corner(piece, x, y, r, b):
    """(rim ring, fill) paths for a corner tile whose box starts at x, y."""
    i = r - b
    if piece == "topleft":
        rim = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s A %s,%s 0 0 0 %s,%s Z" % (
            n(x), n(y + r), n(r), n(r), n(x + r), n(y), n(x + r), n(y + b), n(i), n(i), n(x + b), n(y + r))
        fill = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s Z" % (n(x + b), n(y + r), n(i), n(i), n(x + r), n(y + b), n(x + r), n(y + r))
    elif piece == "topright":
        rim = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s A %s,%s 0 0 0 %s,%s Z" % (
            n(x), n(y), n(r), n(r), n(x + r), n(y + r), n(x + r - b), n(y + r), n(i), n(i), n(x), n(y + b))
        fill = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s Z" % (n(x), n(y + b), n(i), n(i), n(x + r - b), n(y + r), n(x), n(y + r))
    elif piece == "bottomleft":
        rim = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s A %s,%s 0 0 0 %s,%s Z" % (
            n(x + r), n(y + r), n(r), n(r), n(x), n(y), n(x + b), n(y), n(i), n(i), n(x + r), n(y + r - b))
        fill = "M %s,%s A %s,%s 0 0 0 %s,%s L %s,%s Z" % (n(x + b), n(y), n(i), n(i), n(x + r), n(y + r - b), n(x + r), n(y))
    else:  # bottomright
        rim = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s A %s,%s 0 0 0 %s,%s Z" % (
            n(x + r), n(y), n(r), n(r), n(x), n(y + r), n(x), n(y + r - b), n(i), n(i), n(x + r - b), n(y))
        fill = "M %s,%s A %s,%s 0 0 1 %s,%s L %s,%s Z" % (n(x + r - b), n(y), n(i), n(i), n(x), n(y + r - b), n(x), n(y))
    return rim, fill


def boxes(x0, y0, r, c=CENTER):
    cols = (x0, x0 + r, x0 + r + c)
    rows = (y0, y0 + r, y0 + r + c)
    size = {0: r, 1: c, 2: r}
    out = {}
    for index, piece in enumerate(PIECES):
        row, col = divmod(index, 3)
        out[piece] = (cols[col], rows[row], size[col], size[row])
    return out


def blurred(distance, extent):
    """How dark a blurred edge is at `distance` past it (negative inside), from 1 to 0.

    A Gaussian blur turns a hard edge into half an error function: half dark on
    the edge itself, fully dark `extent` inside, gone `extent` outside (three sigmas).
    """
    sigma = extent / 3.0
    return 0.5 * math.erfc(distance / (sigma * math.sqrt(2)))


def stops(darkest, extent, near, far):
    """Gradient stops from offset 0 (`near` past the shadow's edge) to 1 (`far` past it)."""
    out = []
    for k in range(SHADOW_STOPS):
        at = k / (SHADOW_STOPS - 1)
        strength = blurred(near + (far - near) * at, extent)
        out.append('<stop offset="%s" stop-color="#000000" stop-opacity="%s"/>' % (n(at), n(darkest * strength)))
    return "".join(out)


def shadow_margins(extent, offset):
    """(top, right, bottom, left): how far the shadow reaches past the frame."""
    return extent - offset, extent, extent + offset, extent


def shadow_parts(radius, extent, offset, darkest):
    """The eight shadow pieces, their gradients and the margin hints, as SVG elements.

    KWin puts each corner piece at a corner of the frame grown by the margins, at
    the piece's own size, and stretches the edge pieces between them. The corner
    pieces are sized so their inner corner is the centre of the shadow's corner
    circle; the edge pieces then carry exactly the straight stretch of the shadow,
    and corner and edge gradients meet without a seam.
    """
    r, e, dy, c = radius, extent, offset, CENTER
    top, right, bottom, left = shadow_margins(e, dy)
    cw, ch = e + r, e + r                    # corner pieces
    x0, y0 = SHADOW_X, 0
    col = (x0, x0 + cw, x0 + cw + c)
    row = (y0, y0 + ch, y0 + ch + c)
    defs, parts = [], []

    def linear(name, x1, y1, x2, y2):
        """From (x1, y1), `e` inside the shadow's edge, to (x2, y2), `e` outside it."""
        defs.append('<linearGradient id="g-%s" gradientUnits="userSpaceOnUse" x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>'
                    % (name, n(x1), n(y1), n(x2), n(y2), stops(darkest, e, -e, e)))

    def radial(name, cx, cy):
        """Around the shadow's corner circle, from its centre out to `e` past it."""
        defs.append('<radialGradient id="g-%s" gradientUnits="userSpaceOnUse" cx="%s" cy="%s" r="%s">%s</radialGradient>'
                    % (name, n(cx), n(cy), n(r + e), stops(darkest, e, -r, e)))

    def piece(name, x, y, w, h):
        parts.append('<g id="shadow-%s"><rect x="%s" y="%s" width="%s" height="%s" style="fill:url(#g-%s)"/></g>'
                     % (name, n(x), n(y), n(w), n(h), name))

    radial("topleft", col[0] + cw, row[0] + ch); piece("topleft", col[0], row[0], cw, ch)
    radial("topright", col[2], row[0] + ch); piece("topright", col[2], row[0], cw, ch)
    radial("bottomleft", col[0] + cw, row[2]); piece("bottomleft", col[0], row[2], cw, ch)
    radial("bottomright", col[2], row[2]); piece("bottomright", col[2], row[2], cw, ch)
    # The top piece reaches down to the shadow's edge, `offset` below the frame's top.
    linear("top", 0, row[1] + e, 0, row[1] - e); piece("top", col[1], row[1] - e, c, e)
    # The bottom piece starts at the frame's bottom; the shadow's edge is `offset` lower.
    linear("bottom", 0, row[2] + dy - e, 0, row[2] + dy + e); piece("bottom", col[1], row[2], c, bottom)
    linear("left", col[1] + e, 0, col[1] - e, 0); piece("left", col[1] - e, row[1], e, c)
    linear("right", col[2] - e, 0, col[2] + e, 0); piece("right", col[2], row[1], e, c)

    hy = row[2] + ch + 4
    parts.append('<rect id="shadow-hint-top-margin" x="%d" y="%d" width="2" height="%d" style="fill:#ff00ff"/>' % (x0, hy, top))
    parts.append('<rect id="shadow-hint-bottom-margin" x="%d" y="%d" width="2" height="%d" style="fill:#ff00ff"/>' % (x0 + 4, hy, bottom))
    parts.append('<rect id="shadow-hint-left-margin" x="%d" y="%d" width="%d" height="2" style="fill:#ff00ff"/>' % (x0 + 8, hy, left))
    parts.append('<rect id="shadow-hint-right-margin" x="%d" y="%d" width="%d" height="2" style="fill:#ff00ff"/>' % (x0 + 8, hy + 4, right))
    size = (col[2] + cw, hy + max(top, bottom) + 2)
    return ["<defs>" + "".join(defs) + "</defs>"] + parts, size


def frame_svg(radius, rim_class, rim_opacity, margin, fill_opacity, shadow=None):
    r, b = radius, 1
    parts = []
    for piece, (x, y, w, h) in boxes(0, 0, r).items():
        if piece in ("topleft", "topright", "bottomleft", "bottomright"):
            rim, fill = corner(piece, x, y, r, b)
            body = shape(fill, "ColorScheme-Background", fill_opacity) + shape(rim, rim_class, rim_opacity)
        elif piece == "top":
            body = shape(rect(x, y + b, w, h - b), "ColorScheme-Background", fill_opacity) + shape(rect(x, y, w, b), rim_class, rim_opacity)
        elif piece == "bottom":
            body = shape(rect(x, y, w, h - b), "ColorScheme-Background", fill_opacity) + shape(rect(x, y + h - b, w, b), rim_class, rim_opacity)
        elif piece == "left":
            body = shape(rect(x + b, y, w - b, h), "ColorScheme-Background", fill_opacity) + shape(rect(x, y, b, h), rim_class, rim_opacity)
        elif piece == "right":
            body = shape(rect(x, y, w - b, h), "ColorScheme-Background", fill_opacity) + shape(rect(x + w - b, y, b, h), rim_class, rim_opacity)
        else:
            body = shape(rect(x, y, w, h), "ColorScheme-Background", fill_opacity)
        parts.append('<g id="%s">%s</g>' % (piece, body))

    # The shape the compositor blurs behind: the same sheet, solid.
    for piece, (x, y, w, h) in boxes(100, 0, r).items():
        if piece in ("topleft", "topright", "bottomleft", "bottomright"):
            _, d = corner(piece, x, y, r, 0)      # with no rim the fill is the whole quarter disc
        else:
            d = rect(x, y, w, h)
        parts.append('<path id="mask-%s" style="fill:#000000" d="%s"/>' % (piece, d))

    # Content margins, read from the size of these marks.
    parts.append('<rect id="hint-top-margin" x="0" y="100" width="2" height="%d" style="fill:#ff00ff"/>' % margin)
    parts.append('<rect id="hint-bottom-margin" x="4" y="100" width="2" height="%d" style="fill:#ff00ff"/>' % margin)
    parts.append('<rect id="hint-left-margin" x="8" y="100" width="%d" height="2" style="fill:#ff00ff"/>' % margin)
    parts.append('<rect id="hint-right-margin" x="8" y="104" width="%d" height="2" style="fill:#ff00ff"/>' % margin)
    parts.append('<rect id="hint-stretch-borders" x="20" y="100" width="2" height="2" style="fill:#ff6600"/>')

    width, height = 160, 110
    if shadow:
        extra, (w, h) = shadow_parts(radius, *shadow)
        parts += extra
        width, height = max(width, w), max(height, h)

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- Written by tools/make-plasma-style.py; edit that instead. -->\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n' % (width, height, width, height)
            + STYLE + "\n" + "\n".join(parts) + "\n</svg>\n")


METADATA = {
    "KPackageStructure": "Plasma/Theme",
    "KPlugin": {
        "Authors": [{"Name": "OziOS"}],
        "Category": "",
        "Description": "Ink glass in the colours of the scheme in use",
        "EnabledByDefault": True,
        "Id": "ozios",
        "License": "MIT",
        "Name": "OziOS",
        "Version": "0.2",
        "Website": "https://github.com/OziiDev/OziOS",
    },
    "X-Plasma-API": "5.0",
}

PLASMARC = """\
[ContrastEffect]
enabled=true
contrast=0.25
intensity=1.4
saturation=1.8

[BlurBehindEffect]
enabled=true

[AdaptiveTransparency]
enabled=true
"""


def files():
    """{relative path: text} of the whole style."""
    out = {"metadata.json": json.dumps(METADATA, indent=4) + "\n", "plasmarc": PLASMARC}
    for prefix, which in SETS.items():
        for name, (radius, rim_class, rim_opacity, margin, fills) in FRAMES.items():
            fill = 1.0 if which is None else fills[which]
            out[prefix + name + ".svg"] = frame_svg(radius, rim_class, rim_opacity, margin, fill, SHADOWS.get(name))
    return out


def main():
    for rel, text in files().items():
        path = os.path.join(OUT, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(os.path.relpath(path, root))


if __name__ == "__main__":
    main()
