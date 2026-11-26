import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import shell, wallcolors  # noqa: E402


def hue_of(hex_colour):
    import colorsys
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


class PickTest(unittest.TestCase):
    def test_the_main_colour_becomes_the_accent(self):
        green = [(40, 200, 90)] * 700 + [(30, 120, 220)] * 200 + [(10, 10, 10)] * 100
        colors = wallcolors.to_hex(wallcolors.pick(green))
        self.assertAlmostEqual(hue_of(colors["accent"]), 140, delta=10)
        self.assertAlmostEqual(hue_of(colors["accent2"]), 212, delta=12)

    def test_dark_surfaces_and_readable_accent(self):
        for pixels in ([(250, 40, 40)] * 50, [(20, 20, 200)] * 50, [(255, 255, 0)] * 50):
            p = wallcolors.pick(pixels)
            self.assertLess(wallcolors._luminance(p["ink"]), 0.01)
            self.assertGreaterEqual(wallcolors._contrast(p["accent"], p["ink"]), 6.0)
            self.assertGreaterEqual(wallcolors._contrast(p["text"], p["raised"]), 12.0)

    def test_a_grey_picture_keeps_cyan(self):
        p = wallcolors.to_hex(wallcolors.pick([(128, 128, 128)] * 100))
        self.assertAlmostEqual(hue_of(p["accent"]), 187, delta=3)


class AutoThemeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {"XDG_CONFIG_HOME": self.tmp.name, "HOME": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def test_colours_are_kept_per_wallpaper(self):
        shell.write_config({"theme": "auto", "wallpaper": "tesseract"}, self.env)
        self.assertTrue(shell.update_wallpaper_colors(self.env))
        self.assertFalse(shell.update_wallpaper_colors(self.env))
        look = shell.look(self.env)
        self.assertEqual(set(look["colors"]), set(shell.COLOR_KEYS))
        palette = shell.palette(look["theme"], look["colors"])
        self.assertEqual(palette["id"], "auto")
        self.assertEqual(palette["accent"], look["colors"]["accent"])

    def test_other_themes_ignore_them(self):
        shell.write_config({"theme": "ember", "colors": {"accent": "#FFFFFF"}}, self.env)
        self.assertFalse(shell.update_wallpaper_colors(self.env))
        self.assertNotIn("colors", shell.look(self.env))
        self.assertEqual(shell.palette("ember")["id"], "ember")

    def test_auto_without_colours_is_cyan(self):
        self.assertEqual(shell.palette("auto")["accent"], shell.palette("cyan")["accent"])
        self.assertEqual(shell.theme_ids()[0], "auto")


if __name__ == "__main__":
    unittest.main()
