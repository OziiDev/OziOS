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
import re
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


# --- the terminal ------------------------------------------------------------------------

# The ANSI colours keep their meaning in every theme (red is red); a light background
# needs darker ones to stay readable.
DARK_ANSI = ((255, 85, 110), (255, 130, 150), (60, 230, 160), (120, 245, 195), (255, 190, 90), (255, 215, 140),
             (70, 150, 255), (130, 185, 255), (175, 130, 255), (205, 175, 255), (0, 229, 255), (130, 242, 255),
             (200, 225, 232), (244, 252, 255))
LIGHT_ANSI = ((196, 34, 66), (226, 60, 90), (18, 140, 84), (30, 170, 105), (176, 110, 0), (205, 135, 0),
              (30, 100, 200), (60, 130, 225), (130, 70, 200), (155, 100, 220), (0, 130, 160), (0, 155, 185),
              (70, 80, 90), (12, 19, 25))
PROFILE = "OziOS.profile"


def render_konsole(theme):
    """The theme as a Konsole colour scheme (same name as the KDE colour scheme)."""
    if theme.light:
        black, black_intense, ansi, bright = (40, 48, 56), (90, 100, 110), LIGHT_ANSI, (0, 0, 0)
    else:
        black, black_intense, ansi, bright = theme.control, _mix(theme.control, theme.text, 0.2), DARK_ANSI, (255, 255, 255)
        if theme.id == DEFAULT:
            black_intense = (70, 90, 105)
    sections = [
        ("General", ["Description=" + ("OziOS" if theme.id == DEFAULT else "OziOS " + theme.title),
                     "Opacity=%s" % ("0.96" if theme.light else "0.92"), "Blur=true", "Wallpaper="]),
        ("Background", ["Color=" + _c(theme.ink)]),
        ("BackgroundIntense", ["Color=" + _c(theme.raised)]),
        ("BackgroundFaint", ["Color=" + _c(theme.ink)]),
        ("Foreground", ["Color=" + _c(theme.text)]),
        ("ForegroundIntense", ["Color=" + _c(bright)]),
        ("ForegroundFaint", ["Color=" + _c(theme.muted)]),
        ("Color0", ["Color=" + _c(black)]),
        ("Color0Intense", ["Color=" + _c(black_intense)]),
    ]
    for number in range(1, 8):
        sections.append(("Color%d" % number, ["Color=" + _c(ansi[(number - 1) * 2])]))
        sections.append(("Color%dIntense" % number, ["Color=" + _c(ansi[(number - 1) * 2 + 1])]))
    return "\n\n".join("[%s]\n%s" % (name, "\n".join(lines)) for name, lines in sections) + "\n"


def data_home():
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def set_konsole(theme, home=None, system_dirs=("/usr/share/konsole",)):
    """Point the user's OziOS terminal profile at the theme's colours. Returns whether it did."""
    home = home or data_home()
    user = os.path.join(home, "konsole", PROFILE)
    source = user if os.path.isfile(user) else next(
        (os.path.join(d, PROFILE) for d in system_dirs if os.path.isfile(os.path.join(d, PROFILE))), None)
    if source is None:
        return False
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    line = "ColorScheme=" + theme.scheme
    if re.search(r"(?m)^ColorScheme=.*$", text):
        text = re.sub(r"(?m)^ColorScheme=.*$", line, text)
    elif re.search(r"(?m)^\[Appearance\]\s*$", text):
        text = re.sub(r"(?m)^\[Appearance\]\s*$", "[Appearance]\n" + line, text, count=1)
    else:
        text = "[Appearance]\n%s\n\n%s" % (line, text)
    os.makedirs(os.path.dirname(user), exist_ok=True)
    with open(user, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


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


def app_palette(theme_id):
    """The colours the OziOS apps draw with (apps/OziUi/Theme.qml), for a theme.

    `cyan` is the accent of any theme; `mid` and `far` are the accent sinking
    into the background, the depth ramp of the design. The cyan theme keeps the
    values it was designed with."""
    theme = BY_ID[theme_id]

    def hexa(rgb):
        return "#%02x%02x%02x" % rgb
    if theme.id == DEFAULT:
        mid, far = (0, 152, 176), (0, 70, 92)
    else:
        mid, far = _mix(theme.accent, theme.ink, 0.35), _mix(theme.accent, theme.ink, 0.7)
    return {"ink": hexa(theme.ink), "raised": hexa(theme.raised), "control": hexa(theme.control),
            "cyan": hexa(theme.accent), "mid": hexa(mid), "far": hexa(far), "ice": hexa(theme.text),
            "muted": hexa(theme.muted), "onAccent": hexa(theme.on_accent or theme.ink), "light": theme.light}


def theme_for_apps(environ=None, kdeglobals=None):
    """The theme the apps should use: OZIOS_THEME if set (tests, previews), else the one in use."""
    environ = os.environ if environ is None else environ
    wanted = environ.get("OZIOS_THEME", "")
    if wanted in BY_ID:
        return wanted
    return current(kdeglobals) or DEFAULT


def listing(kdeglobals=None):
    now = current(kdeglobals)
    return [{"id": t.id, "name": title(t), "accent": "#%02x%02x%02x" % t.accent,
             "background": "#%02x%02x%02x" % t.ink, "light": t.light, "current": t.id == now} for t in THEMES]


def apply(theme_id, run=subprocess.run, home=None):
    """Switch to a theme: the desktop's colour scheme, then the terminal's. Returns the exit status
    of plasma-apply-colorscheme."""
    theme = BY_ID[theme_id]
    try:
        done = run(["plasma-apply-colorscheme", theme.scheme], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return 127
    if done.returncode == 0:
        try:
            set_konsole(theme, home=home)
        except OSError:
            pass                        # the desktop changed; a terminal profile that can not be written is no reason to fail
    return done.returncode


# --- day and night ------------------------------------------------------------------------

AUTO_FILE = "theme-auto.json"
TIMER = "ozios-theme-auto.timer"
AUTO_DEFAULTS = {"day": "frost", "night": DEFAULT, "sunrise": "07:00", "sunset": "19:00"}


def auto_path(config=None):
    return os.path.join(config or config_home(), "ozios", AUTO_FILE)


def _minutes(text):
    hours, _, minutes = text.partition(":")
    return int(hours) * 60 + int(minutes or 0)


def auto_choice(now, settings):
    """The theme the clock asks for: the day theme from sunrise to sunset, the night theme otherwise.
    `now` is a datetime.time."""
    minute = now.hour * 60 + now.minute
    day = _minutes(settings["sunrise"]) <= minute < _minutes(settings["sunset"])
    return settings["day"] if day else settings["night"]


def read_auto(config=None):
    try:
        with open(auto_path(config), encoding="utf-8") as fh:
            settings = json.load(fh)
    except (OSError, ValueError):
        return None
    merged = dict(AUTO_DEFAULTS, **{k: v for k, v in settings.items() if k in AUTO_DEFAULTS})
    if merged["day"] not in BY_ID or merged["night"] not in BY_ID:
        return None
    try:
        _minutes(merged["sunrise"]), _minutes(merged["sunset"])
    except ValueError:
        return None
    return merged


def auto_tick(run=subprocess.run, home=None, config=None, kdeglobals=None, now=None):
    """Run by the timer: switch when the clock asks for another theme than the one in use.
    Returns the theme switched to, or ""."""
    import datetime
    settings = read_auto(config)
    if settings is None:
        return ""
    wanted = auto_choice(now or datetime.datetime.now().time(), settings)
    if current(kdeglobals) == wanted:
        return ""
    return wanted if apply(wanted, run=run, home=home) == 0 else ""


def _timer(run, enable):
    command = ["systemctl", "--user", "enable" if enable else "disable", "--now", TIMER]
    try:
        return run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except FileNotFoundError:
        return False


def stop_auto(run=subprocess.run, config=None):
    """End the day and night switching, if it is on: a theme picked by hand wins. Returns whether it was on."""
    if read_auto(config) is None:
        return False
    try:
        os.remove(auto_path(config))
    except OSError:
        pass
    _timer(run, False)
    return True


def main(argv=None, out=print, run=subprocess.run, kdeglobals=None, home=None, config=None, now=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi theme", description=tr("Choose the colours of the desktop."))
    parser.add_argument("name", nargs="?", choices=[t.id for t in THEMES] + ["auto"], help=tr("the theme to switch to"))
    parser.add_argument("state", nargs="?", choices=["on", "off"], default="on", help=argparse.SUPPRESS)
    parser.add_argument("--day", choices=[t.id for t in THEMES], help=tr("with auto: the theme from sunrise to sunset"))
    parser.add_argument("--night", choices=[t.id for t in THEMES], help=tr("with auto: the theme at night"))
    parser.add_argument("--auto-tick", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help=tr("machine-readable output"))
    args = parser.parse_args(argv)

    if args.auto_tick:
        switched = auto_tick(run=run, home=home, config=config, kdeglobals=kdeglobals, now=now)
        if switched:
            out(tr("Theme: {name}", name=title(BY_ID[switched])))
        return 0
    if args.name == "auto":
        path = auto_path(config)
        if args.state == "off":
            stop_auto(run, config)
            _timer(run, False)
            out(tr("The colours no longer follow the time of day"))
            return 0
        settings = dict(read_auto(config) or AUTO_DEFAULTS)
        if args.night is None and not read_auto(config):
            settings["night"] = next((t.id for t in THEMES if t.id == current(kdeglobals) and not t.light), DEFAULT)
        settings.update({k: v for k, v in (("day", args.day), ("night", args.night)) if v})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
        if not _timer(run, True):
            out(tr("The timer could not be started; the colours change at the next login."))
        auto_tick(run=run, home=home, config=config, kdeglobals=kdeglobals, now=now)
        out(tr("Day and night: {day} by day, {night} at night",
               day=title(BY_ID[settings["day"]]), night=title(BY_ID[settings["night"]])))
        return 0
    if args.name:
        code = apply(args.name, run=run, home=home)
        if code == 127:
            out(tr("plasma-apply-colorscheme is missing; run this inside the desktop session"))
            return 1
        if code != 0:
            out(tr("The colours could not be changed"))
            return 1
        stop_auto(run, config)                 # a theme picked by hand ends the automatic switching
        out(tr("Theme: {name}", name=title(BY_ID[args.name])))
        return 0
    items = listing(kdeglobals)
    if args.json:
        out(json.dumps(items, ensure_ascii=False))
        return 0
    for item in items:
        out("%s %-8s %s" % ("*" if item["current"] else " ", item["id"], item["name"]))
    return 0
