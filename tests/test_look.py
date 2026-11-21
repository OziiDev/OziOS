import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import look  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))


class Reading(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()

    def write(self, name, text):
        with open(os.path.join(self.home, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_nothing_written_yet_is_the_fluid_preset(self):
        values = look.read_all(self.home)
        self.assertEqual(values, look.PRESETS["fluid"])
        self.assertEqual(look.current_preset(values), "fluid")

    def test_values_come_from_kwin_the_frames_and_kdeglobals(self):
        self.write("ozidecorationrc", "[Decoration]\nCornerRadius=14\nOutlineWidth=0\nGlow=false\nTitleBar=false\n")
        self.write("kwinrc", "[Plugins]\nblurEnabled=false\nslideEnabled=true\n\n[Script-ozios-tiling]\nGap=4\nTileByDefault=true\n")
        self.write("kdeglobals", "[General]\nColorScheme=OziOS\n\n[KDE]\nAnimationDurationFactor=0.9\n")
        self.assertEqual(look.read_all(self.home), {"radius": 14, "outline": 0, "glow": False, "titlebar": False,
                                                    "gaps": 4, "tiling": True, "blur": False, "speed": "relaxed"})
        self.assertEqual(look.current_preset(look.read_all(self.home)), "")

    def test_the_speed_is_the_nearest_named_one(self):
        for factor, name in (("0", "off"), ("0.02", "off"), ("0.5", "fast"), ("0.6", "fast"), ("0.7", "normal"),
                             ("1", "relaxed"), ("3", "relaxed"), ("x", "normal")):
            self.write("kdeglobals", "[KDE]\nAnimationDurationFactor=%s\n" % factor)
            self.assertEqual(look.read_all(self.home)["speed"], name, factor)

    def test_a_broken_value_falls_back_to_the_default(self):
        self.write("ozidecorationrc", "[Decoration]\nCornerRadius=round\nGlow=maybe\n")
        values = look.read_all(self.home)
        self.assertEqual((values["radius"], values["glow"]), (10, True))

    def test_every_preset_is_whole_and_valid(self):
        for name, values in look.PRESETS.items():
            self.assertEqual(set(values), set(look.ORDER), name)
            for key, value in values.items():
                self.assertEqual(look.check(key, value), value, (name, key))

    def test_the_state_for_the_app(self):
        state = look.state(self.home)
        self.assertEqual(state["preset"], "fluid")
        self.assertEqual([p["id"] for p in state["presets"]], ["fluid", "tiling", "light"])
        self.assertEqual([s["id"] for s in state["speeds"]], ["off", "fast", "normal", "relaxed"])
        self.assertEqual(state["ranges"], {"radius": [0, 24], "outline": [0, 4], "gaps": [0, 40]})
        json.dumps(state)


class Writing(unittest.TestCase):
    def test_values_are_checked(self):
        self.assertEqual(look.check("radius", "12"), 12)
        self.assertEqual(look.check("glow", "off"), False)
        self.assertEqual(look.check("glow", True), True)
        self.assertEqual(look.check("speed", "fast"), "fast")
        for name, value in (("radius", 25), ("radius", -1), ("gaps", "wide"), ("glow", "maybe"), ("speed", "warp"),
                            ("colour", 1)):
            with self.assertRaises(ValueError):
                look.check(name, value)

    def test_a_setting_is_written_and_kwin_rereads(self):
        run = Recorder()
        look.set_value("radius", 14, run=run, qdbus="qdbus6")
        self.assertEqual(run.calls, [
            ["kwriteconfig6", "--file", "ozidecorationrc", "--group", "Decoration", "--key", "CornerRadius", "14"],
            ["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
        ])

    def test_gaps_are_a_little_wider_at_the_screens_edge(self):
        run = Recorder()
        look.set_value("gaps", 8, run=run, qdbus="")
        self.assertEqual(run.calls, [
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Script-ozios-tiling", "--key", "Gap", "8"],
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Script-ozios-tiling", "--key", "OuterGap", "10"],
        ])
        run = Recorder()
        look.set_value("gaps", 0, run=run, qdbus="")
        self.assertIn(["kwriteconfig6", "--file", "kwinrc", "--group", "Script-ozios-tiling", "--key", "OuterGap", "0"],
                      run.calls)

    def test_speed_is_announced_and_blur_loads_or_unloads(self):
        run = Recorder()
        look.set_values({"speed": "fast", "blur": False}, run=run, qdbus="qdbus6")
        self.assertIn(["kwriteconfig6", "--file", "kdeglobals", "--group", "KDE", "--key", "AnimationDurationFactor",
                       "--notify", "0.5"], run.calls)
        self.assertIn(["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins", "--key", "blurEnabled", "false"], run.calls)
        self.assertIn(["qdbus6", "org.kde.KWin", "/Effects", "org.kde.kwin.Effects.unloadEffect", "blur"], run.calls)
        self.assertEqual(run.calls[-1], ["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"])

    def test_nothing_is_written_when_a_value_is_wrong(self):
        run = Recorder()
        with self.assertRaises(ValueError):
            look.set_values({"radius": 8, "gaps": 99}, run=run, qdbus="qdbus6")
        self.assertEqual(run.calls, [])

    def test_a_preset_writes_every_setting(self):
        run = Recorder()
        look.apply_preset("tiling", run=run, qdbus="qdbus6")
        keys = [c[c.index("--key") + 1] for c in run.calls if c[0] == "kwriteconfig6"]
        self.assertEqual(sorted(keys), sorted(["CornerRadius", "OutlineWidth", "Glow", "TitleBar", "Gap", "OuterGap",
                                               "TileByDefault", "blurEnabled", "AnimationDurationFactor"]))
        self.assertIn(["kwriteconfig6", "--file", "ozidecorationrc", "--group", "Decoration", "--key", "TitleBar", "false"],
                      run.calls)
        with self.assertRaises(ValueError):
            look.apply_preset("loud", run=run, qdbus="qdbus6")


class Command(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.lines = []
        self.run = Recorder()

    def main(self, *argv):
        return look.main(list(argv), out=self.lines.append, run=self.run, home=self.home, qdbus="qdbus6")

    def test_without_arguments_it_lists_the_settings(self):
        self.assertEqual(self.main(), 0)
        self.assertEqual(self.lines[0], "Preset: Fluid")
        self.assertEqual(len(self.lines), 1 + len(look.ORDER))
        self.assertIn("Corner radius", self.lines[1])

    def test_json(self):
        self.assertEqual(self.main("--json"), 0)
        self.assertEqual(json.loads(self.lines[0])["preset"], "fluid")

    def test_a_preset(self):
        self.assertEqual(self.main("preset", "light"), 0)
        self.assertEqual(self.lines, ["Look: Light"])
        self.assertEqual(self.main("preset"), 2)
        self.assertEqual(self.main("preset", "loud"), 2)
        self.assertEqual(self.lines[-1], "There is no preset called loud")

    def test_one_setting(self):
        self.assertEqual(self.main("titlebar", "off"), 0)
        self.assertEqual(self.lines, ["Title bars: off"])
        self.assertEqual(self.main("radius"), 0)
        self.assertEqual(self.lines[-1], "10")
        self.assertEqual(self.main("radius", "99"), 2)
        self.assertEqual(self.lines[-1], "radius takes a number from 0 to 24")
        self.assertEqual(self.main("volume", "3"), 2)


class Wiring(unittest.TestCase):
    def test_ozi_hands_look_to_python(self):
        self.assertIn("doctor | report | clean | play | gaming | theme | look)", read("packages", "ozi-cli", "ozi"))
        self.assertIn('"look": look.main', read("python", "ozipkg", "tools.py"))

    def test_the_app_and_the_card_of_keys_are_installed(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        for needle in ('"$src/apps/ozi-look/ozi-look" "$apps/ozi-look/ozi-look"', '"$pkgdir/usr/bin/ozi-look"',
                       "applications/ozi-look.desktop", "applications/ozi-keys.desktop"):
            self.assertIn(needle, text)
        keys = read("apps", "ozi-keys.desktop")
        self.assertIn("Exec=ozi-look --keys", keys)
        self.assertIn("X-KDE-Shortcuts=Meta+K", keys)
        self.assertIn("StartupWMClass=ozi-keys", keys)
        self.assertIn('"ozi-keys" if keys else "ozi-look"', read("apps", "ozi-look", "ozi-look"))

    def test_the_card_lists_the_keys_apply_branding_sets(self):
        qml = read("apps", "ozi-look", "Main.qml")
        branding = read("tools", "apply-branding.sh")
        for key in ("Meta+T", "Meta+F", "Meta+Q", "Meta+Enter", "Meta+K", "Meta+Ctrl+1"):
            self.assertIn('"%s' % key, qml)
        self.assertIn('shortcut kwin "Window Close" $((0x09000033)) $((0x10000051))', branding)
        self.assertIn('shortcut org.kde.konsole.desktop _launch $((0x0C000054)) $((0x11000004))', branding)
        self.assertIn('shortcut plasmashell "manage activities" $((0x12000051))', branding)
        self.assertLess(branding.index('shortcut plasmashell "manage activities" $((0x12000051))'),
                        branding.index('shortcut kwin "Window Close" $((0x09000033)) $((0x10000051))'))
        undo = branding.split('if [ "${1:-}" = "--undo" ]; then')[1].split("\nfi\n")[0]
        self.assertIn('shortcut kwin "Window Close" $((0x09000033))\n', undo)
        self.assertIn('shortcut plasmashell "manage activities" $((0x10000051))', undo)


if __name__ == "__main__":
    unittest.main()
