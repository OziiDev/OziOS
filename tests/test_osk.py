import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from ozipkg import osk  # noqa: E402

TR_SAMPLE = """
xkb_symbols "x" {
	key <AE02>               {	[               2,      apostrophe,        sterling,     twosuperior ] };
	key <AD01>               {	[               q,               Q,              at,     Greek_OMEGA ] };
	key <AD08>               {
		type= "FOUR_LEVEL_SEMIALPHABETIC",
		symbols[1]= [        idotless,               I,       paragraph,      VoidSymbol ]
	};
	key <AC10>               {	[        scedilla,        Scedilla,           acute,      dead_acute ] };
	key <AC11>               {
		type= "FOUR_LEVEL_SEMIALPHABETIC",
		symbols[1]= [               i,       Iabovedot,      apostrophe,      dead_caron ]
	};
};
"""


class Keymap(unittest.TestCase):
    def test_typed_keys_keep_their_symbols(self):
        keys = osk.parse_keymap(TR_SAMPLE)
        self.assertEqual(keys["AD08"][:2], ["idotless", "I"])
        self.assertEqual(keys["AC11"][:2], ["i", "Iabovedot"])
        self.assertEqual(keys["AD01"][2], "at")

    def test_turkish_letters_and_symbols(self):
        rows, symbols = osk.build(osk.parse_keymap(TR_SAMPLE), osk.keysyms())
        letters = {k["label"]: k for row in rows for k in row}
        self.assertEqual(letters["ı"]["shift"], "I")
        self.assertEqual(letters["i"]["shift"], "İ")
        self.assertEqual(letters["ş"]["code"], 39)
        by_label = {k["label"]: k["keys"] for k in symbols}
        self.assertEqual(by_label["@"], [osk.ALTGR, 16])
        self.assertEqual(by_label["'"], [osk.SHIFT, 3])
        self.assertNotIn("¶", by_label)

    def test_dead_and_void_keys_type_nothing(self):
        table = osk.keysyms()
        self.assertEqual(osk.char_of("dead_acute", table), "")
        self.assertEqual(osk.char_of("VoidSymbol", table), "")
        self.assertEqual(osk.char_of("U20BA", table), "₺")


class Layout(unittest.TestCase):
    def test_sources(self):
        self.assertEqual(osk._parse_kxkbrc("[Layout]\nLayoutList=tr,us\nVariantList=f,\nUse=true\n"), ("tr", "f"))
        self.assertEqual(osk._parse_xorg('Option "XkbLayout" "de"\n'), ("de", ""))
        self.assertEqual(osk._parse_vconsole("KEYMAP=trq\n"), ("tr", ""))

    def test_environment_wins(self):
        self.assertEqual(osk.layout({"OZIWM_XKB_LAYOUT": "fr", "HOME": "/nonexistent"}), ("fr", ""))

    def test_touch_screen_from_udev(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(osk.touch_screen(d))
            with open(os.path.join(d, "c13:70"), "w") as f:
                f.write("E:ID_INPUT=1\nE:ID_INPUT_TOUCHSCREEN=1\n")
            self.assertTrue(osk.touch_screen(d))


if __name__ == "__main__":
    unittest.main()
