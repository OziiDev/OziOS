import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import presence  # noqa: E402


class Presence(unittest.TestCase):
    def test_says_only_ozios(self):
        act = presence.activity(1000, "0.4")
        text = json.dumps(act)
        # Never a program name: a client mod's name there could get the account banned.
        for name in ("Vesktop", "Discord", "vencord", "Firefox", "Terminal"):
            self.assertNotIn(name.lower(), text.lower())
        self.assertEqual(act["timestamps"]["start"], 1000)

    def test_frames(self):
        frame = presence.pack(1, {"a": 1})
        self.assertEqual(frame[:8], (1).to_bytes(4, "little") + (7).to_bytes(4, "little"))
        self.assertEqual(frame[8:], b'{"a":1}')


if __name__ == "__main__":
    unittest.main()
