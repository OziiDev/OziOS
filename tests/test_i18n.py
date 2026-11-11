import ast
import glob
import json
import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "python"))

from ozipkg import i18n  # noqa: E402


def source_strings():
    """Every English string the code can pass to tr()."""
    found = set()
    for path in glob.glob(os.path.join(ROOT, "python", "ozipkg", "*.py")):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr" and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                found.add(node.args[0].value)
            # rule tables pass their titles and details through tr() later
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_rule":
                found.update(arg.value for arg in node.args[4:6])
            if isinstance(node, ast.Tuple) and len(node.elts) == 4 and all(isinstance(e, ast.Constant) for e in node.elts) \
                    and node.elts[1].value in ("danger", "warning", "notice") \
                    and node.elts[0].value not in ("info", "notice", "warning", "danger"):
                found.add(node.elts[3].value)
    # QML files call backend.tr("...") for the same table
    for path in glob.glob(os.path.join(ROOT, "apps", "**", "*.qml"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            found.update(re.findall(r'backend\.tr\("((?:[^"\\]|\\.)*)"\)', fh.read()))
    return found


def table():
    with open(os.path.join(ROOT, "data", "i18n", "tr.json"), encoding="utf-8") as fh:
        return json.load(fh)


def fields(text):
    return sorted(re.findall(r"\{(\w+)\}", text))


class Translations(unittest.TestCase):
    def test_every_string_is_translated(self):
        missing = sorted(s for s in source_strings() if s not in table())
        self.assertEqual(missing, [])

    def test_no_stale_entries(self):
        stale = sorted(k for k in table() if k not in source_strings())
        self.assertEqual(stale, [])

    def test_placeholders_match(self):
        for english, turkish in table().items():
            self.assertEqual(fields(english), fields(turkish), english)

    def test_nothing_is_left_empty_or_identical(self):
        for english, turkish in table().items():
            self.assertTrue(turkish.strip(), english)
            if english not in ("Terminal",):               # words that are the same in both languages
                self.assertNotEqual(english, turkish, english)


class Lookup(unittest.TestCase):
    def setUp(self):
        self.old = {k: os.environ.get(k) for k in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG", "OZIOS_DATA")}
        for key in self.old:
            os.environ.pop(key, None)
        i18n.reset()

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        i18n.reset()

    def test_turkish_session(self):
        os.environ["LANG"] = "tr_TR.UTF-8"
        self.assertEqual(i18n.tr("Camera"), "Kamera")
        self.assertEqual(i18n.tr("Building {name}...", name="vlc"), "vlc derleniyor...")

    def test_other_languages_get_english(self):
        os.environ["LANG"] = "de_DE.UTF-8"
        self.assertEqual(i18n.tr("Camera"), "Camera")

    def test_unknown_text_passes_through(self):
        os.environ["LANG"] = "tr_TR.UTF-8"
        self.assertEqual(i18n.tr("Not in the table"), "Not in the table")


if __name__ == "__main__":
    unittest.main()
