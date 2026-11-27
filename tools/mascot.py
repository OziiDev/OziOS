#!/usr/bin/env python3
"""Ozi-chan, the OziOS mascot: a small cat girl in an OziOS hoodie, drawn from
shapes so she scales to any size and takes any colours.

    python3 tools/mascot.py          writes branding/mascot/*.svg

`ozi_chan()` returns her as an SVG group for other pictures (the wallpapers
use it); the box she is drawn in is 400 wide and 520 tall.
"""
import os

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = os.path.join(HERE, "..", "branding", "mascot")

# Her own colours; a wallpaper may give others for hoodie, eyes and hair.
DEFAULT = {
    "hair": "#2A2F45",
    "hair_light": "#454C6B",
    "skin": "#FFE6D8",
    "skin_shade": "#F6C9B6",
    "hoodie": "#45F582",
    "hoodie_shade": "#2CC466",
    "eyes": "#22C97A",
    "eyes_dark": "#0E6B45",
    "legs": "#20232F",
    "blush": "#FF8FAE",
    "line": "#1B1D2A",
}


def ozi_chan(x=0, y=0, scale=1.0, colors=None, wave=True, flip=False, wink=False):
    """She, standing, the top left of her box at (x, y)."""
    c = dict(DEFAULT, **(colors or {}))
    flip_t = " translate(400 0) scale(-1 1)" if flip else ""
    g = ['<g transform="translate(%.1f %.1f) scale(%.3f)%s">' % (x, y, scale, flip_t)]
    add = g.append
    # The tail, behind everything: a long S that ends in a light tip.
    add('<path d="M 262 440 C 330 450, 362 404, 344 346 C 330 300, 352 268, 372 274" '
        'stroke="%s" stroke-width="26" fill="none" stroke-linecap="round"/>' % c["hair"])
    add('<path d="M 356 280 C 362 272, 370 270, 374 274" stroke="%s" stroke-width="26" fill="none" stroke-linecap="round"/>'
        % c["hoodie"])
    # Long hair at the back.
    add('<path d="M 78 205 C 60 300, 70 380, 108 420 L 292 420 C 330 380, 340 300, 322 205 Z" fill="%s"/>' % c["hair"])
    # Legs and shoes.
    add('<rect x="156" y="430" width="34" height="62" rx="15" fill="%s"/>' % c["legs"])
    add('<rect x="210" y="430" width="34" height="62" rx="15" fill="%s"/>' % c["legs"])
    add('<ellipse cx="170" cy="494" rx="26" ry="14" fill="%s"/>' % c["line"])
    add('<ellipse cx="232" cy="494" rx="26" ry="14" fill="%s"/>' % c["line"])
    add('<ellipse cx="164" cy="489" rx="10" ry="4" fill="#FFFFFF" opacity="0.35"/>')
    add('<ellipse cx="226" cy="489" rx="10" ry="4" fill="#FFFFFF" opacity="0.35"/>')
    # The hoodie: a soft bell with a pocket and the OziOS ring.
    add('<path d="M 140 318 C 120 360, 112 410, 118 446 Q 200 462 282 446 C 288 410, 280 360, 260 318 Z" fill="%s"/>'
        % c["hoodie"])
    add('<path d="M 118 446 Q 200 462 282 446 L 282 436 Q 200 452 118 436 Z" fill="%s"/>' % c["hoodie_shade"])
    add('<path d="M 160 400 Q 200 392 240 400 L 236 430 Q 200 436 164 430 Z" fill="%s"/>' % c["hoodie_shade"])
    add('<circle cx="200" cy="362" r="17" fill="none" stroke="#FFFFFF" stroke-width="6"/>')
    add('<circle cx="212" cy="350" r="5" fill="#FFFFFF"/>')
    # Strings of the hood.
    add('<path d="M 186 318 L 182 352" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round"/>')
    add('<path d="M 214 318 L 218 352" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round"/>')
    add('<circle cx="182" cy="355" r="4" fill="#FFFFFF"/><circle cx="218" cy="355" r="4" fill="#FFFFFF"/>')
    # Arms: the left one hangs, the right one waves (or hangs too).
    add('<path d="M 146 328 C 118 352, 104 384, 110 410" stroke="%s" stroke-width="30" fill="none" stroke-linecap="round"/>'
        % c["hoodie"])
    add('<circle cx="111" cy="414" r="16" fill="%s"/>' % c["skin"])
    if wave:
        add('<path d="M 254 330 C 290 318, 312 290, 318 256" stroke="%s" stroke-width="30" fill="none" stroke-linecap="round"/>'
            % c["hoodie"])
        add('<circle cx="320" cy="246" r="17" fill="%s"/>' % c["skin"])
        # A paw: three little toe lines.
        for dx in (-6, 0, 6):
            add('<path d="M %d 236 L %d 243" stroke="%s" stroke-width="2.5" stroke-linecap="round"/>'
                % (320 + dx, 320 + dx, c["skin_shade"]))
        for a in (0, 1):
            add('<path d="M %d %d q 8 -6 4 -16" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.7"/>'
                % (346 + a * 12, 236 + a * 16, c["hoodie"]))
    else:
        add('<path d="M 254 328 C 282 352, 296 384, 290 410" stroke="%s" stroke-width="30" fill="none" stroke-linecap="round"/>'
            % c["hoodie"])
        add('<circle cx="289" cy="414" r="16" fill="%s"/>' % c["skin"])
    # Neck and the hood around it.
    add('<rect x="182" y="290" width="36" height="34" rx="12" fill="%s"/>' % c["skin_shade"])
    add('<path d="M 132 322 Q 200 290 268 322 Q 200 346 132 322 Z" fill="%s"/>' % c["hoodie_shade"])
    # Cat ears, with pink inside.
    add('<path d="M 92 150 L 96 52 L 168 104 Z" fill="%s" stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
        % (c["hair"], c["hair"]))
    add('<path d="M 308 150 L 304 52 L 232 104 Z" fill="%s" stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
        % (c["hair"], c["hair"]))
    add('<path d="M 106 128 L 108 76 L 150 106 Z" fill="%s" opacity="0.9"/>' % c["blush"])
    add('<path d="M 294 128 L 292 76 L 250 106 Z" fill="%s" opacity="0.9"/>' % c["blush"])
    # The face.
    add('<ellipse cx="200" cy="210" rx="112" ry="100" fill="%s"/>' % c["skin"])
    # Hair on top and the fringe: soft points over the forehead.
    add('<path d="M 84 214 C 70 120, 140 84, 200 84 C 262 84, 330 120, 316 214 '
        'C 300 170, 286 158, 270 150 L 262 182 L 244 148 L 226 178 L 210 146 L 192 180 L 176 148 '
        'L 160 178 L 146 152 L 136 190 C 118 176, 100 190, 84 214 Z" fill="%s"/>' % c["hair"])
    add('<path d="M 118 120 C 150 96, 190 92, 220 98" stroke="%s" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.8"/>'
        % c["hair_light"])
    # Side locks framing the face.
    add('<path d="M 86 196 C 80 250, 90 300, 120 330 C 112 290, 116 240, 122 200 Z" fill="%s"/>' % c["hair"])
    add('<path d="M 314 196 C 320 250, 310 300, 280 330 C 288 290, 284 240, 278 200 Z" fill="%s"/>' % c["hair"])
    # A hair clip in the hoodie's colour: a little ">_".
    add('<rect x="236" y="134" width="40" height="22" rx="7" fill="%s" transform="rotate(-14 256 145)"/>' % c["hoodie"])
    add('<path d="M 245 140 l 7 5 l -7 5" stroke="%s" stroke-width="3" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round" transform="rotate(-14 256 145)"/>' % c["line"])
    add('<path d="M 257 151 l 9 0" stroke="%s" stroke-width="3" stroke-linecap="round" transform="rotate(-14 256 145)"/>'
        % c["line"])
    # Eyes: big and shiny.
    for ex, closed in ((150, False), (250, wink)):
        if closed:
            add('<path d="M %d 226 Q %d 210 %d 226" stroke="%s" stroke-width="6" fill="none" stroke-linecap="round"/>'
                % (ex - 24, ex, ex + 24, c["line"]))
            continue
        add('<ellipse cx="%d" cy="226" rx="25" ry="31" fill="#FFFFFF"/>' % ex)
        add('<ellipse cx="%d" cy="230" rx="21" ry="27" fill="%s"/>' % (ex, c["eyes"]))
        add('<ellipse cx="%d" cy="238" rx="14" ry="17" fill="%s"/>' % (ex, c["eyes_dark"]))
        add('<ellipse cx="%d" cy="246" rx="12" ry="7" fill="%s" opacity="0.55"/>' % (ex, c["eyes"]))
        add('<circle cx="%d" cy="218" r="8" fill="#FFFFFF"/>' % (ex - 8))
        add('<circle cx="%d" cy="244" r="4" fill="#FFFFFF" opacity="0.9"/>' % (ex + 9))
        # The upper lash line, with a flick at the outer corner.
        flick = "M %d 206 l -8 -7" % (ex - 26) if ex < 200 else "M %d 205 l 8 -7" % (ex + 26)
        add('<path d="M %d 206 Q %d 186 %d 205 %s" stroke="%s" stroke-width="5.5" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round"/>' % (ex - 26, ex, ex + 26, flick, c["line"]))
    # Brows, blush, a cat mouth and a fang.
    add('<path d="M 132 178 q 18 -8 36 -2" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.8"/>' % c["hair"])
    add('<path d="M 232 176 q 18 -6 36 2" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.8"/>' % c["hair"])
    add('<ellipse cx="128" cy="268" rx="20" ry="10" fill="%s" opacity="0.55"/>' % c["blush"])
    add('<ellipse cx="272" cy="268" rx="20" ry="10" fill="%s" opacity="0.55"/>' % c["blush"])
    add('<path d="M 186 266 q 7 9 14 0 q 7 9 14 0" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/>' % c["line"])
    add('<path d="M 205 270 l 3 7 l 3 -6" fill="#FFFFFF" stroke="%s" stroke-width="1.5" stroke-linejoin="round"/>' % c["line"])
    g.append("</g>")
    return "".join(g)


def standalone(colors=None, **kw):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 520" width="400" height="520">\n'
            + ozi_chan(colors=colors, **kw) + "\n</svg>\n")


VARIANTS = {
    "ozi-chan.svg": dict(),
    "ozi-chan-goz-kirp.svg": dict(wink=True),
    "ozi-chan-mor.svg": dict(colors={"hoodie": "#9B7BFF", "hoodie_shade": "#7656E0", "eyes": "#B394FF", "eyes_dark": "#4B2FA8"}),
    "ozi-chan-pembe.svg": dict(colors={"hoodie": "#FF7EB6", "hoodie_shade": "#E25A97", "eyes": "#FF9CC6", "eyes_dark": "#A0275E"}),
    "ozi-chan-mavi.svg": dict(colors={"hoodie": "#4FB6FF", "hoodie_shade": "#2E8FE0", "eyes": "#57C3FF", "eyes_dark": "#155C9E"}),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, kw in VARIANTS.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(standalone(**kw))
        print(name)


if __name__ == "__main__":
    main()
