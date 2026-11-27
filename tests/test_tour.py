import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import tour  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


class Tour(unittest.TestCase):
    def test_every_scene_is_complete_and_her_pictures_exist(self):
        for s in tour.SCENES:
            self.assertTrue(s["title"] and s["text"], s)
            self.assertGreaterEqual(s["seconds"], 8)
            self.assertIn(s["look"], tour.LOOKS)
        for name in tour.LOOKS.values():
            self.assertTrue(os.path.exists(os.path.join(ROOT, "branding", "mascot", name)), name)

    def test_programs_shown_are_allowed_on_a_restricted_board(self):
        from ozipkg import mode
        for s in tour.SCENES:
            if s.get("open"):
                self.assertNotIn(os.path.basename(s["open"][0]), mode.BLOCKED_PROGRAMS, s["title"])

    def test_a_scene_closes_only_what_it_opened(self):
        windows = [{"id": 1}]
        sent = []

        def ipc(req):
            sent.append(req)
            if req.get("get") == "windows":
                return {"ok": list(windows)}
            if req.get("do") == "spawn":
                windows.append({"id": 2})
            return {"ok": None}
        t = tour.Tour(ipc=ipc)
        t.enter(2)                      # opens a program
        self.assertIn({"do": "spawn", "command": tour.SCENES[2]["open"]}, sent)
        self.assertEqual(t.leave()["closed"], 1)
        self.assertIn({"do": "close", "id": 2}, sent)
        self.assertNotIn({"do": "close", "id": 1}, sent)

    def test_the_keyboard_scene_shows_and_hides_the_keyboard(self):
        sent = []
        t = tour.Tour(ipc=lambda req: sent.append(req) or {"ok": []})
        i = next(i for i, s in enumerate(tour.SCENES) if s.get("keyboard"))
        t.enter(i)
        t.leave()
        self.assertIn({"do": "key", "key": "keyboard-show"}, sent)
        self.assertIn({"do": "key", "key": "keyboard-hide"}, sent)


if __name__ == "__main__":
    unittest.main()
