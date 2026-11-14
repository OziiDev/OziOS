import hashlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import cli, helper  # noqa: E402


class Names(unittest.TestCase):
    def test_accepts_real_package_names(self):
        for name in ("firefox", "lib32-mesa", "python-pyqt6", "gtk2+", "linux-ozios-headers", "ttf-jetbrains-mono.1"):
            self.assertEqual(helper.check_names([name]), [name])

    def test_rejects_anything_odd(self):
        for name in ("", "-Rdd", "--noconfirm", "a b", "a;b", "$(id)", "A", "x" * 101, "a\nb", "../x"):
            with self.assertRaises(helper.HelperError, msg=repr(name)):
                helper.check_names([name])

    def test_needs_at_least_one(self):
        with self.assertRaises(helper.HelperError):
            helper.check_names([])


class Plan(unittest.TestCase):
    def test_verbs(self):
        self.assertEqual(helper.plan(["install-repo", "vlc"])[0],
                         [["pacman", "-S", "--needed", "--noconfirm", "--", "vlc"]])
        self.assertEqual(helper.plan(["remove", "vlc", "mpv"])[0],
                         [["pacman", "-Rns", "--noconfirm", "--", "vlc", "mpv"]])
        self.assertEqual(helper.plan(["upgrade"])[0], [["pacman", "-Syu", "--noconfirm"]])
        self.assertEqual(helper.plan(["undo", "12"])[0], [["snapper", "-c", "root", "undochange", "12..0"]])

    def test_unknown_verbs_and_bad_arguments(self):
        for argv in ([], ["rm"], ["upgrade", "x"], ["undo", "1;2"], ["undo"], ["install-file", "/a.pkg.tar.zst"]):
            with self.assertRaises(helper.HelperError, msg=repr(argv)):
                helper.plan(argv)

    def test_snapshot_description_cannot_become_an_option(self):
        cmd = helper.plan(["snapshot", "--delete", "me\x00"])[0][0]
        self.assertEqual(cmd[:5], ["snapper", "-c", "root", "create", "-d"])
        self.assertFalse(cmd[5].startswith("-"))
        self.assertNotIn("\x00", cmd[5])


class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.staging = os.path.join(self.tmp.name, "staging")
        self.pkg = os.path.join(self.tmp.name, "demo-1-1-x86_64.pkg.tar.zst")
        self.data = b"package bytes" * 1000
        with open(self.pkg, "wb") as fh:
            fh.write(self.data)
        self.sha = hashlib.sha256(self.data).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def test_copies_when_the_digest_matches(self):
        copy = helper.stage_file(self.pkg, self.sha, self.staging)
        self.assertTrue(copy.startswith(self.staging))
        self.assertTrue(copy.endswith(".pkg.tar.zst"))
        with open(copy, "rb") as fh:
            self.assertEqual(fh.read(), self.data)

    def test_wrong_digest_leaves_nothing_behind(self):
        with self.assertRaises(helper.HelperError):
            helper.stage_file(self.pkg, "0" * 64, self.staging)
        self.assertEqual(os.listdir(self.staging), [])

    def test_rejects_bad_digest_and_names(self):
        for source, sha in ((self.pkg, "xyz"), ("relative.pkg.tar.zst", self.sha), (self.pkg + ".txt", self.sha),
                            (os.path.join(self.tmp.name, "missing.pkg.tar.zst"), self.sha)):
            with self.assertRaises(helper.HelperError, msg=source):
                helper.stage_file(source, sha, self.staging)

    def test_install_file_plan_uses_the_copy(self):
        commands, cleanup = helper.plan(["install-file", self.pkg, self.sha], staging=self.staging)
        self.assertEqual(commands[0][:4], ["pacman", "-U", "--noconfirm", "--"])
        self.assertEqual(commands[0][4], cleanup[0])
        self.assertNotEqual(commands[0][4], self.pkg)


class Main(unittest.TestCase):
    def run_main(self, argv, runner=None, euid=0):
        out = io.StringIO()
        code = helper.main(argv, out=out, runner=runner or (lambda cmd, o: 0), geteuid=lambda: euid)
        return code, [json.loads(line) for line in out.getvalue().splitlines()]

    def test_refuses_to_run_unprivileged(self):
        code, events = self.run_main(["upgrade"], euid=1000)
        self.assertEqual(code, 1)
        self.assertEqual(events[0]["event"], "error")

    def test_reports_start_and_done(self):
        code, events = self.run_main(["upgrade"])
        self.assertEqual((code, [e["event"] for e in events]), (0, ["start", "done"]))

    def test_stops_at_the_first_failure(self):
        code, events = self.run_main(["remove", "vlc"], runner=lambda cmd, o: 5)
        self.assertEqual((code, events[-1]), (5, {"event": "done", "status": 5}))

    def test_bad_input_is_an_error_event_not_a_crash(self):
        code, events = self.run_main(["remove", "-Rdd"])
        self.assertEqual(code, 2)
        self.assertEqual(events[-1]["event"], "error")


class Cleaning(unittest.TestCase):
    def test_the_fixed_commands(self):
        self.assertEqual(helper.plan(["clean-cache"])[0], [["paccache", "-rk2"], ["paccache", "-ruk0"]])
        self.assertEqual(helper.plan(["clean-journal"])[0], [["journalctl", "--vacuum-time=14d"]])
        self.assertEqual(helper.plan(["clean-orphans"])[0], [])

    def test_no_arguments_are_accepted(self):
        for verb in ("clean-cache", "clean-journal", "clean-orphans"):
            with self.assertRaises(helper.HelperError, msg=verb):
                helper.plan([verb, "--all"])

    def test_orphans_skip_the_protected_and_the_odd(self):
        names = helper.orphan_names(lambda cmd: (0, "libfoo\nlinux-headers\nlinux-ozios-zfs\nozios-edu\nbase-devel\n-Rdd\nbar+baz\n"))
        self.assertEqual(names, ["libfoo", "bar+baz"])

    def test_no_orphans_is_not_an_error(self):
        self.assertEqual(helper.orphan_names(lambda cmd: (1, "")), [])

    def run_main(self, orphans, runner):
        out = io.StringIO()
        code = helper.main(["clean-orphans"], out=out, runner=runner, geteuid=lambda: 0,
                           capture_output=lambda cmd: orphans)
        return code, [json.loads(line) for line in out.getvalue().splitlines()]

    def test_orphans_are_removed_by_name_in_one_command(self):
        commands = []
        code, events = self.run_main((0, "libfoo\nlibbar\n"), lambda cmd, o: commands.append(cmd) or 0)
        self.assertEqual(code, 0)
        self.assertEqual(commands, [["pacman", "-Rns", "--noconfirm", "--", "libfoo", "libbar"]])
        self.assertIn("removing: libfoo libbar", [e.get("line") for e in events])

    def test_nothing_to_remove_runs_nothing(self):
        commands = []
        code, events = self.run_main((1, ""), lambda cmd, o: commands.append(cmd) or 0)
        self.assertEqual((code, commands), (0, []))
        self.assertIn("no unneeded packages", [e.get("line") for e in events])


class FakeProc:
    def __init__(self, lines):
        self.stdout = iter(lines)

    def wait(self):
        return 0


class Client(unittest.TestCase):
    def test_snapshot_comes_first_and_output_is_relayed(self):
        calls, lines = [], []

        def runner(cmd, **kwargs):
            calls.append(cmd)
            return FakeProc([json.dumps({"event": "output", "line": "installing vlc"}) + "\n",
                             json.dumps({"event": "done", "status": 0}) + "\n"])

        status = cli.call_helper("install-repo", ["vlc"], out=lines.append, runner=runner)
        self.assertEqual(status, 0)
        self.assertEqual([c[2] for c in calls], ["snapshot", "install-repo"])
        self.assertEqual(calls[1][:2], ["pkexec", "/usr/lib/ozios/ozi-pkg-helper"])
        self.assertIn("installing vlc", lines)

    def test_no_snapshot_for_undo(self):
        calls = []
        cli.call_helper("undo", ["3"], out=lambda t: None,
                        runner=lambda cmd, **k: calls.append(cmd) or FakeProc([]))
        self.assertEqual(len(calls), 1)

    def test_missing_pkexec_is_a_clean_error(self):
        def runner(cmd, **kwargs):
            raise FileNotFoundError

        with self.assertRaises(cli.CliError):
            cli.call_helper("upgrade", [], out=print, runner=runner)


class SubIds(unittest.TestCase):
    class User:
        def __init__(self, name):
            self.pw_name = name

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.files = [os.path.join(self.dir.name, "subuid"), os.path.join(self.dir.name, "subgid")]

    def grant(self, uid, name="ozi"):
        return helper.grant_subids(uid, files=self.files, lookup=lambda _: self.User(name))

    def lines(self, index=0):
        with open(self.files[index], encoding="ascii") as fh:
            return fh.read().splitlines()

    def test_adds_a_range_to_both_files_once(self):
        self.assertTrue(self.grant("1000"))
        self.assertEqual(self.lines(0), ["ozi:100000:65536"])
        self.assertEqual(self.lines(1), ["ozi:100000:65536"])
        self.assertFalse(self.grant("1000"))
        self.assertEqual(self.lines(0), ["ozi:100000:65536"])

    def test_next_range_follows_the_existing_ones(self):
        for path in self.files:
            with open(path, "w", encoding="ascii") as fh:
                fh.write("other:100000:65536\n")
        self.grant("1001")
        self.assertEqual(self.lines(0)[-1], "ozi:165536:65536")

    def test_only_ordinary_accounts_through_pkexec(self):
        for uid in (None, "", "abc", "0", "999", "65534", "-1"):
            with self.assertRaises(helper.HelperError, msg=repr(uid)):
                self.grant(uid)
        with self.assertRaises(helper.HelperError):
            self.grant("1000", name="Bad Name")
        self.assertFalse(os.path.exists(self.files[0]))

    def test_the_verb_takes_no_arguments(self):
        self.assertEqual(helper.plan(["subids"]), ([], []))
        with self.assertRaises(helper.HelperError):
            helper.plan(["subids", "root"])


if __name__ == "__main__":
    unittest.main()
