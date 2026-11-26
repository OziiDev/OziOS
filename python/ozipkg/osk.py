"""The on-screen keyboard's keys, read from the keyboard layout in use.

The shell draws the keys; oziwm presses them (IPC "press" with evdev codes),
so whatever the layout makes of a key is what gets typed: Turkish Q, Turkish F,
German, French or US alike. The labels come from the same layout through
xkbcli, so they match.

    board()  -> {"layout": "tr", "rows": [[key...]...], "symbols": [key...]}

A key is {"label": "ş", "shift": "Ş", "code": 39} on the letter rows, and
{"label": "@", "keys": [100, 16]} on the symbol page (the keys pressed together).
"""
import json
import os
import re
import subprocess

SHIFT = 42
# What the symbol page offers: punctuation and the everyday signs, not every
# arrow and quotation mark a layout has on its third level.
ORDER = "@#₺€$£%&*-+=()/?!'\":;,._\\|<>[]{}^~`°§×÷"
EVERYDAY = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~") | set("€₺£°§×÷")
ALTGR = 100     # right Alt: the third level on most layouts

# Physical keys, row by row, as xkb names them, with their evdev codes.
ROWS = [
    [("AE%02d" % i, 1 + i) for i in range(1, 13)],
    [("AD%02d" % i, 15 + i) for i in range(1, 13)],
    [("AC%02d" % i, 29 + i) for i in range(1, 12)] + [("BKSL", 43)],
    [("LSGT", 86)] + [("AB%02d" % i, 43 + i) for i in range(1, 11)],
]
EXTRA = [("TLDE", 41)]

_HERE = os.path.dirname(os.path.abspath(__file__))
KEYSYMS_PATHS = [
    os.path.join(_HERE, "..", "..", "data", "osk", "keysyms.json"),
    "/usr/share/ozios/data/osk/keysyms.json",
]


def keysyms():
    for path in KEYSYMS_PATHS:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return {}


def char_of(sym, table):
    """The character a keysym types, or "" for dead keys, modifiers and the like."""
    if not sym or sym == "VoidSymbol" or sym.startswith("dead_"):
        return ""
    if len(sym) == 1:
        return sym
    m = re.fullmatch(r"U([0-9A-Fa-f]{4,6})", sym)
    if m:
        return chr(int(m.group(1), 16))
    return table.get(sym, "")


def _parse_kxkbrc(text):
    layouts, variants, use = "", "", True
    group = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            group = line
            continue
        if group == "[Layout]" and "=" in line:
            key, value = (p.strip() for p in line.split("=", 1))
            if key == "LayoutList":
                layouts = value
            elif key == "VariantList":
                variants = value
            elif key == "Use":
                use = value.lower() != "false"
    if not use or not layouts:
        return None
    return layouts.split(",")[0], (variants.split(",")[0] if variants else "")


def _parse_xorg(text):
    layout = re.search(r'Option\s+"XkbLayout"\s+"([^"]+)"', text)
    if not layout:
        return None
    variant = re.search(r'Option\s+"XkbVariant"\s+"([^"]*)"', text)
    return layout.group(1).split(",")[0], (variant.group(1).split(",")[0] if variant else "")


def _parse_vconsole(text):
    m = re.search(r"^KEYMAP=\"?([\w-]+)", text, re.M)
    if not m:
        return None
    keymap = m.group(1)
    known = {"trq": ("tr", ""), "trf": ("tr", "f"), "us": ("us", ""), "de": ("de", ""),
             "de-latin1": ("de", ""), "fr": ("fr", ""), "uk": ("gb", ""), "es": ("es", ""), "it": ("it", "")}
    return known.get(keymap, (keymap.split("-")[0], ""))


def layout(environ=os.environ):
    """(layout, variant) the way oziwm picks it: env, Plasma's kxkbrc, X11, the console."""
    if environ.get("OZIWM_XKB_LAYOUT"):
        return environ["OZIWM_XKB_LAYOUT"].split(",")[0], environ.get("OZIWM_XKB_VARIANT", "").split(",")[0]
    home = environ.get("HOME", "")
    sources = [
        (os.path.join(home, ".config", "kxkbrc"), _parse_kxkbrc),
        ("/etc/X11/xorg.conf.d/00-keyboard.conf", _parse_xorg),
        ("/etc/vconsole.conf", _parse_vconsole),
    ]
    for path, parse in sources:
        try:
            with open(path, encoding="utf-8") as f:
                found = parse(f.read())
        except OSError:
            continue
        if found:
            return found
    return "us", ""


def parse_keymap(text):
    """xkb key name -> its symbols by level, from `xkbcli compile-keymap`."""
    keys = {}
    for m in re.finditer(r"key <(\w+)>\s*\{(.*?)\};", text, re.S):
        body = m.group(2)
        # `{ [ a, A ] }`, or with a type: `symbols[1]= [ a, A ]`.
        levels = re.search(r"symbols\[\d+\]\s*=\s*\[([^\]]*)\]", body) or re.match(r"\s*\[([^\]]*)\]", body)
        if levels:
            keys[m.group(1)] = [s.strip() for s in levels.group(1).split(",")]
    return keys


def compile_keymap(name, variant=""):
    args = ["xkbcli", "compile-keymap", "--layout", name]
    if variant:
        args += ["--variant", variant]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def build(keys, table):
    """The letter rows and the symbol page from a parsed keymap."""
    rows, typed = [], set()
    for row in ROWS:
        out = []
        for name, code in row:
            levels = keys.get(name, [])
            first = char_of(levels[0] if levels else "", table)
            if not first:
                continue
            second = char_of(levels[1] if len(levels) > 1 else "", table) or first
            out.append({"label": first, "shift": second, "code": code})
            typed.add(first)
        rows.append(out)
    # The symbol page: what Shift or AltGr gives on any key, and the keys left out
    # above, that the letter rows do not type already.
    symbols, seen = [], set(typed)
    for name, code in [k for row in ROWS for k in row] + EXTRA:
        levels = keys.get(name, [])
        for level, mods in ((0, []), (1, [SHIFT]), (2, [ALTGR])):
            if len(levels) <= level:
                continue
            ch = char_of(levels[level], table)
            if not ch or ch in seen or ch.isalnum() and level != 0:
                continue
            if ch.isalpha() or ch not in EVERYDAY:
                continue
            seen.add(ch)
            symbols.append({"label": ch, "keys": mods + [code]})
    symbols.sort(key=lambda k: ORDER.find(k["label"]) if k["label"] in ORDER else len(ORDER))
    return rows, symbols


def cache_path(environ=os.environ):
    base = environ.get("XDG_CACHE_HOME") or os.path.join(environ.get("HOME", "/tmp"), ".cache")
    return os.path.join(base, "ozios", "osk.json")


def board(environ=os.environ):
    name, variant = layout(environ)
    path = cache_path(environ)
    try:
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("layout") == name and cached.get("variant") == variant and cached.get("rows"):
            return cached
    except (OSError, ValueError):
        pass
    rows, symbols = build(parse_keymap(compile_keymap(name, variant)), keysyms())
    if not any(rows):
        rows, symbols = build(parse_keymap(compile_keymap("us")), keysyms())
    result = {"layout": name, "variant": variant, "rows": rows, "symbols": symbols}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
    except OSError:
        pass
    return result


def touch_screen(udev="/run/udev/data"):
    """Whether a touch screen (a board, a touch laptop) is plugged in."""
    try:
        names = os.listdir(udev)
    except OSError:
        return False
    for name in names:
        if not name.startswith("c13:"):
            continue
        try:
            with open(os.path.join(udev, name), encoding="utf-8", errors="replace") as f:
                if "E:ID_INPUT_TOUCHSCREEN=1" in f.read():
                    return True
        except OSError:
            continue
    return False
