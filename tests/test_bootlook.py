import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import bootlook, shell  # noqa: E402

CONF = """timeout: 5
default_entry: 2

# CachyOS Limine theme
# Author: diegons490 (https://github.com/diegons490/cachyos-limine-theme)
term_palette: 1e1e2e;f38ba8;a6e3a1;f9e2af;89b4fa;f5c2e7;94e2d5;cdd6f4
term_background: ffffffff
interface_branding:
wallpaper: boot():/limine-splash.png

comment: machine-id=abc
/+OziOS
  //linux-ozios
  protocol: linux
  wallpaper: boot():/not-ours.png
  cmdline: quiet rw
"""


class RewriteTest(unittest.TestCase):
    def setUp(self):
        self.lines = bootlook.theme_lines(shell.palette("mint"), "boot():/limine-splash.png")

    def test_only_the_theme_lines_at_the_top_change(self):
        out = bootlook.rewrite(CONF, self.lines)
        head, _, entries = out.partition("/+OziOS")
        self.assertIn("timeout: 5\ndefault_entry: 2\n", head)
        self.assertIn("comment: machine-id=abc", head)
        self.assertNotIn("CachyOS Limine theme", head)
        self.assertNotIn("1e1e2e", head)
        self.assertEqual(head.count("wallpaper:"), 1)
        self.assertIn("interface_branding: OziOS", head)
        # Entries, and options inside them, stay as they were.
        self.assertEqual("/+OziOS" + entries, CONF[CONF.index("/+OziOS"):])

    def test_running_twice_changes_nothing(self):
        once = bootlook.rewrite(CONF, self.lines)
        self.assertEqual(bootlook.rewrite(once, self.lines), once)

    def test_limine_colour_formats(self):
        values = dict(l.split(": ", 1) for l in self.lines if ": " in l and not l.startswith("#"))
        self.assertRegex(values["term_background"], r"^[0-9A-F]{8}$")
        self.assertRegex(values["term_foreground"], r"^[0-9A-F]{6}$")
        self.assertEqual(len(values["term_palette"].split(";")), 8)

    def test_root_copies_only_pictures_the_user_may_read(self):
        self.assertIsNone(bootlook.usable_picture("tesseract", None))
        self.assertIsNone(bootlook.usable_picture("relative.png", None))
        self.assertIsNone(bootlook.usable_picture("/etc/shadow", None))
        self.assertEqual(bootlook.usable_picture("/etc/hostname", None) or "/etc/hostname", "/etc/hostname")


if __name__ == "__main__":
    unittest.main()
