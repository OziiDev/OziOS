import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import files  # noqa: E402


def touch(path, data=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = {"HOME": self.tmp, "XDG_DATA_HOME": os.path.join(self.tmp, ".local/share"),
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)


class Listing(Base):
    def test_folders_first_natural_order_hidden_files_hidden(self):
        for name in ("b10.txt", "b2.txt", "a.png", ".secret"):
            touch(self.p("d", name))
        os.mkdir(self.p("d", "zfolder"))
        names = [e["name"] for e in files.listdir(self.p("d"))["entries"]]
        self.assertEqual(names, ["zfolder", "a.png", "b2.txt", "b10.txt"])
        self.assertIn(".secret", [e["name"] for e in files.listdir(self.p("d"), hidden=True)["entries"]])

    def test_kinds(self):
        touch(self.p("photo.jpg"))
        touch(self.p("notes"), b"hello\n")
        touch(self.p("blob"), b"\0\1\2")
        touch(self.p("pkg.tar.zst"))
        self.assertTrue(files.entry(self.p("photo.jpg"))["preview"])
        self.assertEqual(files.mime_of(self.p("notes")), "text/plain")
        self.assertEqual(files.mime_of(self.p("blob")), "application/octet-stream")
        self.assertTrue(files.entry(self.p("pkg.tar.zst"))["archive"])
        self.assertEqual(files.icon_for("image/png")[:2], ["image-png", "image-x-generic"])

    def test_sizes(self):
        self.assertEqual(files.human_size(512), "512 B")
        self.assertEqual(files.human_size(1536), "1.5 KB")
        self.assertEqual(files.human_size(1024 ** 3), "1 GB")

    def test_search(self):
        touch(self.p("a", "b", "Report 2026.pdf"))
        touch(self.p(".hidden", "report.txt"))
        found = [e["name"] for e in files.search(self.tmp, "report")]
        self.assertEqual(found, ["Report 2026.pdf"])


class Names(Base):
    def test_free_name(self):
        touch(self.p("a.txt"))
        touch(self.p("a (2).txt"))
        touch(self.p("pkg.tar.gz"))
        self.assertEqual(files.free_name(self.tmp, "a.txt"), "a (3).txt")
        self.assertEqual(files.free_name(self.tmp, "pkg.tar.gz"), "pkg (2).tar.gz")
        self.assertEqual(files.free_name(self.tmp, "new.txt"), "new.txt")

    def test_bad_names(self):
        for bad in ("", " ", "a/b", "..", "."):
            with self.assertRaises(ValueError):
                files.check_name(bad)

    def test_rename_and_make(self):
        touch(self.p("a.txt"))
        touch(self.p("b.txt"))
        with self.assertRaises(ValueError):
            files.rename(self.p("a.txt"), "b.txt")
        self.assertEqual(files.rename(self.p("a.txt"), "c.txt"), self.p("c.txt"))
        self.assertEqual(os.path.basename(files.make_folder(self.tmp, "New")), "New")
        self.assertEqual(os.path.basename(files.make_folder(self.tmp, "New")), "New (2)")


class Transfer(Base):
    def test_copy_keeps_both_and_reports(self):
        touch(self.p("src", "f.txt"), b"1" * 3000)
        touch(self.p("src", "sub", "g.txt"))
        os.mkdir(self.p("dst"))
        lines = []
        files.transfer([self.p("src")], self.p("dst"), log=lines.append)
        files.transfer([self.p("src")], self.p("dst"))
        self.assertTrue(os.path.isfile(self.p("dst", "src", "sub", "g.txt")))
        self.assertTrue(os.path.isdir(self.p("dst", "src (2)")))
        self.assertTrue(os.path.isdir(self.p("src")))
        self.assertTrue(lines[-1].startswith("progress 3001 3001"))

    def test_move(self):
        touch(self.p("a.txt"))
        os.mkdir(self.p("dst"))
        files.transfer([self.p("a.txt")], self.p("dst"), move=True)
        self.assertFalse(os.path.exists(self.p("a.txt")))
        self.assertTrue(os.path.exists(self.p("dst", "a.txt")))

    def test_not_into_itself(self):
        os.makedirs(self.p("a", "b"))
        with self.assertRaises(ValueError):
            files.transfer([self.p("a")], self.p("a", "b"))


class Trash(Base):
    def test_trash_restore_empty(self):
        touch(self.p("docs", "x.txt"), b"hi")
        files.trash([self.p("docs", "x.txt")], self.env)
        self.assertFalse(os.path.exists(self.p("docs", "x.txt")))
        listed = files.trash_list(self.env)["entries"]
        self.assertEqual([(e["name"], e["original"]) for e in listed], [("x.txt", self.p("docs", "x.txt"))])
        self.assertEqual(files.trash_count(self.env), 1)
        files.restore([listed[0]["trashName"]], self.env)
        self.assertTrue(os.path.exists(self.p("docs", "x.txt")))
        files.trash([self.p("docs", "x.txt")], self.env)
        files.empty_trash(environ=self.env)
        self.assertEqual(files.trash_count(self.env), 0)
        self.assertEqual(os.listdir(os.path.join(files.trash_dir(self.env), "info")), [])

    def test_same_name_twice(self):
        for _ in range(2):
            touch(self.p("x.txt"))
            files.trash([self.p("x.txt")], self.env)
        self.assertEqual(files.trash_count(self.env), 2)


@unittest.skipUnless(shutil.which("bsdtar"), "bsdtar is not installed")
class Archives(Base):
    def test_round_trip(self):
        touch(self.p("pack", "a.txt"), b"a")
        touch(self.p("pack", "b", "c.txt"), b"c")
        zip_path = files.compress([self.p("pack")])
        self.assertEqual(os.path.basename(zip_path), "pack.zip")
        shutil.rmtree(self.p("pack"))
        out = files.extract(zip_path)
        self.assertEqual(out, self.p("pack"))       # one folder inside: no folder in a folder
        self.assertTrue(os.path.isfile(self.p("pack", "b", "c.txt")))

    def test_stem(self):
        self.assertEqual(files.archive_stem("x.tar.gz"), "x")
        self.assertEqual(files.archive_stem("x.zip"), "x")


class Drives(unittest.TestCase):
    def test_removable_and_media_only(self):
        lsblk = {"blockdevices": [
            {"name": "sda", "rm": False, "hotplug": False, "type": "disk", "fstype": None, "children": [
                {"name": "sda1", "type": "part", "fstype": "vfat", "mountpoint": "/boot", "size": "1G"},
                {"name": "sda2", "type": "part", "fstype": "btrfs", "mountpoint": "/", "size": "200G"}]},
            {"name": "sdb", "rm": True, "hotplug": True, "type": "disk", "fstype": None, "children": [
                {"name": "sdb1", "type": "part", "fstype": "exfat", "label": "Ventoy",
                 "mountpoint": "/run/media/ozi/Ventoy", "size": "29G"},
                {"name": "sdb2", "type": "part", "fstype": "vfat", "label": "VTOYEFI", "mountpoint": None, "size": "32M"}]}]}
        got = files.parse_lsblk(json.dumps(lsblk))
        self.assertEqual([(d["name"], d["mounted"]) for d in got], [("Ventoy", True), ("VTOYEFI", False)])


class Opening(unittest.TestCase):
    def test_exec_line_gets_the_file(self):
        self.assertEqual(files.command_with_file("gwenview %U", "/a b.png"), ["gwenview", "file:///a%20b.png"])
        self.assertEqual(files.command_with_file("mpv --player-operation-mode=pseudo-gui -- %F", "/v.mp4"),
                         ["mpv", "--player-operation-mode=pseudo-gui", "--", "/v.mp4"])
        self.assertEqual(files.command_with_file("app %i %c", "/f"), ["app", "/f"])


if __name__ == "__main__":
    unittest.main()
