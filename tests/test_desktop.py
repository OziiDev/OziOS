"""The OziOS shell: themes, the Plasma style, the dock and launcher packages, the window motion.

Plasma itself is not available here, so these check what can be checked
without it: generated files match their generators, every package is well
formed, the frames are cut into the right pieces, the KWin effect runs against
a stand-in for KWin's script API, and the QML is at least balanced and imports
only what Plasma provides.
"""
import configparser
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import themes, tools  # noqa: E402

NODE = shutil.which("node")
DESKTOP = os.path.join(ROOT, "desktop")
SVG = "{http://www.w3.org/2000/svg}"


def load_tool(name):
    path = os.path.join(ROOT, "tools", name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def luminance(rgb):
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def rgb(value):
    return tuple(int(x) for x in value.split(","))


def rgb_hex(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


# --- colour themes ------------------------------------------------------------------

class Themes(unittest.TestCase):
    def scheme(self, theme):
        name = "branding/" + theme.file_name if theme.id == themes.DEFAULT else "branding/themes/" + theme.file_name
        return name, read(*name.split("/"))

    def test_the_files_are_what_the_generator_writes(self):
        for theme in themes.THEMES:
            name, text = self.scheme(theme)
            self.assertEqual(text, themes.render(theme), "%s is stale: run tools/make-themes.py" % name)

    def test_the_original_cyan_scheme_is_kept(self):
        _, text = self.scheme(themes.BY_ID["cyan"])
        self.assertIn("[Colors:Selection]\nBackgroundNormal=0,229,255\n", text)
        self.assertIn("ColorScheme=OziOS\nName=OziOS\n", text)

    def test_every_scheme_parses_and_names_itself(self):
        for theme in themes.THEMES:
            parser = configparser.ConfigParser(interpolation=None, strict=True)
            parser.optionxform = str
            parser.read_string(self.scheme(theme)[1])
            self.assertEqual(parser["General"]["ColorScheme"], theme.scheme)
            for group in ("Window", "View", "Button", "Selection", "Tooltip", "Complementary", "Header"):
                self.assertIn("Colors:" + group, parser)

    def test_text_is_readable_everywhere(self):
        for theme in themes.THEMES:
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read_string(self.scheme(theme)[1])
            for group in ("Window", "View", "Button", "Tooltip", "Header"):
                section = parser["Colors:" + group]
                ratio = contrast(rgb(section["ForegroundNormal"]), rgb(section["BackgroundNormal"]))
                self.assertGreaterEqual(ratio, 7, "%s %s: %.1f" % (theme.id, group, ratio))
            selection = parser["Colors:Selection"]
            ratio = contrast(rgb(selection["ForegroundNormal"]), rgb(selection["BackgroundNormal"]))
            self.assertGreaterEqual(ratio, 3.5, "%s selection: %.1f" % (theme.id, ratio))
            # the accent stands out from the background it is drawn on (dock lights, borders)
            window = parser["Colors:Window"]
            ratio = contrast(rgb(window["DecorationFocus"]), rgb(window["BackgroundNormal"]))
            self.assertGreaterEqual(ratio, 3, "%s accent: %.1f" % (theme.id, ratio))

    def test_ids_and_scheme_names_are_unique(self):
        self.assertEqual(len({t.id for t in themes.THEMES}), len(themes.THEMES))
        self.assertEqual(len({t.scheme for t in themes.THEMES}), len(themes.THEMES))

    def test_the_theme_in_use_is_read_from_kdeglobals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "kdeglobals")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("[KDE]\nColorScheme=Nope\n\n[General]\nColorScheme=OziOSEmber\nfont=x\n")
            self.assertEqual(themes.current(path), "ember")
            items = themes.listing(path)
            self.assertEqual([i["id"] for i in items if i["current"]], ["ember"])
            self.assertEqual(themes.current(os.path.join(folder, "missing")), "")

    def test_switching_runs_plasma_apply_colorscheme_and_recolours_the_terminal(self):
        calls = []

        class Done:
            returncode = 0

        def run(argv, **kwargs):
            calls.append(argv)
            return Done()
        out = []
        with tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, "konsole"))
            with open(os.path.join(home, "konsole", "OziOS.profile"), "w", encoding="utf-8") as fh:
                fh.write(read("branding", "konsole", "OziOS.profile"))
            self.assertEqual(themes.main(["mint"], out=out.append, run=run, home=home, config=home), 0)
            with open(os.path.join(home, "konsole", "OziOS.profile"), encoding="utf-8") as fh:
                profile = fh.read()
        self.assertEqual(calls, [["plasma-apply-colorscheme", "OziOSMint"]])
        self.assertIn("Mint", out[0])
        self.assertIn("ColorScheme=OziOSMint", profile)
        self.assertIn("TerminalColumns=110", profile)                  # the rest of the profile stays

    def test_the_terminal_profile_comes_from_the_system_copy_the_first_time(self):
        with tempfile.TemporaryDirectory() as folder:
            system, home = os.path.join(folder, "system"), os.path.join(folder, "home")
            os.makedirs(system)
            with open(os.path.join(system, "OziOS.profile"), "w", encoding="utf-8") as fh:
                fh.write("[General]\nName=OziOS\n")
            self.assertTrue(themes.set_konsole(themes.BY_ID["frost"], home=home, system_dirs=(system,)))
            with open(os.path.join(home, "konsole", "OziOS.profile"), encoding="utf-8") as fh:
                self.assertIn("[Appearance]\nColorScheme=OziOSFrost", fh.read())
            self.assertFalse(themes.set_konsole(themes.BY_ID["frost"], home=os.path.join(folder, "nobody"), system_dirs=()))

    def test_every_theme_has_a_terminal_scheme_and_cyan_keeps_the_original(self):
        for theme in themes.THEMES:
            text = read("branding", "konsole", theme.scheme + ".colorscheme")
            self.assertEqual(text, themes.render_konsole(theme), "%s is stale: run tools/make-themes.py" % theme.scheme)
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read_string(text)
            background, foreground = rgb(parser["Background"]["Color"]), rgb(parser["Foreground"]["Color"])
            self.assertGreaterEqual(contrast(foreground, background), 7, theme.id)
            for number in range(1, 7):                                  # the coloured ANSI text stays readable
                self.assertGreaterEqual(contrast(rgb(parser["Color%d" % number]["Color"]), background), 3, (theme.id, number))

    def test_apps_get_the_themes_palette(self):
        cyan = themes.app_palette("cyan")
        theme_qml = read("apps", "OziUi", "Theme.qml")
        defaults = {k: v.lower() for k, v in re.findall(r'property color (\w+): "(#[0-9A-Fa-f]{6})"', theme_qml)}
        for key in ("ink", "raised", "control", "cyan", "mid", "far", "ice", "muted", "onAccent"):
            self.assertEqual(cyan[key], defaults[key], key)                 # the cyan theme is what the QML says
        frost = themes.app_palette("frost")
        self.assertTrue(frost["light"])
        self.assertGreaterEqual(contrast(rgb_hex(frost["ice"]), rgb_hex(frost["ink"])), 7)
        self.assertEqual(themes.theme_for_apps({"OZIOS_THEME": "rose"}, kdeglobals=os.devnull), "rose")
        self.assertEqual(themes.theme_for_apps({"OZIOS_THEME": "nope"}, kdeglobals=os.devnull), "cyan")

    def test_day_and_night_follow_the_clock(self):
        import datetime
        settings = dict(themes.AUTO_DEFAULTS, day="frost", night="aurora")
        for clock, expected in (("06:59", "aurora"), ("07:00", "frost"), ("18:59", "frost"), ("19:00", "aurora"), ("00:30", "aurora")):
            hours, minutes = (int(x) for x in clock.split(":"))
            self.assertEqual(themes.auto_choice(datetime.time(hours, minutes), settings), expected, clock)

    def auto_run(self, calls, kdeglobals_scheme=""):
        class Done:
            returncode = 0

        def run(argv, **kwargs):
            calls.append(argv)
            return Done()
        return run

    def test_auto_saves_the_choice_starts_the_timer_and_switches_now(self):
        import datetime
        calls, out = [], []
        with tempfile.TemporaryDirectory() as folder:
            code = themes.main(["auto", "--night", "rose"], out=out.append, run=self.auto_run(calls), home=folder,
                               config=folder, kdeglobals=os.devnull, now=datetime.time(13, 0))
            with open(themes.auto_path(folder), encoding="utf-8") as fh:
                saved = json.load(fh)
        self.assertEqual(code, 0)
        self.assertEqual(saved["day"], "frost")
        self.assertEqual(saved["night"], "rose")
        self.assertIn(["systemctl", "--user", "enable", "--now", "ozios-theme-auto.timer"], calls)
        self.assertIn(["plasma-apply-colorscheme", "OziOSFrost"], calls)        # it is day: frost at once
        self.assertIn("Frost", out[-1])

    def test_the_timer_switches_only_when_the_clock_asks_for_another_theme(self):
        import datetime
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, "ozios"))
            with open(themes.auto_path(folder), "w", encoding="utf-8") as fh:
                json.dump({"day": "frost", "night": "mint"}, fh)
            kdeglobals = os.path.join(folder, "kdeglobals")
            with open(kdeglobals, "w", encoding="utf-8") as fh:
                fh.write("[General]\nColorScheme=OziOSMint\n")
            calls = []
            run = self.auto_run(calls)
            self.assertEqual(themes.auto_tick(run=run, home=folder, config=folder, kdeglobals=kdeglobals, now=datetime.time(23, 0)), "")
            self.assertEqual(calls, [])                                         # night, mint already: nothing to do
            self.assertEqual(themes.auto_tick(run=run, home=folder, config=folder, kdeglobals=kdeglobals, now=datetime.time(9, 0)), "frost")
            self.assertEqual(calls, [["plasma-apply-colorscheme", "OziOSFrost"]])
        self.assertEqual(themes.auto_tick(run=run, config=os.path.join(folder, "gone")), "")   # not on: nothing

    def test_picking_a_theme_by_hand_ends_auto(self):
        calls = []
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, "ozios"))
            with open(themes.auto_path(folder), "w", encoding="utf-8") as fh:
                json.dump({"day": "frost", "night": "cyan"}, fh)
            themes.main(["ember"], out=lambda *_: None, run=self.auto_run(calls), home=folder, config=folder)
            self.assertFalse(os.path.exists(themes.auto_path(folder)))
        self.assertIn(["systemctl", "--user", "disable", "--now", "ozios-theme-auto.timer"], calls)

    def test_auto_off(self):
        calls, out = [], []
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, "ozios"))
            with open(themes.auto_path(folder), "w", encoding="utf-8") as fh:
                json.dump({"day": "frost", "night": "cyan"}, fh)
            self.assertEqual(themes.main(["auto", "off"], out=out.append, run=self.auto_run(calls), config=folder), 0)
            self.assertFalse(os.path.exists(themes.auto_path(folder)))
        self.assertIn(["systemctl", "--user", "disable", "--now", "ozios-theme-auto.timer"], calls)

    def test_a_broken_settings_file_turns_nothing_on(self):
        with tempfile.TemporaryDirectory() as folder:
            os.makedirs(os.path.join(folder, "ozios"))
            for text in ("not json", '{"day": "purple", "night": "cyan"}', '{"sunrise": "x"}'):
                with open(themes.auto_path(folder), "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.assertIsNone(themes.read_auto(folder), text)

    def test_the_timer_runs_the_tick_and_is_installed(self):
        service = read("packages", "ozios-settings", "ozios-theme-auto.service")
        timer = read("packages", "ozios-settings", "ozios-theme-auto.timer")
        self.assertIn("ExecStart=/usr/bin/ozi theme --auto-tick", service)
        self.assertIn("ConditionPathExists=%h/.config/ozios/theme-auto.json", service)
        self.assertIn("OnCalendar=", timer)
        self.assertIn("WantedBy=timers.target", timer)
        self.assertIn("ozios-theme-auto.timer", read("packages", "ozios-settings", "PKGBUILD"))

    def test_outside_the_desktop_it_says_so(self):
        def run(argv, **kwargs):
            raise FileNotFoundError(argv[0])
        out = []
        self.assertEqual(themes.main(["rose"], out=out.append, run=run, config=os.devnull), 1)
        self.assertIn("plasma-apply-colorscheme", out[0])

    def test_an_unknown_theme_is_refused(self):
        with self.assertRaises(SystemExit):
            themes.main(["purple"], out=lambda *_: None)

    def test_json_listing_for_the_control_widget(self):
        out = []
        themes.main(["--json"], out=out.append, kdeglobals=os.devnull)
        items = json.loads(out[0])
        self.assertEqual([i["id"] for i in items], [t.id for t in themes.THEMES])
        for item in items:
            self.assertRegex(item["accent"], r"^#[0-9a-f]{6}$")

    def test_ozi_hands_the_command_to_python(self):
        self.assertIn("theme", tools.COMMANDS)
        self.assertRegex(read("packages", "ozi-cli", "ozi"), r"gaming \| theme\)")


# --- the Plasma style ---------------------------------------------------------------

PIECES = ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright")


def path_box(d):
    """Bounding box of a path made of M, L, H, V, A (quarter arcs) and Z."""
    xs, ys = [], []
    tokens = re.findall(r"[MLHVAZ]|-?\d+(?:\.\d+)?", d)
    i = 0
    x = y = 0.0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd in ("M", "L"):
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
        elif cmd == "H":
            x = float(tokens[i])
            i += 1
        elif cmd == "V":
            y = float(tokens[i])
            i += 1
        elif cmd == "A":
            x, y = float(tokens[i + 5]), float(tokens[i + 6])
            i += 7
        elif cmd == "Z":
            continue
        xs.append(x)
        ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


class PlasmaStyle(unittest.TestCase):
    style = os.path.join(DESKTOP, "plasma-style", "ozios")

    def test_the_files_are_what_the_generator_writes(self):
        maker = load_tool("make-plasma-style.py")
        for rel, text in maker.files().items():
            with open(os.path.join(self.style, *rel.split("/")), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), text, "%s is stale: run tools/make-plasma-style.py" % rel)

    def test_every_frame_has_its_pieces_masks_and_margins(self):
        frames = glob.glob(os.path.join(self.style, "**", "*.svg"), recursive=True)
        self.assertEqual(len(frames), 12)
        for path in frames:
            root = ET.parse(path).getroot()
            ids = {el.get("id") for el in root.iter() if el.get("id")}
            for piece in PIECES:
                self.assertIn(piece, ids, path)
                self.assertIn("mask-" + piece, ids, path)
            for side in ("top", "bottom", "left", "right"):
                self.assertIn("hint-%s-margin" % side, ids, path)

    def test_the_pieces_tile_into_one_rounded_sheet(self):
        """Each piece fills exactly its cell of the 3x3 grid, so Plasma can stretch them without seams."""
        root = ET.parse(os.path.join(self.style, "widgets", "panel-background.svg")).getroot()
        groups = {g.get("id"): g for g in root.iter(SVG + "g")}
        r, c = 12, 16
        cells = {"topleft": (0, 0, r, r), "top": (r, 0, r + c, r), "topright": (r + c, 0, 2 * r + c, r),
                 "left": (0, r, r, r + c), "center": (r, r, r + c, r + c), "right": (r + c, r, 2 * r + c, r + c),
                 "bottomleft": (0, r + c, r, 2 * r + c), "bottom": (r, r + c, r + c, 2 * r + c),
                 "bottomright": (r + c, r + c, 2 * r + c, 2 * r + c)}
        for piece, cell in cells.items():
            boxes = [path_box(p.get("d")) for p in groups[piece].iter(SVG + "path")]
            union = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
            self.assertEqual(union, cell, piece)

    def test_colours_come_from_the_scheme(self):
        for path in glob.glob(os.path.join(self.style, "**", "*.svg"), recursive=True):
            root = ET.parse(path).getroot()
            for el in root.iter(SVG + "path"):
                if el.get("id", "").startswith("mask-"):
                    continue
                self.assertTrue(el.get("class", "").startswith("ColorScheme-"), path)
                self.assertIn("fill:currentColor", el.get("style", ""), path)
            self.assertIsNotNone(root.find(SVG + "style"), path)

    def test_translucent_is_lighter_and_opaque_is_solid(self):
        def opacity(rel):
            text = read("desktop", "plasma-style", "ozios", *rel.split("/"))
            return float(re.search(r'id="center"><path class="ColorScheme-Background" style="fill:currentColor;fill-opacity:([\d.]+)"', text).group(1))
        self.assertLess(opacity("translucent/widgets/panel-background.svg"), opacity("widgets/panel-background.svg"))
        self.assertEqual(opacity("opaque/dialogs/background.svg"), 1.0)


# --- Plasma and KWin packages -------------------------------------------------------

PACKAGES = {
    "Plasma/Applet": glob.glob(os.path.join(DESKTOP, "plasmoids", "*")),
    "Plasma/Wallpaper": glob.glob(os.path.join(DESKTOP, "wallpaper", "*")),
    "Plasma/LookAndFeel": glob.glob(os.path.join(DESKTOP, "look-and-feel", "*")),
    "Plasma/Theme": glob.glob(os.path.join(DESKTOP, "plasma-style", "*")),
    "KWin/Effect": glob.glob(os.path.join(DESKTOP, "kwin", "effects", "*")),
}


class Packages(unittest.TestCase):
    def test_metadata_is_valid_and_matches_the_folder(self):
        seen = 0
        for structure, folders in PACKAGES.items():
            for folder in folders:
                with open(os.path.join(folder, "metadata.json"), encoding="utf-8") as fh:
                    meta = json.load(fh)
                name = os.path.basename(folder)
                if structure != "Plasma/LookAndFeel":
                    self.assertEqual(meta.get("KPackageStructure"), structure, name)
                self.assertEqual(meta["KPlugin"]["Id"], name)
                self.assertTrue(meta["KPlugin"].get("Name"), name)
                seen += 1
        self.assertGreaterEqual(seen, 7)

    def test_applets_have_their_entry_point_and_a_valid_config(self):
        for folder in PACKAGES["Plasma/Applet"]:
            self.assertTrue(os.path.isfile(os.path.join(folder, "contents", "ui", "main.qml")), folder)
            config = os.path.join(folder, "contents", "config", "main.xml")
            if os.path.exists(config):
                ET.parse(config)

    def test_the_launcher_answers_the_meta_key_and_the_dock_counts_as_a_task_manager(self):
        launcher = json.loads(read("desktop", "plasmoids", "org.ozios.launcher", "metadata.json"))
        self.assertIn("org.kde.plasma.launchermenu", launcher["X-Plasma-Provides"])
        dock = json.loads(read("desktop", "plasmoids", "org.ozios.dock", "metadata.json"))
        self.assertIn("org.kde.plasma.multitasking", dock["X-Plasma-Provides"])

    def test_the_motion_replaces_kwins_own_open_close_animation(self):
        meta = json.loads(read("desktop", "kwin", "effects", "ozios_motion", "metadata.json"))
        self.assertEqual(meta["X-KWin-Exclusive-Category"], "toplevel-open-close-animation")
        self.assertEqual(meta["X-Plasma-API"], "javascript")
        for text in (read("tools", "apply-branding.sh"), read("packages", "ozi-cli", "ozi")):
            self.assertIn("ozios_motion", text)
            self.assertRegex(text, r"scale\b.*false|kwin_effect \"\$name\" false")

    def test_the_package_installs_the_shell(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        for needle in ("org.ozios.dock org.ozios.launcher", "/usr/share/plasma/desktoptheme/ozios/",
                       "/usr/share/kwin/effects/ozios_motion/contents/code/main.js", "branding/themes/*.colors"):
            self.assertIn(needle, text)

    def test_layouts_use_widgets_that_exist(self):
        ours = {os.path.basename(f) for f in PACKAGES["Plasma/Applet"]}
        scripts = glob.glob(os.path.join(DESKTOP, "layouts", "*.js")) + glob.glob(os.path.join(ROOT, "edu", "layouts", "*.js")) \
            + glob.glob(os.path.join(DESKTOP, "look-and-feel", "*", "contents", "layouts", "*.js"))
        for path in scripts:
            with open(path, encoding="utf-8") as fh:
                for widget in re.findall(r'addWidget\("([^"]+)"\)', fh.read()):
                    self.assertTrue(widget.startswith("org.kde.plasma.") or widget in ours, "%s: %s" % (path, widget))

    def test_the_default_desktop_is_the_ozios_shell(self):
        for rel in (("desktop", "layouts", "default.js"),
                    ("desktop", "look-and-feel", "org.ozios.desktop", "contents", "layouts", "org.kde.plasma.desktop-layout.js")):
            text = read(*rel)
            self.assertIn('addWidget("org.ozios.launcher")', text)
            self.assertIn('addWidget("org.ozios.dock")', text)
            self.assertNotIn("kickoff", text)
        self.assertIn("[plasmarc][Theme]\nname=ozios", read("desktop", "look-and-feel", "org.ozios.desktop", "contents", "defaults"))


# --- QML --------------------------------------------------------------------------------

ALLOWED_IMPORTS = re.compile(r"^(QtQuick(\.\w+)*|org\.kde\.[\w.]+|\"[\w./-]+\")$")


def strip_code(text):
    """QML without strings and comments, for counting brackets."""
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if text.startswith("//", i):
            i = text.find("\n", i)
            i = n if i < 0 else i
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif ch in "\"'`":
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            out.append(ch + ch)
            i = j + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


class Qml(unittest.TestCase):
    files = glob.glob(os.path.join(DESKTOP, "**", "*.qml"), recursive=True)

    def test_brackets_balance(self):
        self.assertTrue(self.files)
        for path in self.files:
            with open(path, encoding="utf-8") as fh:
                code = strip_code(fh.read())
            for left, right in ("{}", "()", "[]"):
                self.assertEqual(code.count(left), code.count(right), "%s: %s%s" % (path, left, right))

    def test_imports_are_qt_or_plasma(self):
        for path in self.files:
            with open(path, encoding="utf-8") as fh:
                for module in re.findall(r"(?m)^import\s+(\S+)", fh.read()):
                    self.assertRegex(module, ALLOWED_IMPORTS, path)

    def test_components_used_by_name_are_next_to_their_users(self):
        for path in self.files:
            folder = os.path.dirname(path)
            with open(path, encoding="utf-8") as fh:
                code = strip_code(fh.read())
            for name in set(re.findall(r"(?m)^\s*(DockItem|AppTile|Tesseract)\s*\{", code)):
                # The splash screen gets the wallpaper's figure copied in when it is installed.
                shared = os.path.join(DESKTOP, "wallpaper", "org.ozios.tesseract", "contents", "ui", name + ".qml")
                self.assertTrue(os.path.isfile(os.path.join(folder, name + ".qml")) or
                                (path.endswith("Splash.qml") and os.path.isfile(shared)), "%s uses %s" % (path, name))

    def test_motion_respects_the_users_animation_setting(self):
        for applet in ("org.ozios.dock", "org.ozios.launcher"):
            self.assertIn("Kirigami.Units.longDuration > 1", read("desktop", "plasmoids", applet, "contents", "ui", "main.qml"))
        for component in (("org.ozios.dock", "DockItem.qml"), ("org.ozios.launcher", "AppTile.qml")):
            self.assertIn("property bool animate", read("desktop", "plasmoids", component[0], "contents", "ui", component[1]))

    def test_the_wallpaper_follows_the_theme_and_stops_when_covered(self):
        text = read("desktop", "wallpaper", "org.ozios.tesseract", "contents", "ui", "main.qml")
        self.assertIn("Kirigami.Theme.highlightColor", text)
        self.assertGreaterEqual(text.count("running: !root.still"), 3)


# --- the KWin effect, run against a stand-in for KWin ---------------------------------

HARNESS = r"""
const fs = require("fs");
const calls = [];
const signal = () => { const s = []; return { connect: f => s.push(f), emit: (...a) => s.forEach(f => f(...a)) }; };
global.effect = { configChanged: signal(), animationEnded: signal(), readConfig: (k, d) => d,
                  isGrabbed: () => false };
global.effects = { windowAdded: signal(), windowClosed: signal(), windowDataChanged: signal(),
                   hasActiveFullScreenEffect: false };
global.Effect = { Scale: "scale", Opacity: "opacity", Translation: "translation",
                  WindowAddedGrabRole: 1, WindowClosedGrabRole: 2, WindowForceBlurRole: 3 };
global.QEasingCurve = { OutBack: "OutBack", OutCubic: "OutCubic", InCubic: "InCubic", InQuad: "InQuad" };
global.animationTime = ms => ms;
let next = 1;
global.animate = settings => { calls.push(settings); return next++; };
const cancelled = [];
global.cancel = id => cancelled.push(id);
eval(fs.readFileSync(process.argv[2], "utf8"));

const win = (extra) => Object.assign({ windowClass: "dolphin org.kde.dolphin", visible: true, managed: true,
    normalWindow: true, dialog: false, hasDecoration: true, popupWindow: false, data: {},
    setData(role, v) { this.data[role] = v; } }, extra);
const normal = win({});
effects.windowAdded.emit(normal);
const popup = win({ hasDecoration: false, popupWindow: true, normalWindow: false });
effects.windowAdded.emit(popup);
const panel = win({ windowClass: "plasmashell org.kde.plasmashell", hasDecoration: false });
effects.windowAdded.emit(panel);
effects.windowClosed.emit(normal);
const dialog = win({ dialog: true, normalWindow: false });
effects.windowAdded.emit(dialog);
process.stdout.write(JSON.stringify({ calls, cancelled, blur: normal.data[3] }));
"""


@unittest.skipUnless(NODE, "node is not installed")
class Motion(unittest.TestCase):
    def run_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            harness = os.path.join(folder, "harness.js")
            with open(harness, "w", encoding="utf-8") as fh:
                fh.write(HARNESS)
            effect = os.path.join(DESKTOP, "kwin", "effects", "ozios_motion", "contents", "code", "main.js")
            done = subprocess.run([NODE, harness, effect], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_windows_rise_out_of_depth_and_sink_back(self):
        result = self.run_effect()
        calls = result["calls"]
        self.assertEqual(len(calls), 3)                       # the window opening, closing, and the dialog
        opening, closing, dialog = calls
        types = [a["type"] for a in opening["animations"]]
        self.assertEqual(types, ["scale", "opacity", "translation"])
        self.assertEqual(opening["animations"][0]["from"], 0.9)
        self.assertEqual(opening["animations"][0]["curve"], "OutBack")     # the slight spring
        self.assertGreater(opening["animations"][2]["from"]["value2"], 0)  # starts lower, rises
        self.assertEqual(closing["animations"][1]["to"], 0)
        self.assertLess(closing["duration"], opening["duration"])
        self.assertEqual(result["cancelled"], [1])            # closing stops the opening
        self.assertLess(dialog["duration"], opening["duration"])
        self.assertEqual(dialog["animations"][0]["from"], 0.95)

    def test_popups_and_the_shell_are_left_alone(self):
        result = self.run_effect()
        self.assertEqual(len(result["calls"]), 3)


@unittest.skipUnless(NODE, "node is not installed")
class Scripts(unittest.TestCase):
    def test_layout_scripts_parse_as_javascript(self):
        scripts = glob.glob(os.path.join(DESKTOP, "**", "*.js"), recursive=True) + glob.glob(os.path.join(ROOT, "edu", "layouts", "*.js"))
        for path in scripts:
            done = subprocess.run([NODE, "--check", path], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, path + "\n" + done.stderr)


if __name__ == "__main__":
    unittest.main()


# --- the real QML in Qt, on top of stand-ins for Plasma ------------------------------------

HAVE_QT = importlib.util.find_spec("PyQt6") is not None


def qt_env():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    if os.name == "nt":
        env.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    return env


@unittest.skipUnless(HAVE_QT, "PyQt6 is not installed")
class ShellInQt(unittest.TestCase):
    """The dock, launcher, control widget and wallpaper, loaded and driven in Qt.

    Plasma's own modules are replaced by tools/plasma_stubs.py, written against
    plasma-workspace and plasma-desktop 6.7; this catches mistakes in OziOS's
    QML, not in what Plasma does with it."""

    def run_tool(self, *args):
        done = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", args[0])] + list(args[1:]),
                              capture_output=True, text=True, env=qt_env(), timeout=300, cwd=ROOT)
        return done

    def test_every_scene_loads_without_a_single_warning(self):
        for extra in ([], ["--still", "--theme", "frost", "--lang", "en_US"]):
            done = self.run_tool("shell-preview.py", "--check", *extra)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("warnings: 0", done.stdout)

    def test_driven_by_pointer_and_keys(self):
        done = self.run_tool("shell-drive.py")
        self.assertEqual(done.returncode, 0, done.stderr)
        result = json.loads(done.stdout)
        self.assertEqual(result["warnings"], [])

        dock = result["dock"]
        self.assertEqual(dock["count"], 7)
        self.assertEqual(max(dock["zoom"]), dock["zoom"][1])           # the icon under the pointer grows most
        self.assertGreater(dock["zoom"][0], 1.05)                       # its neighbours a little
        self.assertEqual(dock["zoom"][-1], 1.0)                         # the far ones not at all
        self.assertEqual(set(dock["zoom_after"]), {1.0})                # and all settle when the pointer leaves
        self.assertEqual(dock["clicks"], [["tasks", "toggle-minimized", 0], ["tasks", "activate", 1],
                                          ["tasks", "activate", 2], ["tasks", "new-instance", 3]])
        self.assertTrue(dock["menu_opened"])
        self.assertEqual(dock["menu"], ["Open a new window", "Pin to the dock", "Close"])
        self.assertEqual(dock["pin_calls"], [["tasks", "pin", "applications:firefox.desktop"]])
        self.assertIn("applications:firefox.desktop", dock["saved_launchers"])
        self.assertEqual(dock["status"], 3)                             # a window wants attention

        launcher = result["launcher"]
        self.assertTrue(launcher["expanded"])
        self.assertEqual(launcher["click"], [["apps", "launch", "Ark"]])
        self.assertTrue(launcher["closed_after_launch"])
        self.assertEqual(launcher["results"], 1)
        self.assertEqual(launcher["search"], [["apps", "launch", "Firefox"]])
        self.assertLess(launcher["category_programs"], launcher["programs"])
        self.assertEqual(launcher["power_buttons"], ["lock-screen", "logout", "reboot", "shutdown"])
        self.assertEqual(launcher["power"], [["system", "trigger", "shutdown"]])

        control = result["control"]
        self.assertEqual(control["swatches"], [t.id for t in themes.THEMES])
        self.assertEqual(control["commands"], ["ozi theme aurora", "ozi effects off", "ozi mode game on"])

        wallpaper = result["wallpaper"]
        self.assertTrue(wallpaper["turning"])
        self.assertFalse(wallpaper["turning_when_covered"])


@unittest.skipUnless(HAVE_QT, "PyQt6 is not installed")
class StyleInQt(unittest.TestCase):
    """The Plasma style's frames drawn with Qt's SVG renderer, which KSvg uses too."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtGui import QGuiApplication
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import plasma_style
        cls.style = plasma_style

    def draw(self, name, theme_id, width, height, borders=("top", "bottom", "left", "right"), variant=""):
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QImage, QPainter
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        self.style.frame(painter, name, QRectF(0, 0, width, height), theme_id, borders=borders, variant=variant)
        painter.end()
        return image

    def test_frames_have_round_corners_a_rim_and_no_seams(self):
        for name in ("widgets/panel-background", "dialogs/background", "widgets/tooltip", "widgets/background"):
            for variant in ("", "translucent/", "opaque/"):
                image = self.draw(name, "cyan", 300, 90, variant=variant)
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0, (name, variant))        # outside the round corner
                self.assertGreater(image.pixelColor(150, 0).alpha(), 0, (name, variant))     # the rim
                middle = {image.pixelColor(x, 45).alpha() for x in range(1, 299)}
                self.assertEqual(len(middle), 1, (name, variant, middle))                    # one sheet, no seams
                column = {image.pixelColor(150, y).alpha() for y in range(1, 89)}
                self.assertEqual(len(column), 1, (name, variant, column))

    def test_the_sheet_takes_each_themes_colours(self):
        for theme in themes.THEMES:
            image = self.draw("dialogs/background", theme.id, 200, 100, variant="opaque/")
            centre = image.pixelColor(100, 50)
            self.assertEqual((centre.red(), centre.green(), centre.blue()), theme.ink, theme.id)
            rim = image.pixelColor(100, 0)
            self.assertGreater(sum(abs(a - b) for a, b in zip((rim.red(), rim.green(), rim.blue()), theme.ink)), 20, theme.id)

    def test_a_bar_at_the_top_edge_has_only_its_bottom_line(self):
        image = self.draw("widgets/panel-background", "cyan", 400, 32, borders=("bottom",))
        self.assertGreater(image.pixelColor(0, 0).alpha(), 0)          # square, it meets the screen's corners
        top, bottom = image.pixelColor(200, 0), image.pixelColor(200, 31)
        self.assertNotEqual((top.red(), top.green(), top.blue()), (bottom.red(), bottom.green(), bottom.blue()))


class Defaults(unittest.TestCase):
    def test_file_search_does_not_read_every_document(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read_string(read("desktop", "defaults", "baloofilerc"))
        self.assertEqual(parser["General"]["only basic indexing"], "true")
        self.assertIn('"$src/desktop/defaults/baloofilerc" "$pkgdir/etc/xdg/baloofilerc"', read("packages", "ozios-settings", "PKGBUILD"))
