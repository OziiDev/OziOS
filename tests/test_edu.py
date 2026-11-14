import os
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "edu", "apply-edu.sh")
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "bash is not available here")
class ApplyEdu(unittest.TestCase):
    """Run the real script with stand-ins for the programs that would change the desktop."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = os.path.join(self.tmp.name, "bin")
        self.log = os.path.join(self.tmp.name, "calls.log")
        os.mkdir(self.bin)
        for name in ("kwriteconfig6", "ozi"):
            path = os.path.join(self.bin, name)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write('#!/bin/sh\necho "%s $*" >> "%s"\n' % (name, self.log.replace("\\", "/")))
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args, live):
        marker = os.path.join(self.tmp.name, "archiso")
        if live:
            os.mkdir(marker)
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], OZIOS_LIVE_DIR=marker)
        done = subprocess.run([BASH, SCRIPT, *args], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        try:
            with open(self.log, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""

    def test_a_board_does_not_lock_or_sleep(self):
        calls = self.run_script(live=False)
        self.assertIn("kscreenlockerrc --group Daemon --key Autolock false", calls)
        self.assertIn("powerdevilrc --group AC --group SuspendAndShutdown --key AutoSuspendAction 0", calls)
        self.assertIn("kcminputrc --group Mouse --key cursorSize 36", calls)

    def test_the_board_layout_comes_last(self):
        calls = self.run_script(live=False).strip().split("\n")
        self.assertEqual(calls[-1], "ozi layout board")

    def test_the_live_session_is_turkish(self):
        calls = self.run_script(live=True)
        self.assertIn("kxkbrc --group Layout --key LayoutList tr", calls)
        self.assertIn("plasma-localerc --group Translations --key LANGUAGE tr", calls)

    def test_an_installed_system_keeps_the_language_chosen_in_the_installer(self):
        calls = self.run_script(live=False)
        self.assertNotIn("kxkbrc", calls)
        self.assertNotIn("plasma-localerc", calls)

    def test_undo_takes_the_settings_out_and_goes_back_to_the_default_layout(self):
        calls = self.run_script("--undo", live=False)
        self.assertIn("--key Autolock --delete", calls)
        self.assertIn("ozi layout default", calls)
        self.assertNotIn("Autolock false", calls)


if __name__ == "__main__":
    unittest.main()
