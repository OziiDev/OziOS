import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import safeupdate  # noqa: E402

MENU = """timeout: 5
/+OziOS
  //linux-ozios
  protocol: linux
  module_path: boot():/abc/linux-ozios/initramfs#1234
  path: boot():/abc/linux-ozios/vmlinuz#5678
  //Snapshots
     path: boot():/abc/limine_history/vmlinuz_sha256_9#1
"""


class Result:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class FakeSystem:
    """A root folder with one kernel, and snapper/pacman stand-ins that change it."""

    def __init__(self, root):
        self.root = root
        self.calls = []
        self.write("usr/lib/modules/7.1-ozios/pkgbase", "linux-ozios\n")
        os.makedirs(self.path("usr/lib/modules/7.1-ozios/kernel"))
        for name in ("boot/vmlinuz-linux-ozios", "boot/initramfs-linux-ozios.img",
                     "boot/abc/linux-ozios/vmlinuz", "boot/abc/linux-ozios/initramfs"):
            self.write(name, "old")
        self.write("boot/limine.conf", MENU)
        self.update_breaks = False

    def path(self, name):
        return os.path.join(self.root, name)

    def write(self, name, text):
        os.makedirs(os.path.dirname(self.path(name)), exist_ok=True)
        with open(self.path(name), "w") as f:
            f.write(text)

    def run(self, argv, **kw):
        self.calls.append(argv)
        if argv[:2] == ["snapper", "-c"] and "create" in argv:
            return Result(0, "41\n" if "pre" in argv else "42\n")
        if argv[:2] == ["snapper", "-c"] and "undochange" in argv:
            # Going back: the new kernel's folder goes, the old kernel's modules return.
            import shutil
            shutil.rmtree(self.path("usr/lib/modules/7.2-ozios"))
            os.rename(self.path("usr/lib/modules/7.2-ozios-broken"), self.path("usr/lib/modules/7.1-ozios"))
            return Result(0)
        if argv[:2] == ["snapper", "-c"]:
            return Result(0)
        return Result(0)

    def pacman(self, argv):
        self.calls.append(argv)
        self.write("boot/vmlinuz-linux-ozios", "new")
        self.write("boot/abc/linux-ozios/vmlinuz", "new")
        if self.update_breaks:
            # A kernel whose modules did not get installed.
            os.rename(self.path("usr/lib/modules/7.1-ozios"), self.path("usr/lib/modules/7.2-ozios-broken"))
            os.makedirs(self.path("usr/lib/modules/7.2-ozios"))
            self.write("usr/lib/modules/7.2-ozios/pkgbase", "linux-ozios\n")
        return 0


class SafeUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sys = FakeSystem(self.tmp.name)
        self.log = []
        self.patch = unittest.mock.patch.object(safeupdate.shutil, "which", lambda name: "/usr/bin/" + name)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def update(self):
        return safeupdate.update(run=self.sys.run, log=self.log.append, root=self.tmp.name, stream=self.sys.pacman)

    def test_menu_paths_lose_their_checksums_and_skip_snapshots(self):
        self.assertEqual(safeupdate.boot_paths(self.tmp.name), ["abc/linux-ozios/initramfs", "abc/linux-ozios/vmlinuz"])

    def test_a_good_update_is_kept(self):
        r = self.update()
        self.assertEqual(r, {"ok": True, "updated": True, "undone": False, "problems": []})
        self.assertFalse(any("undochange" in c for c in self.sys.calls))
        with open(self.sys.path("boot/vmlinuz-linux-ozios")) as f:
            self.assertEqual(f.read(), "new")

    def test_a_broken_update_is_undone_with_the_boot_files(self):
        self.sys.update_breaks = True
        r = self.update()
        self.assertTrue(r["undone"])
        self.assertIn("modülleri eksik", " ".join(r["problems"]))
        self.assertIn(["snapper", "-c", "root", "undochange", "41..42"], self.sys.calls)
        for name in ("boot/vmlinuz-linux-ozios", "boot/abc/linux-ozios/vmlinuz"):
            with open(self.sys.path(name)) as f:
                self.assertEqual(f.read(), "old", name)

    def test_a_menu_entry_without_its_file_is_a_problem(self):
        os.remove(self.sys.path("boot/abc/linux-ozios/initramfs"))
        problems = safeupdate.health(self.tmp.name, run=self.sys.run)
        self.assertTrue(any("abc/linux-ozios/initramfs" in p for p in problems))

    def test_restore_takes_away_kernels_the_update_added(self):
        safeupdate.save_boot(self.tmp.name)
        self.sys.write("boot/vmlinuz-linux-extra", "x")
        self.sys.write("boot/initramfs-linux-extra.img", "x")
        safeupdate.restore_boot(self.tmp.name)
        self.assertFalse(os.path.exists(self.sys.path("boot/vmlinuz-linux-extra")))
        self.assertTrue(os.path.exists(self.sys.path("boot/vmlinuz-linux-ozios")))


import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()
