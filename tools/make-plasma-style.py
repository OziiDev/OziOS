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
import os

root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
OUT = os.path.join(root, "desktop", "plasma-style", "ozios")

CENTER = 16          # size of the middle tile; it is stretched
PIECES = ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright")

# name: radius, rim class, rim opacity, content margin, fill opacity (normal, translucent)
FRAMES = {
    "widgets/panel-background": (12, "ColorScheme-Highlight", 0.30, 4, (0.94, 0.74)),
    "dialogs/background": (12, "ColorScheme-Highlight", 0.22, 8, (0.97, 0.82)),
    "widgets/tooltip": (8, "ColorScheme-Text", 0.12, 6, (0.97, 0.86)),
    "widgets/background": (12, "ColorScheme-Text", 0.10, 8, (0.86, 0.66)),
}
SETS = {"": 0, "translucent/": 1, "opaque/": None}

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


def frame_svg(radius, rim_class, rim_opacity, margin, fill_opacity):
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

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- Written by tools/make-plasma-style.py; edit that instead. -->\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="110" viewBox="0 0 160 110">\n'
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
            out[prefix + name + ".svg"] = frame_svg(radius, rim_class, rim_opacity, margin, fill)
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
