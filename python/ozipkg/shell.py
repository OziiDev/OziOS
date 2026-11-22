"""ozi-shell's logic: applications, search, the dock's pins and the system
status the bar shows. No Qt here, so it runs under unittest anywhere.
"""
import configparser
import json
import os
import re
import shutil
import subprocess

DEFAULT_PINS = ("org.kde.dolphin", "firefox", "org.kde.konsole", "ozi-store", "ozi-look", "systemsettings")


def data_dirs(environ=os.environ):
    home = environ.get("XDG_DATA_HOME") or os.path.join(environ.get("HOME", "/root"), ".local/share")
    system = (environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    return [home] + [d for d in system if d]


def _localized(section, key, lang):
    for candidate in (f"{key}[{lang}]", f"{key}[{lang.split('_')[0]}]", key):
        if candidate in section:
            return section[candidate]
    return ""


def parse_desktop_entry(text, lang="tr_TR"):
    """One .desktop file as a dict, or None if it should not be listed."""
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    try:
        parser.read_string(text)
    except configparser.Error:
        return None
    if not parser.has_section("Desktop Entry"):
        return None
    entry = parser["Desktop Entry"]
    if entry.get("Type", "Application") != "Application":
        return None
    if entry.get("NoDisplay", "false").lower() == "true" or entry.get("Hidden", "false").lower() == "true":
        return None
    desktops = ("OziOS", "KDE")
    only = [d for d in entry.get("OnlyShowIn", "").split(";") if d]
    if only and not any(d in only for d in desktops):
        return None
    if any(d in entry.get("NotShowIn", "").split(";") for d in desktops):
        return None
    exec_line = entry.get("Exec", "")
    if not exec_line:
        return None
    return {
        "name": _localized(entry, "Name", lang),
        "generic": _localized(entry, "GenericName", lang),
        "comment": _localized(entry, "Comment", lang),
        "keywords": _localized(entry, "Keywords", lang),
        "icon": entry.get("Icon", ""),
        "exec": exec_line,
        "terminal": entry.get("Terminal", "false").lower() == "true",
        "categories": [c for c in entry.get("Categories", "").split(";") if c],
        "wm_class": entry.get("StartupWMClass", ""),
    }


def applications(environ=os.environ, lang=None):
    """Every listed application, by desktop file id; earlier data dirs win."""
    lang = lang or (environ.get("LANG", "tr_TR").split(".")[0] or "tr_TR")
    found = {}
    for base in data_dirs(environ):
        root = os.path.join(base, "applications")
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for name in files:
                if not name.endswith(".desktop"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                app_id = rel[: -len(".desktop")].replace(os.sep, "-")
                if app_id in found:
                    continue
                try:
                    with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as f:
                        entry = parse_desktop_entry(f.read(), lang)
                except OSError:
                    continue
                found[app_id] = entry
    apps = [dict(e, id=i) for i, e in found.items() if e]
    apps.sort(key=lambda a: a["name"].casefold())
    return apps


_FIELD = re.compile(r"%[fFuUdDnNickvm%]")


def command_for(exec_line, terminal=False):
    """The argv to start an Exec= line with no files given."""
    import shlex
    try:
        argv = shlex.split(exec_line)
    except ValueError:
        argv = exec_line.split()
    argv = [_FIELD.sub(lambda m: "%" if m.group() == "%%" else "", a) for a in argv]
    argv = [a for a in argv if a]
    if terminal:
        argv = ["konsole", "-e"] + argv
    return argv


_TR = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def _fold(text):
    return text.translate(_TR).casefold()


def search(apps, query, limit=40):
    """Best matches first: name start, word start, anywhere, then other fields."""
    q = _fold(query.strip())
    if not q:
        return list(apps)[:limit]
    scored = []
    for app in apps:
        name = _fold(app["name"])
        others = _fold(" ".join([app.get("generic", ""), app.get("comment", ""), app.get("keywords", ""), app["id"]]))
        if name.startswith(q):
            score = 0
        elif any(w.startswith(q) for w in re.split(r"[\s\-_.]+", name)):
            score = 1
        elif q in name:
            score = 2
        elif q in others:
            score = 3
        else:
            continue
        scored.append((score, len(name), app))
    scored.sort(key=lambda s: (s[0], s[1], s[2]["name"].casefold()))
    return [s[2] for s in scored[:limit]]


def match_app(apps_by_id, app_id):
    """The desktop entry for a window's app_id (exact id, last part, or WM class)."""
    if not app_id:
        return None
    if app_id in apps_by_id:
        return apps_by_id[app_id]
    low = app_id.casefold()
    for key, app in apps_by_id.items():
        if key.casefold() == low or key.casefold().split(".")[-1] == low.split(".")[-1]:
            return app
        if app.get("wm_class", "").casefold() == low:
            return app
    return None


def desktop_config_path(environ=os.environ):
    base = environ.get("XDG_CONFIG_HOME") or os.path.join(environ.get("HOME", "/root"), ".config")
    return os.path.join(base, "ozios", "desktop.json")


def read_config(environ=os.environ):
    try:
        with open(desktop_config_path(environ), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_config(changes, environ=os.environ):
    data = read_config(environ)
    data.update(changes)
    path = desktop_config_path(environ)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return data


def pins(apps_by_id, environ=os.environ):
    wanted = read_config(environ).get("dock") or list(DEFAULT_PINS)
    return [i for i in wanted if i in apps_by_id]


def dock_items(apps_by_id, pinned, windows):
    """Pinned apps in order, then running apps that are not pinned.

    Each item: id, name, icon, pinned, windows (ids), active.
    """
    items = []
    index = {}
    for app_id in pinned:
        app = apps_by_id.get(app_id)
        if not app:
            continue
        index[app_id] = len(items)
        items.append({"id": app_id, "name": app["name"], "icon": app["icon"], "pinned": True,
                      "windows": [], "active": False, "exec": app["exec"], "terminal": app["terminal"]})
    for w in windows:
        app = match_app(apps_by_id, w.get("app_id", ""))
        key = app["id"] if app else (w.get("app_id") or "window-%s" % w["id"])
        if key not in index:
            index[key] = len(items)
            items.append({"id": key, "name": app["name"] if app else (w.get("title") or key),
                          "icon": app["icon"] if app else (w.get("app_id") or "application-x-executable"),
                          "pinned": False, "windows": [], "active": False,
                          "exec": app["exec"] if app else "", "terminal": app["terminal"] if app else False})
        item = items[index[key]]
        item["windows"].append(w["id"])
        item["active"] = item["active"] or bool(w.get("focused"))
    return items


# ---- system status ------------------------------------------------------

def _run(argv, timeout=2):
    if not shutil.which(argv[0]):
        return None
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def parse_wpctl_volume(text):
    """`Volume: 0.45 [MUTED]` -> (45, True)."""
    m = re.search(r"Volume:\s*([0-9.]+)(\s*\[MUTED\])?", text or "")
    if not m:
        return None
    return int(round(float(m.group(1)) * 100)), bool(m.group(2))


def volume():
    parsed = parse_wpctl_volume(_run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]))
    if not parsed:
        return {"available": False, "percent": 0, "muted": False}
    return {"available": True, "percent": parsed[0], "muted": parsed[1]}


def set_volume(percent):
    percent = max(0, min(150, int(percent)))
    _run(["wpctl", "set-volume", "-l", "1.5", "@DEFAULT_AUDIO_SINK@", "%d%%" % percent])
    return volume()


def toggle_mute():
    _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
    return volume()


def battery(root="/sys/class/power_supply"):
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return {"present": False}
    for name in names:
        base = os.path.join(root, name)
        try:
            with open(os.path.join(base, "type")) as f:
                if f.read().strip() != "Battery":
                    continue
            with open(os.path.join(base, "capacity")) as f:
                capacity = int(f.read().strip())
            status = ""
            if os.path.exists(os.path.join(base, "status")):
                with open(os.path.join(base, "status")) as f:
                    status = f.read().strip()
        except (OSError, ValueError):
            continue
        return {"present": True, "percent": max(0, min(100, capacity)),
                "charging": status in ("Charging", "Full")}
    return {"present": False}


def parse_nmcli(text):
    """`nmcli -t -f TYPE,STATE,CONNECTION device` -> what the bar shows."""
    best = {"kind": "none", "name": ""}
    for line in (text or "").splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 3 or parts[1] != "connected":
            continue
        kind = {"wifi": "wifi", "ethernet": "wired"}.get(parts[0])
        if kind and (best["kind"] == "none" or kind == "wired"):
            best = {"kind": kind, "name": parts[2].replace("\\:", ":")}
    return best


def network():
    return parse_nmcli(_run(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"]))


def status():
    return {"volume": volume(), "battery": battery(), "network": network()}


# ---- look ---------------------------------------------------------------

# The second glow colour of each theme; oziwm/src/theme.rs has the same table.
ACCENT2 = {
    "cyan": (124, 92, 255), "aurora": (255, 92, 200), "ember": (232, 64, 140),
    "mint": (60, 140, 255), "rose": (160, 92, 255), "frost": (110, 80, 230),
}

LOOK_DEFAULTS = {"theme": "cyan", "glow": 1.0, "animation_speed": 1.0, "corner_radius": 12,
                 "lock_after_minutes": 10, "wallpaper": "tesseract"}


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def palette(theme_id):
    """Colours for the shell, as #RRGGBB strings."""
    from . import themes
    theme = next((t for t in themes.THEMES if t.id == theme_id), themes.THEMES[0])
    return {
        "id": theme.id, "light": theme.light,
        "ink": _hex(theme.ink), "raised": _hex(theme.raised), "control": _hex(theme.control),
        "text": _hex(theme.text), "muted": _hex(theme.muted),
        "accent": _hex(theme.accent), "accent2": _hex(ACCENT2.get(theme.id, theme.accent_alt)),
    }


def look(environ=os.environ):
    """The look settings with defaults filled in and values kept in range."""
    data = dict(LOOK_DEFAULTS)
    cfg = read_config(environ)
    for key in LOOK_DEFAULTS:
        if key in cfg:
            data[key] = cfg[key]
    try:
        data["glow"] = max(0.0, min(2.0, float(data["glow"])))
        data["animation_speed"] = max(0.0, min(3.0, float(data["animation_speed"])))
        data["corner_radius"] = max(0, min(24, int(data["corner_radius"])))
        data["lock_after_minutes"] = max(0, min(1440, int(data["lock_after_minutes"])))
        if not isinstance(data["wallpaper"], str) or not data["wallpaper"]:
            data["wallpaper"] = "tesseract"
    except (TypeError, ValueError):
        data = dict(LOOK_DEFAULTS)
    return data


def theme_ids():
    from . import themes
    return [t.id for t in themes.THEMES]


# ---- radios, brightness, power ------------------------------------------

def _split_terse(line):
    """nmcli -t fields: split on ':' that is not escaped, unescape the rest."""
    return [p.replace("\\:", ":").replace("\\\\", "\\") for p in re.split(r"(?<!\\):", line)]


def parse_nmcli_radio(text):
    """`nmcli -t radio` -> {"wifi_hw": bool, "wifi": bool}."""
    parts = (text or "").strip().split(":")
    if len(parts) < 2:
        return {"wifi_hw": False, "wifi": False}
    return {"wifi_hw": parts[0] == "enabled", "wifi": parts[1] == "enabled"}


def parse_wifi_list(text):
    """`nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list` -> networks,
    one per name, the strongest signal kept, the one in use first."""
    best = {}
    for line in (text or "").splitlines():
        parts = _split_terse(line)
        if len(parts) < 4 or not parts[1]:
            continue
        in_use, ssid, signal, security = parts[0] == "*", parts[1], parts[2], parts[3]
        try:
            signal = int(signal)
        except ValueError:
            signal = 0
        secure = bool(security.strip()) and security.strip() != "--"
        old = best.get(ssid)
        if old is None or signal > old["signal"] or in_use:
            best[ssid] = {"ssid": ssid, "signal": max(signal, old["signal"] if old else 0),
                          "secure": secure, "active": in_use or bool(old and old["active"])}
    return sorted(best.values(), key=lambda n: (not n["active"], -n["signal"], n["ssid"].casefold()))


def parse_bt_powered(text):
    return bool(re.search(r"^\s*Powered:\s*yes", text or "", re.M))


def parse_bt_devices(text):
    """`bluetoothctl devices Paired` -> [(mac, name)]."""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"Device\s+([0-9A-F:]{17})\s+(.*)", line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def brightness_percent(current, maximum):
    if maximum <= 0:
        return 0
    return max(0, min(100, round(current * 100 / maximum)))


def brightness_value(percent, maximum):
    """Never fully dark: 1% is the floor, so the screen cannot be lost."""
    percent = max(1, min(100, int(percent)))
    return max(1, round(maximum * percent / 100))


def wifi():
    radio = parse_nmcli_radio(_run(["nmcli", "-t", "radio"]))
    return dict(radio, available=_run(["nmcli", "-v"]) is not None)


def wifi_networks():
    _run(["nmcli", "dev", "wifi", "rescan"], timeout=4)
    return parse_wifi_list(_run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], timeout=6))


def set_wifi(on):
    _run(["nmcli", "radio", "wifi", "on" if on else "off"])
    return wifi()


def connect_wifi(ssid, password=""):
    """Use a saved connection if there is one, else connect (with a password if given)."""
    saved = (_run(["nmcli", "-t", "-f", "NAME", "connection", "show"]) or "").splitlines()
    if ssid in saved and not password:
        argv = ["nmcli", "connection", "up", "id", ssid]
    else:
        argv = ["nmcli", "dev", "wifi", "connect", ssid] + (["password", password] if password else [])
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.SubprocessError) as err:
        return {"ok": False, "message": str(err)}
    message = (done.stdout + done.stderr).strip()
    needs = done.returncode != 0 and bool(re.search(r"secrets were required|password|802-11-wireless-security", message, re.I))
    return {"ok": done.returncode == 0, "needs_password": needs, "message": message.splitlines()[-1] if message else ""}


def bluetooth():
    show = _run(["bluetoothctl", "show"], timeout=3)
    if show is None or "No default controller" in show or not show.strip():
        return {"available": False, "powered": False, "devices": []}
    powered = parse_bt_powered(show)
    devices = []
    for mac, name in parse_bt_devices(_run(["bluetoothctl", "devices", "Paired"], timeout=3))[:8]:
        info = _run(["bluetoothctl", "info", mac], timeout=3) or ""
        devices.append({"mac": mac, "name": name, "connected": bool(re.search(r"Connected:\s*yes", info))})
    return {"available": True, "powered": powered, "devices": devices}


def set_bluetooth(on):
    _run(["bluetoothctl", "power", "on" if on else "off"], timeout=5)
    return bluetooth()


def bluetooth_device(mac, connect):
    if not re.fullmatch(r"[0-9A-F:]{17}", mac or ""):
        return bluetooth()
    _run(["bluetoothctl", "connect" if connect else "disconnect", mac], timeout=15)
    return bluetooth()


def airplane(state_wifi=None, state_bt=None):
    w = state_wifi if state_wifi is not None else wifi()
    b = state_bt if state_bt is not None else bluetooth()
    return not w.get("wifi") and not (b.get("available") and b.get("powered"))


def set_airplane(on):
    _run(["nmcli", "radio", "all", "off" if on else "on"])
    _run(["bluetoothctl", "power", "off" if on else "on"], timeout=5)
    return {"wifi": wifi(), "bluetooth": bluetooth()}


def _backlight(root="/sys/class/backlight"):
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    # Prefer the panel's own controller over firmware/vendor ones.
    names.sort(key=lambda n: (not n.startswith(("intel", "amdgpu", "nvidia")), n))
    for name in names:
        try:
            with open(os.path.join(root, name, "brightness")) as f:
                cur = int(f.read())
            with open(os.path.join(root, name, "max_brightness")) as f:
                top = int(f.read())
        except (OSError, ValueError):
            continue
        return name, cur, top
    return None


def brightness(root="/sys/class/backlight"):
    found = _backlight(root)
    if not found:
        return {"available": False, "percent": 100}
    _, cur, top = found
    return {"available": True, "percent": brightness_percent(cur, top)}


def set_brightness(percent):
    """Through logind, which lets the person at the seat change it without root."""
    found = _backlight()
    if not found:
        return brightness()
    name, _, top = found
    _run(["busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1/session/auto",
          "org.freedesktop.login1.Session", "SetBrightness", "ssu", "backlight", name,
          str(brightness_value(percent, top))])
    return brightness()


POWER_PROFILES = ("power-saver", "balanced", "performance")


def power_profile():
    out = (_run(["powerprofilesctl", "get"]) or "").strip()
    return out if out in POWER_PROFILES else ""


def set_power_profile(name):
    if name in POWER_PROFILES:
        _run(["powerprofilesctl", "set", name])
    return power_profile()


def media(action):
    """Play/pause, next, previous on the first media player found (MPRIS)."""
    method = {"play-pause": "PlayPause", "next": "Next", "previous": "Previous"}.get(action)
    if not method:
        return False
    names = _run(["busctl", "--user", "list", "--no-legend"]) or ""
    players = [l.split()[0] for l in names.splitlines() if l.startswith("org.mpris.MediaPlayer2.")]
    if not players:
        return False
    _run(["busctl", "--user", "call", players[0], "/org/mpris/MediaPlayer2",
          "org.mpris.MediaPlayer2.Player", method])
    return True


def full_status():
    """Everything the bar and the quick panel show."""
    w, b = wifi(), bluetooth()
    return dict(status(), wifi=w, bluetooth=b, airplane=airplane(w, b),
                brightness=brightness(), power=power_profile())


# ---- wallpapers ---------------------------------------------------------

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def wallpaper_dirs(environ=os.environ):
    home = environ.get("HOME", "/root")
    pictures = os.path.join(home, "Resimler")
    try:
        with open(os.path.join(environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"), "user-dirs.dirs")) as f:
            m = re.search(r'^XDG_PICTURES_DIR="(.*)"', f.read(), re.M)
            if m:
                pictures = m.group(1).replace("$HOME", home)
    except OSError:
        pass
    return [
        ("OziOS", "/usr/share/ozios/wallpapers"),
        ("OziOS", os.path.join(os.path.dirname(__file__), "..", "..", "branding", "wallpapers")),
        ("Sistem", "/usr/share/wallpapers"),
        ("Resimlerim", os.path.join(pictures, "Duvar kağıtları")),
        ("Resimlerim", pictures),
    ]


def wallpapers(environ=os.environ, limit=200):
    """Every picture that can be a wallpaper: OziOS's own first, then the
    system's (KDE and CachyOS packages), then the user's Pictures."""
    found, seen = [], set()
    for group, root in wallpaper_dirs(environ):
        if not os.path.isdir(root):
            continue
        depth0 = root.rstrip("/").count("/")
        for dirpath, dirnames, files in os.walk(root):
            # KDE packages keep sizes under contents/images: take the biggest only.
            if dirpath.count("/") - depth0 > 4:
                dirnames[:] = []
                continue
            dirnames.sort()
            pictures = sorted(f for f in files if f.lower().endswith(IMAGE_EXT))
            if "contents/images" in dirpath.replace("\\", "/") and pictures:
                pictures = [max(pictures, key=lambda f: os.path.getsize(os.path.join(dirpath, f)))]
            for name in pictures:
                path = os.path.realpath(os.path.join(dirpath, name))
                low = (dirpath + "/" + name).casefold()
                if path in seen or "screenshot" in low or "ekran görüntü" in low:
                    continue
                seen.add(path)
                title = os.path.splitext(name)[0]
                if "contents/images" in dirpath:
                    title = os.path.basename(dirpath.split("/contents/")[0])
                    if dirpath.rstrip("/").endswith("images_dark"):
                        title += " (koyu)"
                found.append({"path": path, "title": title.replace("-", " ").replace("_", " "), "group": group})
                if len(found) >= limit:
                    return found
    return found
