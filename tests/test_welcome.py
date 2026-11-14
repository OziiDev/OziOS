import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import welcome  # noqa: E402


class Welcome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.old
        self.tmp.cleanup()

    def test_only_known_actions_start(self):
        started = []
        welcome.launch("store", popen=lambda cmd, **k: started.append(cmd))
        self.assertEqual(started, [["ozi-store"]])
        for bad in ("rm -rf /", "", "STORE", "../x"):
            with self.assertRaises(ValueError):
                welcome.launch(bad, popen=lambda cmd, **k: started.append(cmd))
        self.assertEqual(len(started), 1)

    def test_missing_program_is_a_readable_error(self):
        def popen(cmd, **kwargs):
            raise FileNotFoundError

        with self.assertRaises(ValueError) as caught:
            welcome.launch("store", popen=popen)
        self.assertIn("ozi-store", str(caught.exception))

    def test_a_program_that_stops_at_once_says_why(self):
        class Quick:
            def __init__(self, code):
                self.code = code

            def poll(self):
                return self.code

        def popen(cmd, stderr=None, **kwargs):
            stderr.write(b"first line\nozi-store: no display\n")
            return Quick(1)

        with self.assertRaises(ValueError) as caught:
            welcome.launch("store", popen=popen, wait=0)
        self.assertIn("no display", str(caught.exception))
        self.assertEqual(welcome.launch("store", popen=lambda cmd, **k: Quick(0), wait=0), {"started": "store"})
        self.assertEqual(welcome.launch("store", popen=lambda cmd, **k: Quick(None), wait=0), {"started": "store"})

    def test_the_windows_button_explains_a_live_session_and_missing_virtualization(self):
        started = []
        popen = lambda cmd, **k: started.append(cmd)
        with self.assertRaises(ValueError) as caught:
            welcome.launch("windows", popen=popen, live=True, kvm_path=__file__)
        self.assertIn("live session", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            welcome.launch("windows", popen=popen, live=False, kvm_path=__file__ + ".missing")
        self.assertIn("virtualization", str(caught.exception))
        self.assertEqual(started, [])
        welcome.launch("windows", popen=popen, live=False, kvm_path=__file__)
        self.assertEqual(started, [["ozi-winsetup", "--gui"]])

    def test_show_at_login_round_trip(self):
        self.assertTrue(welcome.show_at_login())
        welcome.set_show_at_login(False)
        self.assertFalse(welcome.show_at_login())
        welcome.set_show_at_login(True)
        self.assertTrue(welcome.show_at_login())

    def test_actions_are_commands_not_strings(self):
        for name, cmd in welcome.ACTIONS.items():
            self.assertIsInstance(cmd, list, name)

    def test_the_install_button_runs_our_wrapper_around_the_live_launcher(self):
        self.assertEqual(welcome.ACTIONS["install"], ["/usr/lib/ozios/start-installer"])

    def test_live_means_a_live_medium_with_an_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "installer.sh")
            with open(script, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\n")
            self.assertFalse(welcome.is_live(root=os.path.join(tmp, "nothing"), installer=script))
            if os.name == "posix":
                os.chmod(script, 0o755)
                self.assertTrue(welcome.is_live(root=tmp, installer=script))
            self.assertFalse(welcome.is_live(root=tmp, installer=os.path.join(tmp, "missing")))

    def test_the_education_edition_is_read_from_its_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "edition")
            self.assertEqual(welcome.edition(path=marker), "")
            with open(marker, "w", encoding="utf-8") as fh:
                fh.write("edu\n")
            self.assertEqual(welcome.edition(path=marker), "edu")

    def test_the_education_buttons_start_the_pen_the_whiteboard_and_eba(self):
        self.assertEqual(welcome.ACTIONS["pen"], ["ozi-pen"])
        self.assertEqual(welcome.ACTIONS["whiteboard"], ["xournalpp"])
        self.assertEqual(welcome.ACTIONS["eba"], ["xdg-open", "https://eba.gov.tr"])

    def test_version_comes_from_the_version_file(self):
        self.assertRegex(welcome.version(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
