"""The boot menu (Limine) dressed like the desktop: the wallpaper the user
chose, a little darker, and the desktop's colours for the text.

Run as root by ozi-boot-look.service when the computer starts and when it
shuts down, so a new wallpaper shows at the next start. It reads the
desktop.json of the user who changed their look last and rewrites only the
theme lines at the top of limine.conf; the boot entries stay as they are.

    ozi-boot-look            update if the look changed since last time
    ozi-boot-look --force    update anyway
    ozi-boot-look --dry-run  print what limine.conf would become
"""
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys

from . import shell

CONFS = ("/boot/limine.conf", "/efi/limine.conf", "/boot/efi/limine.conf", "/boot/EFI/limine/limine.conf")
SPLASH = "limine-splash.png"
DEFAULT_SPLASH = "/usr/share/ozios/branding/limine-splash.png"
LOGO = "/usr/share/ozios/branding/logo.svg"
STAMP = "/var/lib/ozios/boot-look"
SIZE = (1920, 1080)

# Theme lines this tool owns; any other top-level option is left alone.
OWNED = re.compile(r"^\s*(wallpaper|wallpaper_style|backdrop|term_palette|term_palette_bright|term_background"
                   r"|term_foreground|term_background_bright|term_foreground_bright|term_margin"
                   r"|term_margin_gradient|interface_branding|interface_branding_colou?r"
                   r"|interface_help_colou?r|interface_help_colou?r_bright)\s*:")
OLD_COMMENTS = re.compile(r"^\s*#\s*(CachyOS Limine theme|Author: diegons490|OziOS boot look)")
MARK = "# OziOS boot look: follows the desktop (ozi-boot-look); edits here are replaced"


def newest_user_look():
    """(home, look) of the person who changed their desktop look last."""
    best = None
    for user in pwd.getpwall():
        if user.pw_uid < 1000 or user.pw_uid >= 60000 or not user.pw_dir.startswith("/home/"):
            continue
        env = {"HOME": user.pw_dir}
        path = shell.desktop_config_path(env)
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, user, env)
    if best is None:
        return None, None, dict(shell.LOOK_DEFAULTS)
    _, user, env = best
    return user, env, shell.look(env)


def usable_picture(path, user):
    """A picture the user could open themself: root must not copy anything else."""
    if not path or path == "tesseract" or not os.path.isabs(path):
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    if not os.path.isfile(path):
        return None
    if st.st_mode & 0o004 or (user is not None and st.st_uid == user.pw_uid):
        return path
    return None


def palette_for(look):
    return shell.palette(look["theme"], look.get("colors"))


def _h(colour):
    return colour.lstrip("#").upper()


def theme_lines(colors, splash_ref):
    ink, text, muted = _h(colors["ink"]), _h(colors["text"]), _h(colors["muted"])
    accent, accent2 = _h(colors["accent"]), _h(colors["accent2"])
    palette = [ink, "E5484D", accent, "F5A524", accent2, accent2, accent, text]
    bright = [muted, "FF6B6F", accent, "FFC861", accent2, accent2, accent, "FFFFFF"]
    return [
        MARK,
        "wallpaper: " + splash_ref,
        "wallpaper_style: stretched",
        "backdrop: " + ink,
        "term_palette: " + ";".join(palette),
        "term_palette_bright: " + ";".join(bright),
        # A dark, see-through sheet behind the menu keeps it readable on any picture.
        "term_background: 50" + ink,
        "term_foreground: " + text,
        "term_background_bright: " + ink,
        "term_foreground_bright: FFFFFF",
        "term_margin: 64",
        "term_margin_gradient: 24",
        "interface_branding: OziOS",
        "interface_branding_colour: " + accent,
        "interface_help_colour: " + muted,
        "interface_help_colour_bright: " + accent,
    ]


def rewrite(conf_text, lines):
    """limine.conf with the theme lines at the top replaced by `lines`."""
    source = conf_text.splitlines()
    first_entry = next((i for i, l in enumerate(source) if l.startswith("/")), len(source))
    head = []
    for line in source[:first_entry]:
        if OWNED.match(line) or OLD_COMMENTS.match(line):
            continue
        if not line.strip() and (not head or not head[-1].strip()):
            continue  # no runs of empty lines
        head.append(line)
    while head and not head[-1].strip():
        head.pop()
    out = head + ([""] if head else []) + lines + [""] + source[first_entry:]
    return "\n".join(out).rstrip("\n") + "\n"


def mount_point(path):
    try:
        out = subprocess.run(["findmnt", "-no", "TARGET", "--target", path],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return out.splitlines()[0] if out else "/"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "/"


def render_splash(picture, colors, out_path):
    """The picture cut to 16:9, a little darker toward the middle where the menu is."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter, QRadialGradient
    _app = QGuiApplication.instance() or QGuiApplication(["ozi-boot-look"])  # noqa: F841
    image = QImage(picture) if picture else QImage()
    if image.isNull():
        image = QImage(DEFAULT_SPLASH)
    if image.isNull():
        return False
    w, h = SIZE
    image = image.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                         Qt.TransformationMode.SmoothTransformation)
    image = image.copy((image.width() - w) // 2, (image.height() - h) // 2, w, h)
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    painter = QPainter(image)
    ink = QColor(colors["ink"])
    glow = QRadialGradient(QPointF(w / 2, h / 2), w * 0.6)
    middle, edge = QColor(ink), QColor(ink)
    middle.setAlphaF(0.55)
    edge.setAlphaF(0.25)
    glow.setColorAt(0.0, middle)
    glow.setColorAt(1.0, edge)
    painter.fillRect(0, 0, w, h, glow)
    draw_mark(painter, w, h, colors, image)
    painter.end()
    tmp = out_path + ".tmp"
    if not image.save(tmp, "PNG"):
        return False
    os.replace(tmp, out_path)
    return True


def _logo_path():
    here = os.path.dirname(os.path.abspath(__file__))
    checkout = os.path.join(here, "..", "..", "branding", "logo.svg")
    return checkout if os.path.isfile(checkout) else LOGO


def busyness(image, x, y, w, h):
    """How much is going on in a part of the picture (detail and contrast,
    roughly 0..1): the mark goes where it covers the least."""
    from PyQt6.QtCore import Qt
    part = image.copy(int(x), int(y), int(w), int(h)).scaled(
        48, 24, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    lum = [[0.0] * 48 for _ in range(24)]
    for j in range(24):
        for i in range(48):
            c = part.pixelColor(i, j)
            lum[j][i] = (0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF())
    flat = [v for row in lum for v in row]
    mean = sum(flat) / len(flat)
    spread = (sum((v - mean) ** 2 for v in flat) / len(flat)) ** 0.5
    edges = sum(abs(lum[j][i] - lum[j][i + 1]) + abs(lum[j][i] - lum[j + 1][i])
                for j in range(23) for i in range(47)) / (23 * 47)
    return spread + 2 * edges + 0.3 * mean


def mark_place(image, w, h, box_w, box_h):
    """(x, y) of the quieter bottom corner. The bottom middle stays free:
    the boot menu counts down there."""
    margin_x, margin_y = w * 0.045, h * 0.07
    places = [(margin_x, h - margin_y - box_h), (w - margin_x - box_w, h - margin_y - box_h)]
    return min(places, key=lambda p: busyness(image, p[0] - 20, p[1] - 20, box_w + 40, box_h + 40))


def draw_mark(painter, w, h, colors, image=None):
    """The OziOS mark and name in a quiet corner of the user's wallpaper: the
    picture is theirs, the boot screen still says whose system it is. "Ozi"
    in the text colour, "OS" in the wallpaper's accent."""
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QRadialGradient
    from PyQt6.QtSvg import QSvgRenderer

    size = h * 0.072                      # logo height
    font = QFont("Overpass", 1)
    font.setPixelSize(int(size * 0.66))
    font.setWeight(QFont.Weight.Bold)
    metrics = QFontMetricsF(font)
    ozi_w, os_w = metrics.horizontalAdvance("Ozi"), metrics.horizontalAdvance("OS")
    gap = size * 0.26
    box_w, box_h = size + gap + ozi_w + os_w, size
    x, y = mark_place(image, w, h, box_w, box_h) if image is not None else ((w - box_w) / 2, h - h * 0.07 - box_h)

    # A soft shade just behind the mark keeps it readable on a bright picture.
    shade = QRadialGradient(QPointF(x + box_w / 2, y + box_h / 2), box_w * 0.95)
    inner, outer = QColor(colors["ink"]), QColor(colors["ink"])
    inner.setAlphaF(0.62)
    outer.setAlphaF(0.0)
    shade.setColorAt(0.0, inner)
    shade.setColorAt(1.0, outer)
    painter.save()
    painter.translate(x + box_w / 2, y + box_h / 2)
    painter.scale(1.0, 0.42)
    painter.translate(-(x + box_w / 2), -(y + box_h / 2))
    painter.fillRect(QRectF(x - box_w, y - box_w, box_w * 3, box_h + box_w * 2), shade)
    painter.restore()

    logo = QSvgRenderer(_logo_path())
    if logo.isValid():
        logo.render(painter, QRectF(x, y, size, size))
    painter.setFont(font)
    baseline = y + (size + metrics.capHeight()) / 2
    painter.setPen(QColor(colors["text"]))
    painter.drawText(QPointF(x + size + gap, baseline), "Ozi")
    painter.setPen(QColor(colors["accent"]))
    painter.drawText(QPointF(x + size + gap + ozi_w, baseline), "OS")


def fingerprint(look, picture):
    stamp = {"look": {k: look.get(k) for k in ("theme", "colors", "wallpaper")}, "picture": picture}
    if picture:
        st = os.stat(picture)
        stamp["mtime"] = st.st_mtime
        stamp["size"] = st.st_size
    return hashlib.sha256(json.dumps(stamp, sort_keys=True).encode()).hexdigest()


def main(argv=()):
    force = "--force" in argv
    dry = "--dry-run" in argv
    confs = [c for c in CONFS if os.path.isfile(c)]
    if not confs:
        print("ozi-boot-look: no limine.conf; nothing to do")
        return 0
    user, _env, look = newest_user_look()
    picture = usable_picture(look.get("wallpaper"), user)
    colors = palette_for(look)
    if look["theme"] == shell.AUTO and not look.get("colors") and picture:
        from . import wallcolors
        colors = palette_for(dict(look, colors=wallcolors.colors_for(picture)))
    stamp = fingerprint(look, picture)
    if not force and not dry:
        try:
            with open(STAMP) as f:
                if f.read().strip() == stamp:
                    return 0
        except OSError:
            pass
    for conf in confs:
        folder = os.path.dirname(conf)
        splash = os.path.join(folder, SPLASH)
        ref = "boot():/" + os.path.relpath(splash, mount_point(folder))
        with open(conf, encoding="utf-8") as f:
            text = f.read()
        new = rewrite(text, theme_lines(colors, ref))
        if dry:
            print(new)
            continue
        if not render_splash(picture, colors, splash):
            print("ozi-boot-look: could not draw", splash, file=sys.stderr)
            continue
        if new != text:
            tmp = conf + ".ozi-tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(new)
            os.chmod(tmp, os.stat(conf).st_mode & 0o7777)
            os.replace(tmp, conf)
        print("ozi-boot-look: updated", conf)
    if not dry:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        with open(STAMP, "w") as f:
            f.write(stamp + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
