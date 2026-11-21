"""The look of the desktop in one place: the windows' corners, outline, glow and
title bars, the gaps between tiles and tiling from the start, how fast things
move, and blur. `ozi look` and the Look app (apps/ozi-look) both use it.

Three presets set everything at once:

    fluid    floating windows, glow and blur, the usual speed: the OziOS look
    tiling   every desktop tiled, no title bars, quick: a tiling desktop
    light    no glow, no blur, small corners, quick: for older or virtual machines

Values go into the files KWin and the OziOS window frames read (kwinrc,
ozidecorationrc, kdeglobals) through kwriteconfig6, then KWin is asked to read
them again, so a change shows at once.
"""
import json
import os
import shutil
import subprocess

from .i18n import tr

SPEEDS = {"off": 0.0, "fast": 0.5, "normal": 0.7, "relaxed": 1.0}

# name -> (file, group, key, kind, default, lowest, highest)
SETTINGS = {
    "radius": ("ozidecorationrc", "Decoration", "CornerRadius", "int", 10, 0, 24),
    "outline": ("ozidecorationrc", "Decoration", "OutlineWidth", "int", 2, 0, 4),
    "glow": ("ozidecorationrc", "Decoration", "Glow", "bool", True, None, None),
    "titlebar": ("ozidecorationrc", "Decoration", "TitleBar", "bool", True, None, None),
    "gaps": ("kwinrc", "Script-ozios-tiling", "Gap", "int", 10, 0, 40),
    "tiling": ("kwinrc", "Script-ozios-tiling", "TileByDefault", "bool", False, None, None),
    "blur": ("kwinrc", "Plugins", "blurEnabled", "bool", True, None, None),
    "speed": ("kdeglobals", "KDE", "AnimationDurationFactor", "speed", "normal", None, None),
}
ORDER = ("radius", "outline", "glow", "titlebar", "gaps", "tiling", "blur", "speed")

PRESETS = {
    "fluid": {"radius": 10, "outline": 2, "glow": True, "titlebar": True, "gaps": 10, "tiling": False,
              "blur": True, "speed": "normal"},
    "tiling": {"radius": 8, "outline": 2, "glow": True, "titlebar": False, "gaps": 8, "tiling": True,
               "blur": True, "speed": "fast"},
    "light": {"radius": 6, "outline": 1, "glow": False, "titlebar": True, "gaps": 6, "tiling": False,
              "blur": False, "speed": "fast"},
}
PRESET_ORDER = ("fluid", "tiling", "light")


def preset_title(name):
    return {"fluid": tr("Fluid"), "tiling": tr("Tiling"), "light": tr("Light")}[name]


def preset_text(name):
    return {
        "fluid": tr("Floating windows with a glow, blur and the usual speed"),
        "tiling": tr("Every desktop tiled, no title bars, quick"),
        "light": tr("No glow or blur, small corners: for older computers"),
    }[name]


def setting_title(name):
    return {
        "radius": tr("Corner radius"), "outline": tr("Outline"), "glow": tr("Glow"),
        "titlebar": tr("Title bars"), "gaps": tr("Gaps between tiles"), "tiling": tr("Tile every desktop"),
        "blur": tr("Blur"), "speed": tr("Animation speed"),
    }[name]


def speed_title(name):
    return {"off": tr("Off"), "fast": tr("Fast"), "normal": tr("Normal"), "relaxed": tr("Relaxed")}[name]


# --- reading ---------------------------------------------------------------------------------

def config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def read_ini(path):
    """{group: {key: value}} of a KDE configuration file; nested groups keep their brackets."""
    out, group = {}, None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            group = line[1:-1]
            out.setdefault(group, {})
        elif group is not None and "=" in line:
            key, value = line.split("=", 1)
            out[group][key.strip()] = value.strip()
    return out


def _bool(text, default):
    text = str(text).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return default


def _speed_name(factor):
    """The named speed nearest to an AnimationDurationFactor."""
    try:
        value = float(factor)
    except (TypeError, ValueError):
        return "normal"
    if value <= 0.05:
        return "off"
    return min((name for name in SPEEDS if name != "off"), key=lambda name: abs(SPEEDS[name] - value))


def read_all(home=None):
    """The current value of every setting."""
    home = home or config_home()
    files = {}
    values = {}
    for name in ORDER:
        file, group, key, kind, default = SETTINGS[name][:5]
        if file not in files:
            files[file] = read_ini(os.path.join(home, file))
        raw = files[file].get(group, {}).get(key)
        if raw is None:
            values[name] = default
        elif kind == "int":
            try:
                values[name] = int(float(raw))
            except ValueError:
                values[name] = default
        elif kind == "bool":
            values[name] = _bool(raw, default)
        else:
            values[name] = _speed_name(raw)
    return values


def current_preset(values):
    """The preset whose every value matches, or ""."""
    for name in PRESET_ORDER:
        if all(values.get(key) == value for key, value in PRESETS[name].items()):
            return name
    return ""


def state(home=None):
    """What the Look app shows: the values, the preset they match, and the names to show."""
    values = read_all(home)
    return {
        "values": values,
        "preset": current_preset(values),
        "presets": [{"id": name, "name": preset_title(name), "text": preset_text(name)} for name in PRESET_ORDER],
        "speeds": [{"id": name, "name": speed_title(name)} for name in SPEEDS],
        "ranges": {name: [SETTINGS[name][5], SETTINGS[name][6]] for name in ORDER if SETTINGS[name][3] == "int"},
    }


# --- writing ---------------------------------------------------------------------------------

def check(name, value):
    """The value in the form it is stored in, or ValueError with a sentence for the person."""
    if name not in SETTINGS:
        raise ValueError(tr("There is no setting called {name}", name=name))
    kind, low, high = SETTINGS[name][3], SETTINGS[name][5], SETTINGS[name][6]
    if kind == "int":
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            raise ValueError(tr("{name} takes a number from {low} to {high}", name=name, low=low, high=high))
        if not low <= number <= high:
            raise ValueError(tr("{name} takes a number from {low} to {high}", name=name, low=low, high=high))
        return number
    if kind == "bool":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text not in ("on", "off", "true", "false", "yes", "no", "1", "0"):
            raise ValueError(tr("{name} is on or off", name=name))
        return _bool(text, False)
    if value not in SPEEDS:
        raise ValueError(tr("speed is one of: {names}", names=", ".join(SPEEDS)))
    return value


def _qdbus():
    return shutil.which("qdbus6") or shutil.which("qdbus-qt6") or shutil.which("qdbus")


def _write(run, file, group, key, text, notify=False):
    command = ["kwriteconfig6", "--file", file, "--group", group, "--key", key]
    if notify:
        command.append("--notify")
    run(command + [text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_values(changes, run=subprocess.run, qdbus=None):
    """Store each {name: value} and let KWin, the frames and the tiling script take them up."""
    clean = {name: check(name, value) for name, value in changes.items()}
    for name, value in clean.items():
        file, group, key, kind = SETTINGS[name][:4]
        if kind == "bool":
            _write(run, file, group, key, "true" if value else "false")
        elif kind == "speed":
            _write(run, file, group, key, str(SPEEDS[value]), notify=True)
        else:
            _write(run, file, group, key, str(value))
        if name == "gaps":
            # A little more at the screen's edges than between windows.
            _write(run, file, group, "OuterGap", str(value + 2 if value else 0))
    qdbus = qdbus if qdbus is not None else _qdbus()
    if qdbus:
        if "blur" in clean:
            method = "loadEffect" if clean["blur"] else "unloadEffect"
            run([qdbus, "org.kde.KWin", "/Effects", "org.kde.kwin.Effects." + method, "blur"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # The frames reread ozidecorationrc and the tiling script its settings.
        run([qdbus, "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return clean


def set_value(name, value, run=subprocess.run, qdbus=None):
    return set_values({name: value}, run=run, qdbus=qdbus)


def apply_preset(name, run=subprocess.run, qdbus=None):
    if name not in PRESETS:
        raise ValueError(tr("There is no preset called {name}", name=name))
    return set_values(dict(PRESETS[name]), run=run, qdbus=qdbus)


# --- ozi look ----------------------------------------------------------------------------------

def _shown(name, value):
    if SETTINGS[name][3] == "bool":
        return tr("on") if value else tr("off")
    if SETTINGS[name][3] == "speed":
        return speed_title(value)
    return str(value)


def main(argv=None, out=print, run=subprocess.run, home=None, qdbus=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog="ozi look", description=tr("How the desktop looks and moves: a preset, or one setting at a time."),
        epilog=tr("Settings: {names}. Presets: {presets}.", names=", ".join(ORDER), presets=", ".join(PRESET_ORDER)))
    parser.add_argument("name", nargs="?", help=tr("preset, or the name of a setting"))
    parser.add_argument("value", nargs="?", help=tr("the preset's name, or the setting's new value"))
    parser.add_argument("--json", action="store_true", help=tr("machine-readable output"))
    args = parser.parse_args(argv)

    try:
        if args.name == "preset":
            if not args.value:
                out(tr("Presets: {presets}", presets=", ".join(PRESET_ORDER)))
                return 2
            apply_preset(args.value, run=run, qdbus=qdbus)
            out(tr("Look: {name}", name=preset_title(args.value)))
            return 0
        if args.name:
            if args.value is None:
                values = read_all(home)
                if args.name not in values:
                    raise ValueError(tr("There is no setting called {name}", name=args.name))
                out(_shown(args.name, values[args.name]))
                return 0
            stored = set_value(args.name, args.value, run=run, qdbus=qdbus)
            out("%s: %s" % (setting_title(args.name), _shown(args.name, stored[args.name])))
            return 0
    except ValueError as err:
        out(str(err))
        return 2

    now = state(home)
    if args.json:
        out(json.dumps(now, ensure_ascii=False))
        return 0
    preset = now["preset"]
    out(tr("Preset: {name}", name=preset_title(preset) if preset else tr("your own")))
    for name in ORDER:
        out("  %-9s %-22s %s" % (name, setting_title(name), _shown(name, now["values"][name])))
    return 0
