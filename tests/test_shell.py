"""Mistakes in shell scripts that show up only on the machine they run on."""
import os
import shutil
import subprocess
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SKIP_DIRS = {".git", ".bridge", "out", ".kernel-pkgs", "__pycache__"}
BASH = shutil.which("bash")


def tracked_files():
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield os.path.join(folder, name)


def scripts():
    """(path, interpreter) for every file that starts with a shell shebang."""
    for path in tracked_files():
        try:
            with open(path, "rb") as fh:
                head = fh.read(60).split(b"\n", 1)[0]
        except OSError:
            continue
        if head.startswith(b"#!") and (b"bash" in head or head.rstrip().endswith(b"/sh")):
            yield path, "bash"


class Scripts(unittest.TestCase):
    def test_there_are_scripts(self):
        self.assertGreater(len(list(scripts())), 20)

    def test_no_script_has_windows_line_endings(self):
        """A carriage return after the shebang makes the interpreter 'not found'."""
        for path, _ in scripts():
            with open(path, "rb") as fh:
                self.assertNotIn(b"\r", fh.read(), path)

    @unittest.skipUnless(BASH, "bash is not available here")
    def test_every_script_parses(self):
        for path, _ in scripts():
            done = subprocess.run([BASH, "-n", path], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, "%s: %s" % (path, done.stderr))

    def test_scripts_that_are_installed_start_with_a_shebang(self):
        for name in ("first-login", "identity", "install-to-target", "start-installer", "patch-installer"):
            with open(os.path.join(ROOT, "packages", "ozios-settings", name), "rb") as fh:
                self.assertTrue(fh.read(2) == b"#!", name)


if __name__ == "__main__":
    unittest.main()
