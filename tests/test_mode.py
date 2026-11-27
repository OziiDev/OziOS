import json
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "python"))

from ozipkg import mode  # noqa: E402


class Modes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.edition = os.path.join(t, "edition")
        self.mode_file = os.path.join(t, "run", "mode")
        self.tries = os.path.join(t, "run", "tries")
        self.password = os.path.join(t, "etc", "ogretmen.sifre")
        with open(self.edition, "w") as f:
            f.write("edu\n")
        self.paths = dict(edition_file=self.edition, mode_file=self.mode_file)

    def tearDown(self):
        self.tmp.cleanup()

    def unlock(self, password, now=lambda: 1000.0):
        return mode.unlock(password, mode_file=self.mode_file, tries_file=self.tries,
                           password_file=self.password, now=now)

    def test_a_board_starts_restricted(self):
        self.assertEqual(mode.current(**self.paths), mode.RESTRICTED)
        self.assertFalse(mode.program_allowed(["ozi-terminal"], **self.paths))
        self.assertFalse(mode.program_allowed(["sh", "-c", "konsole -e htop"], **self.paths))
        self.assertTrue(mode.program_allowed(["firefox"], **self.paths))
        self.assertFalse(mode.app_allowed("ozi-store", "ozi-store", **self.paths))
        self.assertFalse(mode.app_allowed("htop", "htop", terminal=True, **self.paths))
        self.assertTrue(mode.app_allowed("ozi-pen", "ozi-pen", **self.paths))

    def test_other_editions_are_always_authorised(self):
        with open(self.edition, "w") as f:
            f.write("")
        self.assertEqual(mode.current(**self.paths), mode.AUTHORISED)
        self.assertTrue(mode.program_allowed(["ozi-terminal"], **self.paths))

    def test_the_default_teacher_password_unlocks(self):
        with self.assertRaises(ValueError):
            self.unlock("yanlis")
        self.assertEqual(self.unlock("ogretmen"), mode.AUTHORISED)
        self.assertEqual(mode.current(**self.paths), mode.AUTHORISED)
        self.assertTrue(mode.program_allowed(["ozi-terminal"], **self.paths))
        mode.lock(self.mode_file)
        self.assertEqual(mode.current(**self.paths), mode.RESTRICTED)

    def test_guessing_has_to_wait(self):
        for _ in range(mode.WAIT_AFTER):
            with self.assertRaises(ValueError):
                self.unlock("yanlis")
        with self.assertRaisesRegex(ValueError, "saniye"):
            self.unlock("ogretmen", now=lambda: 1010.0)
        self.assertEqual(self.unlock("ogretmen", now=lambda: 1000.0 + mode.WAIT_SECONDS + 1), mode.AUTHORISED)

    def test_a_new_password_needs_authorised_mode(self):
        with self.assertRaises(ValueError):
            mode.set_password("yeni1234", password_file=self.password, **self.paths)
        self.unlock("ogretmen")
        mode.set_password("yeni1234", password_file=self.password, **self.paths)
        self.assertEqual(os.stat(self.password).st_mode & 0o777, 0o600)
        mode.lock(self.mode_file)
        with self.assertRaises(ValueError):
            self.unlock("ogretmen")
        self.assertEqual(self.unlock("yeni1234", now=lambda: 1000.0 + 999), mode.AUTHORISED)

    def test_hashes_are_salted(self):
        a, b = mode.hash_password("x"), mode.hash_password("x")
        self.assertNotEqual(a, b)
        self.assertTrue(mode.check_password("x", a) and not mode.check_password("y", a))


class Freezing(unittest.TestCase):
    def test_restore_keeps_the_lesson_notes(self):
        argv = mode.rsync_argv("/var/lib/ozios/dondurma/ozi", "/home/ozi")
        self.assertIn("--delete", argv)
        self.assertIn("/Belgeler/Ders Notları", argv)
        self.assertEqual(argv[-2:], ["/var/lib/ozios/dondurma/ozi/", "/home/ozi/"])

    def test_turning_on_saves_first(self):
        with tempfile.TemporaryDirectory() as t:
            calls = []

            class R:
                returncode = 0
                stderr = ""

            def run(argv, **kw):
                calls.append(argv)
                return R()
            settings_file = os.path.join(t, "dondurma.json")
            s = mode.freeze_enable(True, "ozi", "/home/ozi", freeze_dir=t, freeze_file=settings_file, run=run)
            self.assertTrue(s["enabled"])
            self.assertEqual(calls[0][-1], os.path.join(t, "ozi") + "/")
            self.assertTrue(mode.freeze_restore(freeze_dir=t, freeze_file=settings_file, run=run,
                                                home_of=lambda u: "/home/" + u))
            self.assertEqual(calls[-1][-1], "/home/ozi/")
            mode.freeze_enable(False, "ozi", "/home/ozi", freeze_dir=t, freeze_file=settings_file, run=run)
            self.assertFalse(mode.freeze_restore(freeze_dir=t, freeze_file=settings_file, run=run))


class SameListsEverywhere(unittest.TestCase):
    def test_oziwm_and_polkit_use_the_same_lists(self):
        with open(os.path.join(ROOT, "oziwm", "src", "policy.rs")) as f:
            rust = set(re.findall(r'"([^"]+)"', f.read().split("const BLOCKED")[1].split("];")[0]))
        self.assertEqual(rust, set(mode.BLOCKED_PROGRAMS))
        with open(os.path.join(ROOT, "edu", "mode", "50-ozios-kisitli.rules")) as f:
            text = f.read()
        listed = json.loads("[" + text.split("var denied = [")[1].split("];")[0] + "]")
        self.assertEqual(listed, list(mode.DENIED_ACTIONS))


if __name__ == "__main__":
    unittest.main()
