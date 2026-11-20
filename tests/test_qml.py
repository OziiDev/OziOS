import glob
import importlib.util
import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
# The windows load in a child Python started with -I, which ignores the user's own
# site-packages; ask that Python, not this one, whether Qt is there.
HAVE_QT = importlib.util.find_spec("PyQt6") is not None and subprocess.run(
    [sys.executable, "-I", "-c", "import PyQt6.QtCore"], capture_output=True).returncode == 0


def offscreen_env(**extra):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", LANG="C.UTF-8")
    if os.name == "nt":
        # Qt's offscreen platform on Windows looks for fonts next to Qt itself, where there are none.
        env.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    env.update(extra)
    return env


def apps():
    return sorted(os.path.basename(os.path.dirname(path)) for path in glob.glob(os.path.join(ROOT, "apps", "*", "Main.qml")))


@unittest.skipUnless(HAVE_QT, "PyQt6 is not installed")
class Windows(unittest.TestCase):
    """Every app's window loads without a single warning from Qt (a mistyped property, a missing import)."""

    def test_each_app_loads_clean(self):
        names = apps()
        self.assertTrue(names)
        # The default theme, and the light one, whose palette the apps take on at start-up.
        for theme in ("cyan", "frost"):
            env = offscreen_env(OZIOS_THEME=theme)
            for name in names:
                with self.subTest(app=name, theme=theme):
                    result = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "qml-check.py"),
                                             os.path.join("apps", name), "1"],
                                            capture_output=True, text=True, env=env, timeout=120, cwd=ROOT)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("loaded: True | warnings: 0", result.stdout)


class Sources(unittest.TestCase):
    def test_every_app_has_a_launcher_and_a_desktop_entry(self):
        for name in apps():
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "apps", name, name)), name)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "apps", name + ".desktop")), name)

    def test_every_launcher_names_its_own_desktop_file(self):
        for name in apps():
            with open(os.path.join(ROOT, "apps", name + ".desktop"), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("StartupWMClass=" + name, text, name)
            self.assertIn("Exec=" + name, text, name)


if __name__ == "__main__":
    unittest.main()
