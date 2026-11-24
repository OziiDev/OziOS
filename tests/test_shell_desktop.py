"""ozi-shell's logic (python/ozipkg/shell.py): apps, search, dock, status."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import shell  # noqa: E402

KONSOLE = """[Desktop Entry]
Type=Application
Name=Konsole
Name[tr]=Konsol
GenericName=Terminal
Exec=konsole %U
Icon=utilities-terminal
Categories=Qt;KDE;System;TerminalEmulator;
Keywords=terminal;komut;
"""


def write(root, name, text):
    path = os.path.join(root, "applications", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class DesktopEntries(unittest.TestCase):
    def test_localized_name_and_fields(self):
        e = shell.parse_desktop_entry(KONSOLE, "tr_TR")
        self.assertEqual(e["name"], "Konsol")
        self.assertEqual(e["icon"], "utilities-terminal")
        self.assertIn("System", e["categories"])

    def test_hidden_and_foreign_entries_are_skipped(self):
        self.assertIsNone(shell.parse_desktop_entry(KONSOLE + "NoDisplay=true\n"))
        self.assertIsNotNone(shell.parse_desktop_entry(KONSOLE + "OnlyShowIn=KDE;\n"))
        self.assertIsNone(shell.parse_desktop_entry(KONSOLE + "OnlyShowIn=GNOME;\n"))
        self.assertIsNone(shell.parse_desktop_entry(KONSOLE + "NotShowIn=KDE;\n"))
        self.assertIsNotNone(shell.parse_desktop_entry(KONSOLE + "OnlyShowIn=KDE;OziOS;\n"))
        self.assertIsNone(shell.parse_desktop_entry("[Desktop Entry]\nType=Link\nName=x\n"))
        self.assertIsNone(shell.parse_desktop_entry("garbage"))

    def test_applications_user_dir_wins(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as system:
            write(system, "org.kde.konsole.desktop", KONSOLE)
            write(home, "org.kde.konsole.desktop", KONSOLE.replace("Name[tr]=Konsol", "Name[tr]=Benim"))
            write(system, "kde/sub.desktop", KONSOLE.replace("Konsole", "Sub"))
            env = {"XDG_DATA_HOME": home, "XDG_DATA_DIRS": system, "LANG": "tr_TR.UTF-8"}
            apps = {a["id"]: a for a in shell.applications(env)}
            self.assertEqual(apps["org.kde.konsole"]["name"], "Benim")
            self.assertIn("kde-sub", apps)

    def test_exec_field_codes_are_dropped(self):
        self.assertEqual(shell.command_for("konsole %U"), ["konsole"])
        self.assertEqual(shell.command_for('env A=1 "my app" --x %f'), ["env", "A=1", "my app", "--x"])
        self.assertEqual(shell.command_for("htop", terminal=True), ["konsole", "-e", "htop"])


class Search(unittest.TestCase):
    APPS = [
        {"id": "org.kde.konsole", "name": "Konsol", "generic": "Terminal", "comment": "", "keywords": "komut"},
        {"id": "firefox", "name": "Firefox", "generic": "Web Tarayıcı", "comment": "", "keywords": ""},
        {"id": "org.kde.dolphin", "name": "Dolphin", "generic": "Dosya Yöneticisi", "comment": "", "keywords": ""},
        {"id": "ozi-look", "name": "Görünüm", "generic": "", "comment": "", "keywords": "tema"},
    ]

    def names(self, q):
        return [a["name"] for a in shell.search(self.APPS, q)]

    def test_name_start_first(self):
        self.assertEqual(self.names("fi")[0], "Firefox")

    def test_turkish_letters_fold(self):
        self.assertEqual(self.names("gorunum"), ["Görünüm"])
        self.assertEqual(self.names("TARAYICI"), ["Firefox"])

    def test_other_fields_count(self):
        self.assertEqual(self.names("tema"), ["Görünüm"])
        self.assertEqual(self.names("komut"), ["Konsol"])

    def test_empty_query_lists_everything(self):
        self.assertEqual(len(shell.search(self.APPS, "  ")), 4)

    def test_no_match(self):
        self.assertEqual(shell.search(self.APPS, "zzz"), [])


class Dock(unittest.TestCase):
    APPS = {
        "org.kde.konsole": {"id": "org.kde.konsole", "name": "Konsol", "icon": "utilities-terminal", "exec": "konsole", "terminal": False, "wm_class": ""},
        "firefox": {"id": "firefox", "name": "Firefox", "icon": "firefox", "exec": "firefox", "terminal": False, "wm_class": ""},
    }

    def test_pinned_then_running(self):
        windows = [
            {"id": 3, "app_id": "org.kde.konsole", "title": "a", "focused": True},
            {"id": 4, "app_id": "com.example.thing", "title": "Thing", "focused": False},
        ]
        items = shell.dock_items(self.APPS, ["firefox", "org.kde.konsole"], windows)
        self.assertEqual([i["id"] for i in items], ["firefox", "org.kde.konsole", "com.example.thing"])
        self.assertEqual(items[1]["windows"], [3])
        self.assertTrue(items[1]["active"])
        self.assertFalse(items[2]["pinned"])

    def test_app_id_matching(self):
        self.assertEqual(shell.match_app(self.APPS, "konsole")["id"], "org.kde.konsole")
        self.assertIsNone(shell.match_app(self.APPS, ""))

    def test_pins_come_from_the_config(self):
        with tempfile.TemporaryDirectory() as cfg:
            env = {"XDG_CONFIG_HOME": cfg}
            self.assertEqual(shell.pins(self.APPS, env), ["firefox", "org.kde.konsole"])  # defaults that exist
            shell.write_config({"dock": ["firefox", "missing"]}, env)
            self.assertEqual(shell.pins(self.APPS, env), ["firefox"])
            shell.write_config({"theme": "mint"}, env)
            self.assertEqual(shell.read_config(env), {"dock": ["firefox", "missing"], "theme": "mint"})


class Status(unittest.TestCase):
    def test_volume(self):
        self.assertEqual(shell.parse_wpctl_volume("Volume: 0.45\n"), (45, False))
        self.assertEqual(shell.parse_wpctl_volume("Volume: 1.00 [MUTED]\n"), (100, True))
        self.assertIsNone(shell.parse_wpctl_volume(""))

    def test_network_prefers_wired(self):
        text = "wifi:connected:Ev Ağı\nethernet:connected:Kablolu\nloopback:connected (externally):lo\n"
        self.assertEqual(shell.parse_nmcli(text), {"kind": "wired", "name": "Kablolu"})
        self.assertEqual(shell.parse_nmcli("wifi:connected:Kafe\\:2\n"), {"kind": "wifi", "name": "Kafe:2"})
        self.assertEqual(shell.parse_nmcli("wifi:disconnected:\n")["kind"], "none")

    def test_battery(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(shell.battery(root), {"present": False})
            bat = os.path.join(root, "BAT0")
            os.makedirs(bat)
            for name, value in (("type", "Battery"), ("capacity", "87"), ("status", "Charging")):
                with open(os.path.join(bat, name), "w") as f:
                    f.write(value + "\n")
            self.assertEqual(shell.battery(root), {"present": True, "percent": 87, "charging": True})


class Look(unittest.TestCase):
    def test_palette_has_every_colour(self):
        for theme_id in shell.theme_ids():
            p = shell.palette(theme_id)
            for key in ("ink", "raised", "control", "text", "muted", "accent", "accent2"):
                self.assertRegex(p[key], r"^#[0-9A-F]{6}$")
        self.assertEqual(shell.palette("nope")["id"], "cyan")

    def test_accent2_matches_the_compositor(self):
        rust = open(os.path.join(os.path.dirname(__file__), "..", "oziwm", "src", "theme.rs")).read()
        for theme_id, rgb in shell.ACCENT2.items():
            self.assertIn('id: "%s"' % theme_id, rust)
            line = next(l for l in rust.splitlines() if 'id: "%s"' % theme_id in l)
            self.assertIn("accent2: rgb(%d, %d, %d)" % rgb, line)

    def test_look_defaults_and_ranges(self):
        with tempfile.TemporaryDirectory() as cfg:
            env = {"XDG_CONFIG_HOME": cfg}
            self.assertEqual(shell.look(env), shell.LOOK_DEFAULTS)
            shell.write_config({"glow": 9, "corner_radius": -3, "theme": "ember"}, env)
            look = shell.look(env)
            self.assertEqual((look["glow"], look["corner_radius"], look["theme"]), (1.0, 0, "ember"))
            shell.write_config({"glow": "much"}, env)
            self.assertEqual(shell.look(env), shell.LOOK_DEFAULTS)


class Radios(unittest.TestCase):
    def test_radio(self):
        self.assertEqual(shell.parse_nmcli_radio("enabled:disabled:missing:enabled\n"), {"wifi_hw": True, "wifi": False})
        self.assertEqual(shell.parse_nmcli_radio(""), {"wifi_hw": False, "wifi": False})

    def test_wifi_list(self):
        text = " :Ozi:80:WPA2\n*:Ozi:100:WPA2\n ::29:WPA2\n :Kafe\\:2:60:\n :Komşu:40:WPA1 WPA2\n"
        nets = shell.parse_wifi_list(text)
        self.assertEqual([n["ssid"] for n in nets], ["Ozi", "Kafe:2", "Komşu"])
        self.assertTrue(nets[0]["active"])
        self.assertEqual(nets[0]["signal"], 100)
        self.assertFalse(nets[1]["secure"])
        self.assertTrue(nets[2]["secure"])

    def test_bluetooth(self):
        self.assertTrue(shell.parse_bt_powered("Controller X\n\tPowered: yes\n"))
        self.assertFalse(shell.parse_bt_powered("\tPowered: no\n"))
        devs = shell.parse_bt_devices("Device AA:BB:CC:DD:EE:FF Kulaklık\nnoise\n")
        self.assertEqual(devs, [("AA:BB:CC:DD:EE:FF", "Kulaklık")])

    def test_airplane(self):
        self.assertTrue(shell.airplane({"wifi": False}, {"available": True, "powered": False}))
        self.assertFalse(shell.airplane({"wifi": True}, {"available": False, "powered": False}))
        self.assertTrue(shell.airplane({"wifi": False}, {"available": False, "powered": False}))

    def test_brightness_never_black(self):
        self.assertEqual(shell.brightness_percent(937, 937), 100)
        self.assertEqual(shell.brightness_value(0, 937), 9)
        self.assertEqual(shell.brightness_value(50, 937), 468)
        self.assertEqual(shell.brightness_value(200, 937), 937)

    def test_brightness_from_sysfs(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(shell.brightness(root), {"available": False, "percent": 100})
            for name, cur in (("acpi_video0", "5"), ("intel_backlight", "468")):
                os.makedirs(os.path.join(root, name))
                with open(os.path.join(root, name, "brightness"), "w") as f:
                    f.write(cur)
                with open(os.path.join(root, name, "max_brightness"), "w") as f:
                    f.write("937" if name.startswith("intel") else "10")
            self.assertEqual(shell.brightness(root), {"available": True, "percent": 50})


ROOT = os.path.join(os.path.dirname(__file__), "..")


class Packaging(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
            return f.read()

    def test_session_pieces_point_at_each_other(self):
        pkgbuild = self.read("packages", "ozi-desktop", "PKGBUILD")
        session = self.read("session", "ozios.desktop")
        start = self.read("session", "ozi-session")
        self.assertIn("Exec=ozi-session", session)
        self.assertIn("/usr/bin/ozi-session", pkgbuild)
        self.assertIn("/usr/lib/ozios/ozi-session-start", pkgbuild)
        self.assertIn("/usr/lib/ozios/ozi-session-start", start)
        self.assertIn("/usr/share/wayland-sessions/ozios.desktop", pkgbuild)
        self.assertIn("ozi-shell", self.read("session", "ozi-session-start"))

    def test_qml_uses_only_qt_and_layer_shell(self):
        allowed = {"QtQuick", "QtQuick.Window", "org.kde.layershell"}
        qml_dir = os.path.join(ROOT, "shell", "qml")
        names = sorted(n for n in os.listdir(qml_dir) if n.endswith(".qml"))
        self.assertIn("Main.qml", names)
        for name in names:
            for line in self.read("shell", "qml", name).splitlines():
                if line.startswith("import "):
                    module = line.split()[1]
                    self.assertIn(module, allowed, "%s imports %s" % (name, module))

    def test_wallpapers_match_their_generator(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("mw", os.path.join(ROOT, "tools", "make-wallpapers.py"))
        mw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mw)
        for name, make in mw.SCENES.items():
            self.assertEqual(self.read("branding", "wallpapers", name), make(), name)

    def test_root_qml_is_not_named_after_the_backend(self):
        # A file called Shell.qml would hide the `Shell` context property.
        self.assertFalse(os.path.exists(os.path.join(ROOT, "shell", "qml", "Shell.qml")))


if __name__ == "__main__":
    unittest.main()
