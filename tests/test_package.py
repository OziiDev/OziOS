"""Static checks that catch the mistakes a build in the VM would otherwise find."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class Pkgbuild(unittest.TestCase):
    def test_every_installed_source_exists(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        missing = []
        for match in re.finditer(r'"\$(?:src|here|theme_src)/([^"]+)"', text):
            rel = match.group(1)
            if "$" in rel.replace("$wallpaper", "").replace("$control", ""):
                continue
            rel = rel.replace("$wallpaper", "org.ozios.tesseract").replace("$control", "org.ozios.control")
            base = "packages/ozios-settings/" if "$here" in match.group(0) else ""
            if "theme_src" in match.group(0):
                base = "desktop/look-and-feel/org.ozios.desktop/"
            if not glob.glob(os.path.join(ROOT, base + rel)):
                missing.append(base + rel)
        self.assertEqual(missing, [])

    def test_depends_on_what_the_apps_import(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        for dep in ("python-pyqt6", "qt6-declarative", "polkit"):
            self.assertRegex(text, r"depends=\([^)]*\b%s\b" % dep)


class Metadata(unittest.TestCase):
    def test_json_files_parse(self):
        for path in glob.glob(os.path.join(ROOT, "desktop", "**", "*.json"), recursive=True) + \
                glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                json.load(fh)

    def test_plasma_packages_carry_an_id_matching_their_folder(self):
        for path in glob.glob(os.path.join(ROOT, "desktop", "*", "org.ozios.*", "metadata.json")):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["KPlugin"]["Id"], os.path.basename(os.path.dirname(path)))

    def test_desktop_files_have_the_basics(self):
        for path in glob.glob(os.path.join(ROOT, "apps", "*.desktop")) + glob.glob(os.path.join(ROOT, "winbridge", "*.desktop")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertTrue(text.startswith("[Desktop Entry]"), path)
            for key in ("Type=", "Name=", "Exec="):
                self.assertIn("\n" + key, text, path)


class Qml(unittest.TestCase):
    """No Qt here, so only the mistakes that can be seen in the text."""

    def files(self):
        return glob.glob(os.path.join(ROOT, "apps", "**", "*.qml"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "desktop", "**", "*.qml"), recursive=True)

    @staticmethod
    def strip(text):
        text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)      # strings first: they may contain "//"
        return re.sub(r"//[^\n]*", "", text)

    def test_brackets_balance(self):
        for path in self.files():
            with open(path, encoding="utf-8") as fh:
                text = self.strip(fh.read())
            for open_, close in ("{}", "()", "[]"):
                self.assertEqual(text.count(open_), text.count(close), "%s: %s%s" % (path, open_, close))

    def test_components_are_listed_in_the_module(self):
        listed = set(re.findall(r"^(?:singleton )?(\w+) 1\.0 ", read("apps", "OziUi", "qmldir"), re.M))
        files = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, "apps", "OziUi", "*.qml"))}
        self.assertEqual(listed, files)

    def test_apps_use_only_known_backend_calls(self):
        for app in ("ozi-store", "ozi-welcome"):
            qml = read("apps", app, "Main.qml")
            py = read("apps", app, app)
            names = set(re.findall(r'backend\.call\("[^"]*",\s*"(\w+)"', qml)) | set(re.findall(r'run\("[^"]*",\s*"(\w+)"', qml))
            for name in names:
                self.assertIn('"%s":' % name, py, "%s calls %s, which the backend does not allow" % (app, name))


if __name__ == "__main__":
    unittest.main()
