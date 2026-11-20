"""OziOS colour themes: a dark ink with one bright accent each, and one light.

A theme is a KDE colour scheme. Everything the desktop draws takes its colours
from the scheme in use: the OziOS Plasma style (bar, dock and popups), the dock,
the launcher, the wallpaper and the window frames. Switching the scheme
switches all of them at once, without restarting anything.

    ozi theme                list the themes and mark the one in use
    ozi theme <name>         switch to it
    ozi theme --json         the same list for the control widget

The .colors files in branding/themes are written from the table below by
tools/make-themes.py; a test checks that they agree.
"""
import json
import os
import subprocess
from dataclasses import dataclass

from .i18n import tr

RGB = tuple


@dataclass(frozen=True)
class Theme:
    id: str
    scheme: str               # colour scheme name and file name (without .colors)
    title: str                # the English name; title() gives it in the user's language
    ink: RGB                  # window background
    raised: RGB               # alternate background, tool tips
    control: RGB              # buttons
    view: RGB                 # lists and text fields
    text: RGB
    muted: RGB
    accent: RGB
    accent_alt: RGB
    light: bool = False
    # Text on the accent and its quieter shades; worked out from the accent when left out.
    on_accent: RGB = None
    on_accent_quiet: RGB = None
    on_accent_visited: RGB = None
    on_accent_negative: RGB = None
    on_accent_neutral: RGB = None
    on_accent_positive: RGB = None

    @property
    def file_name(self):
        return self.scheme + ".colors"


def _mix(a, b, amount):
    return tuple(int(round(x + (y - x) * amount)) for x, y in zip(a, b))


def _plus(a, b):
    return tuple(min(255, x + y) for x, y in zip(a, b))


THEMES = (
    # The original look; its values are kept exactly as they were.
    Theme("cyan", "OziOS", "Cyan", ink=(8, 11, 16), raised=(14, 19, 27), control=(20, 27, 38), view=(11, 15, 22),
          text=(244, 252, 255), muted=(128, 150, 160), accent=(0, 229, 255), accent_alt=(0, 170, 195),
          on_accent=(8, 11, 16), on_accent_quiet=(20, 45, 55), on_accent_visited=(30, 40, 90),
          on_accent_negative=(150, 0, 30), on_accent_neutral=(110, 65, 0), on_accent_positive=(0, 85, 50)),
    Theme("aurora", "OziOSAurora", "Aurora", ink=(11, 8, 20), raised=(19, 15, 33), control=(28, 22, 47), view=(14, 11, 26),
          text=(246, 243, 255), muted=(150, 140, 178), accent=(176, 140, 255), accent_alt=(128, 96, 232)),
    Theme("ember", "OziOSEmber", "Ember", ink=(16, 10, 8), raised=(27, 18, 14), control=(39, 26, 20), view=(21, 13, 10),
          text=(255, 247, 240), muted=(172, 146, 132), accent=(255, 140, 64), accent_alt=(222, 102, 34)),
    Theme("mint", "OziOSMint", "Mint", ink=(7, 14, 12), raised=(12, 23, 20), control=(18, 33, 29), view=(9, 18, 15),
          text=(240, 255, 250), muted=(130, 166, 153), accent=(60, 230, 160), accent_alt=(30, 182, 122)),
    Theme("rose", "OziOSRose", "Rose", ink=(16, 8, 11), raised=(27, 14, 19), control=(39, 20, 28), view=(21, 10, 14),
          text=(255, 242, 246), muted=(176, 136, 151), accent=(255, 94, 140), accent_alt=(219, 60, 106)),
    Theme("frost", "OziOSFrost", "Frost (light)", ink=(242, 246, 249), raised=(232, 238, 243), control=(224, 232, 238),
          view=(251, 252, 253), text=(12, 19, 25), muted=(92, 111, 122), accent=(0, 145, 172), accent_alt=(0, 116, 140),
          light=True, on_accent=(255, 255, 255), on_accent_quiet=(214, 240, 245)),
)
BY_ID = {theme.id: theme for theme in THEMES}
DEFAULT = "cyan"

# Status colours: readable on the theme's own background.
DARK_STATUS = {"negative": (255, 85, 110), "neutral": (255, 190, 90), "positive": (60, 230, 160), "visited": (120, 170, 255)}
LIGHT_STATUS = {"negative": (196, 34, 66), "neutral": (176, 110, 0), "positive": (18, 140, 84), "visited": (70, 80, 200)}


def _c(rgb):
    return "%d,%d,%d" % rgb


def _group(name, background, alternate, theme, status):
    accent = theme.accent
    return [
        "[%s]" % name,
        "BackgroundNormal=" + _c(background),
        "BackgroundAlternate=" + _c(alternate),
        "ForegroundNormal=" + _c(theme.text),
        "ForegroundInactive=" + _c(theme.muted),
        "ForegroundActive=" + _c(accent if not theme.light else theme.accent_alt),
        "ForegroundLink=" + _c(accent if not theme.light else theme.accent_alt),
        "ForegroundVisited=" + _c(status["visited"]),
        "ForegroundNegative=" + _c(status["negative"]),
        "ForegroundNeutral=" + _c(status["neutral"]),
        "ForegroundPositive=" + _c(status["positive"]),
        "DecorationFocus=" + _c(accent),
        "DecorationHover=" + _c(accent),
        "",
    ]


def render(theme):
    """The theme as the text of a KDE colour scheme file."""
    status = LIGHT_STATUS if theme.light else DARK_STATUS
    on = theme.on_accent or theme.ink
    lines = [
        "[General]",
        "ColorScheme=" + theme.scheme,
        "Name=" + ("OziOS" if theme.id == DEFAULT else "OziOS " + theme.title),
        "shadeSortColumn=true",
        "",
        "[KDE]",
        "contrast=4",
        "",
        "[ColorEffects:Disabled]",
        "ColorAmount=0",
        "ColorEffect=0",
        "ContrastAmount=0.65",
        "ContrastEffect=1",
        "IntensityAmount=0.1",
        "IntensityEffect=2",
        "",
        "[ColorEffects:Inactive]",
        "ChangeSelectionColor=true",
        "ColorAmount=0.025",
        "ColorEffect=2",
        "ContrastAmount=0.1",
        "ContrastEffect=2",
        "Enable=false",
        "IntensityAmount=0",
        "IntensityEffect=0",
        "",
    ]
    lines += _group("Colors:Window", theme.ink, theme.raised, theme, status)
    lines += _group("Colors:View", theme.view, _plus(theme.view, (5, 7, 9)) if not theme.light else theme.raised, theme, status)
    lines += _group("Colors:Button", theme.control, _plus(theme.control, (6, 8, 10)) if not theme.light else theme.raised, theme, status)
    lines += [
        "[Colors:Selection]",
        "BackgroundNormal=" + _c(theme.accent),
        "BackgroundAlternate=" + _c(theme.accent_alt),
        "ForegroundNormal=" + _c(on),
        "ForegroundInactive=" + _c(theme.on_accent_quiet or _mix(on, theme.accent, 0.35)),
        "ForegroundActive=" + _c(on),
        "ForegroundLink=" + _c(on),
        "ForegroundVisited=" + _c(theme.on_accent_visited or _mix(on, (30, 40, 90), 0.5)),
        "ForegroundNegative=" + _c(theme.on_accent_negative or _mix(on, (150, 0, 30), 0.8)),
        "ForegroundNeutral=" + _c(theme.on_accent_neutral or _mix(on, (110, 65, 0), 0.8)),
        "ForegroundPositive=" + _c(theme.on_accent_positive or _mix(on, (0, 85, 50), 0.8)),
        "DecorationFocus=" + _c(theme.accent),
        "DecorationHover=" + _c(theme.accent),
        "",
    ]
    if theme.light:
        tooltip = (theme.view, theme.raised)
    else:
        tooltip = (theme.raised, theme.control)
    lines += _group("Colors:Tooltip", tooltip[0], tooltip[1], theme, status)
    # Complementary is what Plasma draws dark surfaces with (lock screen, on-screen messages);
    # it stays dark in the light theme too.
    if theme.light:
        dark = BY_ID[DEFAULT]
        complementary = Theme("x", "x", "x", ink=dark.ink, raised=dark.raised, control=dark.control, view=dark.view,
                              text=dark.text, muted=dark.muted, accent=theme.accent, accent_alt=theme.accent_alt)
        lines += _group("Colors:Complementary", dark.ink, dark.raised, complementary, DARK_STATUS)
    else:
        lines += _group("Colors:Complementary", theme.ink, theme.raised, theme, status)
    lines += _group("Colors:Header", theme.ink, theme.raised, theme, status)
    lines += [
        "[WM]",
        "activeBackground=" + _c(theme.ink),
        "activeBlend=" + _c(theme.accent),
        "activeForeground=" + _c(theme.text),
        "inactiveBackground=" + _c(theme.ink),
        "inactiveBlend=" + _c(theme.raised),
        "inactiveForeground=" + _c(theme.muted),
    ]
    return "\n".join(lines) + "\n"


# --- the theme in use ---------------------------------------------------------------

def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def scheme_in_use(kdeglobals=None):
    """The colour scheme named in kdeglobals, or ""."""
    path = kdeglobals or os.path.join(config_home(), "kdeglobals")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return ""
    group = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            group = line[1:-1]
        elif group == "General" and line.startswith("ColorScheme="):
            return line.split("=", 1)[1].strip()
    return ""


def current(kdeglobals=None):
    """The id of the OziOS theme in use, or "" when the scheme is not one of ours."""
    scheme = scheme_in_use(kdeglobals)
    for theme in THEMES:
        if theme.scheme == scheme:
            return theme.id
    return ""


def title(theme):
    """The theme's name in the user's language."""
    return {
        "cyan": tr("Cyan"),
        "aurora": tr("Aurora"),
        "ember": tr("Ember"),
        "mint": tr("Mint"),
        "rose": tr("Rose"),
        "frost": tr("Frost (light)"),
    }.get(theme.id, theme.title)


def listing(kdeglobals=None):
    now = current(kdeglobals)
    return [{"id": t.id, "name": title(t), "accent": "#%02x%02x%02x" % t.accent,
             "background": "#%02x%02x%02x" % t.ink, "light": t.light, "current": t.id == now} for t in THEMES]


def apply(theme_id, run=subprocess.run):
    """Switch to a theme. Returns the command's exit status."""
    theme = BY_ID[theme_id]
    try:
        done = run(["plasma-apply-colorscheme", theme.scheme], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return 127
    return done.returncode


def main(argv=None, out=print, run=subprocess.run, kdeglobals=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi theme", description=tr("Choose the colours of the desktop."))
    parser.add_argument("name", nargs="?", choices=[t.id for t in THEMES], help=tr("the theme to switch to"))
    parser.add_argument("--json", action="store_true", help=tr("machine-readable output"))
    args = parser.parse_args(argv)
    if args.name:
        code = apply(args.name, run=run)
        if code == 127:
            out(tr("plasma-apply-colorscheme is missing; run this inside the desktop session"))
            return 1
        if code != 0:
            out(tr("The colours could not be changed"))
            return 1
        out(tr("Theme: {name}", name=title(BY_ID[args.name])))
        return 0
    items = listing(kdeglobals)
    if args.json:
        out(json.dumps(items, ensure_ascii=False))
        return 0
    for item in items:
        out("%s %-8s %s" % ("*" if item["current"] else " ", item["id"], item["name"]))
    return 0
