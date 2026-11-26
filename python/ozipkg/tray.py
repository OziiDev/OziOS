"""The system tray: programs that keep running in the background (Discord,
Steam, Telegram, a VPN...) put a small icon in the bar through the
StatusNotifierItem D-Bus protocol, with a menu (com.canonical.dbusmenu).

ozi-shell owns org.kde.StatusNotifierWatcher (programs register with it) and
draws the icons. Reading an item and its menu goes through `busctl --json`,
which turns D-Bus's nested types into plain JSON; this module turns that JSON
into what the bar needs, and is tested without a bus.
"""
import json
import os
import subprocess
import tempfile

ITEM_IFACE = "org.kde.StatusNotifierItem"
MENU_IFACE = "com.canonical.dbusmenu"
DEFAULT_PATH = "/StatusNotifierItem"


def split_service(service, sender=""):
    """(bus name, object path) from what a program registered: a bus name, a
    path (then the sender is the bus name) or "name/path"."""
    if service.startswith("/"):
        return sender, service
    if "/" in service:
        name, _, path = service.partition("/")
        return name, "/" + path
    return service, DEFAULT_PATH


def _value(v):
    """busctl's {"type": t, "data": d} -> d, all the way down."""
    if isinstance(v, dict) and set(v) == {"type", "data"}:
        return _value(v["data"])
    if isinstance(v, list):
        return [_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _value(x) for k, x in v.items()}
    return v


def busctl(*args, timeout=3):
    """Run `busctl --user --json=short ARGS`; the parsed reply or None."""
    try:
        # "--" after the verb: a "-1" among the arguments is not an option.
        out = subprocess.run(["busctl", "--user", "--json=short", args[0], "--", *args[1:]],
                             capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def parse_props(reply):
    """GetAll's reply -> the item's properties as plain values."""
    if not reply:
        return {}
    data = _value(reply.get("data"))
    if isinstance(data, list) and data:
        data = data[0]
    return data if isinstance(data, dict) else {}


def best_pixmap(pixmaps, want=48):
    """The (width, height, ARGB bytes) closest to `want` px from IconPixmap."""
    good = [p for p in pixmaps or [] if len(p) == 3 and p[0] > 0 and p[1] > 0 and len(p[2]) >= p[0] * p[1] * 4]
    if not good:
        return None
    bigger = [p for p in good if p[0] >= want]
    w, h, data = min(bigger, key=lambda p: p[0]) if bigger else max(good, key=lambda p: p[0])
    return w, h, bytes(data)


def pixmap_png(w, h, argb, folder=None):
    """Write an IconPixmap (ARGB32, big-endian) as a PNG; its path."""
    from PyQt6.QtGui import QImage
    # The protocol's pixels are A, R, G, B bytes; Qt's RGBA8888 wants R, G, B, A.
    rgba = bytearray(len(argb))
    rgba[0::4] = argb[1::4]
    rgba[1::4] = argb[2::4]
    rgba[2::4] = argb[3::4]
    rgba[3::4] = argb[0::4]
    image = QImage(bytes(rgba), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
    folder = folder or os.path.join(tempfile.gettempdir(), "ozi-tray-%d" % os.getuid())
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "%x.png" % (hash(bytes(argb)) & 0xFFFFFFFFFFFF))
    if not os.path.exists(path):
        image.save(path, "PNG")
    return path


def item_view(service, props, icon_file=""):
    """What the bar shows for one item."""
    tip = props.get("ToolTip")
    tip_text = ""
    if isinstance(tip, list) and len(tip) >= 3:
        tip_text = tip[2] or (tip[3] if len(tip) > 3 else "")
    title = props.get("Title") or tip_text or props.get("Id") or ""
    icon = props.get("IconName") or ""
    theme_path = props.get("IconThemePath") or ""
    if icon and theme_path and not icon.startswith("/"):
        for ext in (".png", ".svg"):
            for sub in ("", "hicolor/48x48/apps", "hicolor/scalable/apps"):
                candidate = os.path.join(theme_path, sub, icon + ext)
                if os.path.isfile(candidate):
                    icon = candidate
                    break
    if icon_file:
        icon = icon_file
    return {
        "service": service,
        "id": props.get("Id") or service,
        "title": title,
        "icon": icon or "application-x-executable",
        "status": props.get("Status") or "Active",
        "menu": props.get("Menu") or "",
        "itemIsMenu": bool(props.get("ItemIsMenu")),
    }


def _menu_entries(children, depth=0):
    out = []
    for child in children or []:
        child = _value(child)
        if not isinstance(child, list) or len(child) < 3:
            continue
        cid, props, kids = child[0], child[1] or {}, child[2]
        if props.get("visible") is False:
            continue
        kind = props.get("type", "standard")
        label = (props.get("label") or "").replace("__", "\0").replace("_", "").replace("\0", "_")
        entry = {"id": cid, "label": label, "separator": kind == "separator",
                 "enabled": props.get("enabled", True) is not False,
                 "toggle": props.get("toggle-type", ""), "checked": props.get("toggle-state", 0) == 1,
                 "depth": depth, "submenu": props.get("children-display") == "submenu" or bool(kids)}
        out.append(entry)
        if kids:
            out.extend(_menu_entries(kids, depth + 1))
    return out


def parse_menu(reply):
    """GetLayout's reply -> a flat list of entries (submenus follow their parent, indented)."""
    if not reply:
        return []
    data = _value(reply.get("data"))
    # (revision, (id, props, children))
    if not isinstance(data, list) or len(data) < 2:
        return []
    root = data[1]
    if not isinstance(root, list) or len(root) < 3:
        return []
    entries = _menu_entries(root[2])
    # No separators at the ends or twice in a row.
    clean = []
    for e in entries:
        if e["separator"] and (not clean or clean[-1]["separator"]):
            continue
        clean.append(e)
    while clean and clean[-1]["separator"]:
        clean.pop()
    return clean


# ---- talking to a program ------------------------------------------------

def read_item(service):
    name, path = split_service(service)
    view = parse_props(busctl("call", name, path, "org.freedesktop.DBus.Properties", "GetAll", "s", ITEM_IFACE))
    if not view:
        return None
    icon_file = ""
    if not view.get("IconName") or (view.get("Status") == "NeedsAttention" and view.get("AttentionIconPixmap")):
        pix = best_pixmap(view.get("AttentionIconPixmap") if view.get("Status") == "NeedsAttention" else None) \
            or best_pixmap(view.get("IconPixmap"))
        if pix:
            try:
                icon_file = pixmap_png(*pix)
            except Exception:
                icon_file = ""
    return item_view(service, view, icon_file)


def activate(service, x=0, y=0, secondary=False):
    name, path = split_service(service)
    method = "SecondaryActivate" if secondary else "Activate"
    return busctl("call", name, path, ITEM_IFACE, method, "ii", str(int(x)), str(int(y))) is not None


def menu(service, menu_path):
    name, _ = split_service(service)
    busctl("call", name, menu_path, MENU_IFACE, "AboutToShow", "i", "0")
    return parse_menu(busctl("call", name, menu_path, MENU_IFACE, "GetLayout", "iias", "0", "-1", "0"))


def menu_click(service, menu_path, entry_id):
    name, _ = split_service(service)
    return busctl("call", name, menu_path, MENU_IFACE, "Event", "isvu",
                  str(int(entry_id)), "clicked", "s", "", "0") is not None
