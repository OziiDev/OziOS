import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

from ozipkg import clean  # noqa: E402
from test_doctor import Fake  # noqa: E402

PACCACHE = "==> finished: 23 candidates (disk space saved: 1.55 GiB)\n"


def write(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"x" * size)


class Parsing(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(clean.parse_size("1.5 GiB"), int(1.5 * 1024 ** 3))
        self.assertEqual(clean.parse_size("300 MiB"), 300 * 1024 ** 2)
        self.assertEqual(clean.parse_size("Archived and active journals take up 1.2G in the file system."), int(1.2 * 1024 ** 3))
        self.assertEqual(clean.parse_size("nothing here"), 0)

    def test_paccache_output(self):
        self.assertEqual(clean.paccache_saving(PACCACHE), int(1.55 * 1024 ** 3))
        self.assertEqual(clean.paccache_saving("==> no candidate packages found for pruning\n"), 0)


class Folders(unittest.TestCase):
    def test_dir_size_counts_files_and_ignores_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(os.path.join(tmp, "a", "one"), 100)
            write(os.path.join(tmp, "two"), 50)
            if hasattr(os, "symlink"):
                try:
                    os.symlink(os.path.join(tmp, "two"), os.path.join(tmp, "link"))
                except OSError:
                    pass
            self.assertEqual(clean.dir_size(tmp), 150)
            self.assertEqual(clean.dir_size(os.path.join(tmp, "missing")), 0)

    def test_only_the_listed_caches_are_emptied(self):
        with tempfile.TemporaryDirectory() as home:
            write(os.path.join(home, ".cache", "thumbnails", "large", "a.png"), 10)
            write(os.path.join(home, ".local", "share", "Trash", "files", "old.txt"), 10)
            write(os.path.join(home, "Documents", "keep.txt"), 10)
            write(os.path.join(home, ".cache", "mozilla", "keep"), 10)
            count = clean.clear_user_caches(home)
            self.assertEqual(count, 2)
            self.assertTrue(os.path.exists(os.path.join(home, "Documents", "keep.txt")))
            self.assertTrue(os.path.exists(os.path.join(home, ".cache", "mozilla", "keep")))
            self.assertEqual(os.listdir(os.path.join(home, ".cache", "thumbnails")), [])
            self.assertTrue(os.path.isdir(os.path.join(home, ".cache", "thumbnails")))


class Survey(unittest.TestCase):
    def probe(self):
        return Fake(programs=["paccache"], commands={
            ("paccache", "-dk2"): (0, PACCACHE), ("paccache", "-duk0"): (0, "==> finished: 2 candidates (disk space saved: 100.0 MiB)\n"),
            ("journalctl", "--disk-usage"): (0, "Archived and active journals take up 512.0M in the file system.\n"),
            ("pacman", "-Qdtq"): (0, "libfoo\nlibbar\n")})

    def test_what_could_be_freed(self):
        with tempfile.TemporaryDirectory() as home:
            write(os.path.join(home, ".cache", "thumbnails", "x"), 2048)
            items = {i["id"]: i for i in clean.survey(self.probe(), home)}
            self.assertEqual(items["cache"]["bytes"], int(1.55 * 1024 ** 3) + 100 * 1024 ** 2)
            self.assertEqual(items["journal"]["bytes"], 512 * 1024 ** 2)
            self.assertEqual(items["orphans"]["count"], 2)
            self.assertEqual(items["user"]["bytes"], 2048)

    def test_without_paccache_the_cache_line_says_why(self):
        probe = Fake(commands={("pacman", "-Qdtq"): (1, "")})
        with tempfile.TemporaryDirectory() as home:
            item = {i["id"]: i for i in clean.survey(probe, home)}["cache"]
            self.assertEqual(item["bytes"], 0)
            self.assertIn("pacman-contrib", item["detail"])


class Main(unittest.TestCase):
    def test_without_yes_nothing_is_changed(self):
        calls, lines = [], []
        with tempfile.TemporaryDirectory() as home:
            write(os.path.join(home, ".cache", "thumbnails", "x"), 10)
            code = clean.main([], out=lines.append, probe=Survey().probe(), home=home,
                              caller=lambda *a, **k: calls.append(a) or 0)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(os.path.join(home, ".cache", "thumbnails", "x")))
        self.assertEqual(calls, [])
        self.assertIn("--yes", lines[-1])

    def test_with_yes_the_helper_verbs_run_and_caches_are_emptied(self):
        calls, lines = [], []
        with tempfile.TemporaryDirectory() as home:
            write(os.path.join(home, ".cache", "thumbnails", "x"), 10)
            code = clean.main(["--yes"], out=lines.append, probe=Survey().probe(), home=home,
                              caller=lambda verb, args, **k: calls.append((verb, args, k)) or 0)
            self.assertEqual(code, 0)
            self.assertEqual(os.listdir(os.path.join(home, ".cache", "thumbnails")), [])
        self.assertEqual([c[0] for c in calls], ["clean-cache", "clean-journal", "clean-orphans"])
        self.assertTrue(all(c[2] == {"out": lines.append, "snapshot": False} or c[2]["snapshot"] is False for c in calls))

    def test_only_picks_items(self):
        calls = []
        with tempfile.TemporaryDirectory() as home:
            clean.main(["--yes", "--only", "journal"], out=lambda t: None, probe=Survey().probe(), home=home,
                       caller=lambda verb, args, **k: calls.append(verb) or 0)
        self.assertEqual(calls, ["clean-journal"])

    def test_a_failing_step_makes_the_exit_status_nonzero(self):
        with tempfile.TemporaryDirectory() as home:
            code = clean.main(["--yes", "--only", "cache"], out=lambda t: None, probe=Survey().probe(), home=home,
                              caller=lambda verb, args, **k: 1)
        self.assertEqual(code, 1)

    def test_unknown_items_are_refused(self):
        with self.assertRaises(SystemExit):
            clean.main(["--only", "everything"], out=lambda t: None, probe=Fake(), home="x", caller=lambda *a, **k: 0)


if __name__ == "__main__":
    unittest.main()
