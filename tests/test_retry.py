"""retry-download: the installer's base system download goes on after the network drops."""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import retry  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
COMMAND = ["/etc/calamares/scripts/pacstrap_calamares", "-c", "/tmp/calamares-root", "base"]

# What pacstrap printed when the network dropped during an installation in the test VM.
DROPPED = [
    "pacstrap: :: Retrieving packages...\n",
    "error: failed retrieving file 'systemd-262.2-1-x86_64.pkg.tar.zst' from mirror.neuf.no : "
    "Could not resolve host: mirror.neuf.no\n",
    "warning: fatal error from mirror.neuf.no, skipping for the remainder of this transaction\n",
    "warning: failed to retrieve some files\n",
    "error: failed to commit transaction (failed to retrieve some files)\n",
    "Errors occurred, no packages were upgraded.\n",
    "==> ERROR: Failed to install packages to new root\n",
]
NO_LISTS = [
    "error: failed retrieving file 'core.db' from geo.mirror.pkgbuild.com : Could not resolve host\n",
    "error: failed to synchronize all databases (download library error)\n",
]
CONFLICT = [
    "error: failed retrieving file 'mesa.pkg.tar.zst' from a.mirror : Connection reset by peer\n",
    "error: failed to commit transaction (conflicting files)\n",
    "intel-ucode: /boot/intel-ucode.img exists in filesystem\n",
]
DONE = [":: Retrieving packages...\n", ":: Processing package changes...\n", "installing base...\n"]


class Process:
    def __init__(self, lines, status):
        self.stdout = iter(lines)
        self.status = status

    def wait(self):
        return self.status


class Runs:
    """Stands in for subprocess.Popen: each run answers with the next (lines, status)."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        if not self.answers:
            raise AssertionError("ran more often than the test expected")
        lines, status = self.answers.pop(0)
        if status is None:
            raise FileNotFoundError(2, "No such file or directory")
        return Process(lines, status)


class Clock:
    def __init__(self):
        self.slept = []

    def __call__(self, seconds):
        self.slept.append(seconds)


def run(runs, online=lambda: True, tries=retry.TRIES):
    out, clock = io.StringIO(), Clock()
    status = retry.main(list(COMMAND), out=out, popen=runs, sleep=clock, is_online=online, tries=tries)
    return status, out.getvalue(), clock.slept


class Failures(unittest.TestCase):
    def test_a_dropped_network_is_a_network_failure(self):
        self.assertTrue(retry.network_failure(DROPPED))
        self.assertTrue(retry.network_failure(NO_LISTS))
        self.assertTrue(retry.network_failure(["error: mesa.pkg.tar.zst: invalid or corrupted package (checksum)\n"]))

    def test_a_conflict_is_not_even_after_a_mirror_failed(self):
        self.assertFalse(retry.network_failure(CONFLICT))
        self.assertFalse(retry.network_failure(["error: failed to prepare transaction (could not satisfy dependencies)\n"]))
        self.assertFalse(retry.network_failure(["error: mesa: signature from \"x\" is invalid\n",
                                                "error: mesa.pkg.tar.zst: invalid or corrupted package (PGP signature)\n"]))

    def test_online_is_any_mirror_answering(self):
        asked = []

        class Connection:
            def close(self):
                pass

        def connect(address, timeout):
            asked.append(address)
            if address[0] != "cachyos.org":
                raise OSError("Network is unreachable")
            return Connection()
        self.assertTrue(retry.online(hosts=["mirror.neuf.no"], connect=connect))
        self.assertEqual(asked, [("mirror.neuf.no", 443), ("archlinux.org", 443), ("cachyos.org", 443)])

        def nothing(address, timeout):
            raise TimeoutError("timed out")
        self.assertFalse(retry.online(hosts=[], connect=nothing))

    def test_the_first_mirrors_of_the_list_are_asked_first(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "mirrorlist")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("## Arch Linux mirrorlist\n#Server = https://old.example/$repo/os/$arch\n"
                         "Server = https://mirror.neuf.no/archlinux/$repo/os/$arch\n"
                         "Server = http://ftp.psnc.pl:8080/linux/archlinux/$repo/os/$arch\n"
                         "Server = https://mirror.neuf.no/other/$repo\n"
                         "Server = https://third.example/$repo/os/$arch\n")
            self.assertEqual(retry.mirror_hosts(path), ["mirror.neuf.no", "ftp.psnc.pl"])
            self.assertEqual(retry.mirror_hosts(os.path.join(folder, "missing")), [])


class Retry(unittest.TestCase):
    def test_a_good_run_happens_once_and_its_output_passes_through(self):
        runs = Runs((DONE, 0))
        status, out, slept = run(runs)
        self.assertEqual(status, 0)
        self.assertEqual(runs.commands, [COMMAND])
        self.assertEqual(out, "".join(DONE))
        self.assertEqual(slept, [])

    def test_a_dropped_download_is_tried_again_and_finishes(self):
        runs = Runs((DROPPED, 1), (NO_LISTS, 1), (DONE, 0))
        status, out, slept = run(runs)
        self.assertEqual(status, 0)
        self.assertEqual(runs.commands, [COMMAND] * 3)
        self.assertEqual(slept, [15, 30])
        self.assertIn("ozios: the download broke off; trying again in 15 s (try 2 of 4)\n", out)
        self.assertIn("ozios: the download finished on try 3\n", out)
        self.assertTrue(out.startswith("".join(DROPPED)))

    def test_it_waits_for_the_network_before_trying_again(self):
        answers = iter([False, False, False, True])
        status, out, slept = run(Runs((DROPPED, 1), (DONE, 0)), online=lambda: next(answers))
        self.assertEqual(status, 0)
        self.assertEqual(slept, [15, retry.STEP, retry.STEP, retry.STEP])
        self.assertEqual(out.count("waiting for the network to come back"), 1)

    def test_it_does_not_wait_for_ever(self):
        status, out, slept = run(Runs((DROPPED, 1), (DROPPED, 1)), online=lambda: False, tries=2)
        self.assertEqual(status, 1)
        self.assertEqual(slept[0], 15)
        self.assertEqual(sum(slept[1:]), retry.WAIT_FOR_NETWORK)

    def test_another_failure_comes_back_at_once(self):
        runs = Runs((CONFLICT, 1))
        status, out, slept = run(runs)
        self.assertEqual(status, 1)
        self.assertEqual(len(runs.commands), 1)
        self.assertEqual(slept, [])
        self.assertNotIn("ozios:", out)

    def test_it_gives_up_after_the_last_try_with_the_commands_status(self):
        runs = Runs(*[(DROPPED, 1)] * retry.TRIES)
        status, out, slept = run(runs)
        self.assertEqual(status, 1)
        self.assertEqual(len(runs.commands), retry.TRIES)
        self.assertEqual(slept, list(retry.PAUSES))
        self.assertNotIn("try 5", out)

    def test_a_missing_command_is_not_tried_again(self):
        runs = Runs(([], None))
        status, out, slept = run(runs)
        self.assertEqual(status, 127)
        self.assertEqual(len(runs.commands), 1)
        self.assertIn("could not run /etc/calamares/scripts/pacstrap_calamares", out)

    def test_without_a_command_it_says_how_to_use_it(self):
        out = io.StringIO()
        self.assertEqual(retry.main([], out=out), 2)
        self.assertIn("usage: retry-download", out.getvalue())

    def test_only_the_last_lines_are_kept(self):
        lines = ["line %d\n" % i for i in range(retry.KEEP * 3)]
        status, kept = retry.run_once(COMMAND, io.StringIO(), Runs((lines, 0)))
        self.assertEqual(status, 0)
        self.assertEqual(kept, lines[-retry.KEEP:])


class Script(unittest.TestCase):
    PATH = os.path.join(ROOT, "packages", "ozios-settings", "retry-download")

    def test_the_script_runs_the_command_itself_when_the_rules_are_missing(self):
        with open(self.PATH, encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("#!/usr/bin/python3 -I\n"))
        self.assertIn("from ozipkg import retry", text)
        self.assertIn("os.execvp(sys.argv[1], sys.argv[1:])", text)
        compile(text, self.PATH, "exec")

    def test_the_package_installs_it_where_the_installer_looks(self):
        with open(os.path.join(ROOT, "packages", "ozios-settings", "PKGBUILD"), encoding="utf-8") as fh:
            self.assertIn('"$here/retry-download"', fh.read())
        from ozipkg import installer
        self.assertEqual(installer.RETRY, "/usr/lib/ozios/retry-download")


if __name__ == "__main__":
    unittest.main()
