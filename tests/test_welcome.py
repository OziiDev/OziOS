import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

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
            welcome.launch("windows", popen=popen)
        self.assertIn("ozi-winsetup", str(caught.exception))

    def test_show_at_login_round_trip(self):
        self.assertTrue(welcome.show_at_login())
        welcome.set_show_at_login(False)
        self.assertFalse(welcome.show_at_login())
        welcome.set_show_at_login(True)
        self.assertTrue(welcome.show_at_login())

    def test_actions_are_commands_not_strings(self):
        for name, cmd in welcome.ACTIONS.items():
            self.assertIsInstance(cmd, list, name)

    def test_the_install_button_runs_the_live_images_own_launcher(self):
        self.assertEqual(welcome.ACTIONS["install"], ["/usr/local/bin/calamares-online.sh"])

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

    def test_version_comes_from_the_version_file(self):
        self.assertRegex(welcome.version(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
