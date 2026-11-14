import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import classroom  # noqa: E402


class Names(unittest.TestCase):
    def test_lines_are_trimmed_and_deduplicated_in_order(self):
        text = "  Ayşe  Yılmaz \n\n# a comment\nMehmet\nayşe yılmaz\nZeynep\t Kaya\n"
        self.assertEqual(classroom.parse_names(text), ["Ayşe Yılmaz", "Mehmet", "Zeynep Kaya"])

    def test_limits(self):
        many = "\n".join("student %d" % n for n in range(500))
        self.assertEqual(len(classroom.parse_names(many)), classroom.MAX_NAMES)
        self.assertEqual(len(classroom.parse_names("x" * 500)[0]), classroom.MAX_NAME_LENGTH)

    def test_empty(self):
        self.assertEqual(classroom.parse_names(""), [])
        self.assertEqual(classroom.parse_names(None), [])

    def test_class_names_cannot_escape_the_folder(self):
        for bad in ("", "../x", "a/b", "a\\b", "x" * 41, "_hidden", ".dot"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                classroom.check_class_name(bad)
        for good in ("5-A", "Fen Bilgisi 7B", "9. sınıf", "Ali's"):
            self.assertEqual(classroom.check_class_name(good), good)


class Classes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = self.tmp.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("XDG_STATE_HOME", None)
        else:
            os.environ["XDG_STATE_HOME"] = self.old
        self.tmp.cleanup()

    def test_save_load_list_delete(self):
        self.assertEqual(classroom.list_classes(), [])
        data = classroom.save("5-A", "Ali\nVeli\nAli\nSelin")
        self.assertEqual(data["names"], ["Ali", "Veli", "Selin"])
        self.assertEqual(classroom.list_classes(), ["5-A"])
        self.assertEqual(classroom.load("5-A")["names"], ["Ali", "Veli", "Selin"])
        classroom.delete("5-A")
        self.assertEqual(classroom.list_classes(), [])
        self.assertEqual(classroom.load("5-A")["names"], [])

    def test_a_round_gives_everybody_one_turn(self):
        classroom.save("c", "A\nB\nC\nD")
        rng = random.Random(7)
        round_one = [classroom.pick("c", rng)["student"] for _ in range(4)]
        self.assertEqual(sorted(round_one), ["A", "B", "C", "D"])
        again = classroom.pick("c", rng)
        self.assertTrue(again["new_round"])
        self.assertEqual(again["left"], 3)

    def test_left_counts_down(self):
        classroom.save("c", "A\nB\nC")
        rng = random.Random(1)
        self.assertEqual([classroom.pick("c", rng)["left"] for _ in range(3)], [2, 1, 0])

    def test_picks_survive_a_restart(self):
        classroom.save("c", "A\nB")
        first = classroom.pick("c", random.Random(3))["student"]
        self.assertEqual(classroom.load("c")["picked"], [first])

    def test_editing_the_list_keeps_picks_that_are_still_there(self):
        classroom.save("c", "A\nB\nC")
        classroom.pick("c", random.Random(2))
        picked = classroom.load("c")["picked"][0]
        data = classroom.save("c", "A\nB\nC\nD\n")
        self.assertEqual(data["picked"], [picked])
        dropped = classroom.save("c", picked.replace(picked, "Z"))
        self.assertEqual(dropped["picked"], [])

    def test_reset(self):
        classroom.save("c", "A\nB")
        classroom.pick("c")
        self.assertEqual(classroom.reset_picks("c")["picked"], [])

    def test_an_empty_class_cannot_be_picked_from(self):
        classroom.save("c", "")
        with self.assertRaises(ValueError):
            classroom.pick("c")

    def test_damaged_files_are_treated_as_empty(self):
        classroom.save("c", "A")
        with open(classroom._path("c"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(classroom.load("c"), {"name": "c", "names": [], "picked": []})


class Groups(unittest.TestCase):
    names = ["s%d" % n for n in range(11)]

    def test_by_count_sizes_differ_by_at_most_one(self):
        groups = classroom.make_groups(self.names, count=4, rng=random.Random(1))
        self.assertEqual(sorted(len(g) for g in groups), [2, 3, 3, 3])
        self.assertEqual(sorted(n for g in groups for n in g), sorted(self.names))

    def test_by_size(self):
        groups = classroom.make_groups(self.names, size=4, rng=random.Random(1))
        self.assertEqual(len(groups), 3)
        self.assertTrue(all(len(g) <= 4 for g in groups))

    def test_more_groups_than_students(self):
        self.assertEqual(len(classroom.make_groups(["a", "b"], count=9)), 2)

    def test_the_input_list_is_not_changed(self):
        before = list(self.names)
        classroom.make_groups(self.names, count=3)
        self.assertEqual(self.names, before)

    def test_errors(self):
        with self.assertRaises(ValueError):
            classroom.make_groups([], count=2)
        with self.assertRaises(ValueError):
            classroom.make_groups(["a"])


class Ding(unittest.TestCase):
    def test_a_sound_when_there_is_a_player_and_a_file(self):
        started = []
        ok = classroom.ding(popen=lambda cmd, **k: started.append(cmd), which=lambda n: "/usr/bin/" + n if n == "paplay" else None,
                            exists=lambda p: p.endswith("complete.oga"))
        self.assertTrue(ok)
        self.assertEqual(started[0][0], "/usr/bin/paplay")

    def test_a_notification_otherwise(self):
        started = []
        ok = classroom.ding(popen=lambda cmd, **k: started.append(cmd), which=lambda n: "/usr/bin/" + n if n == "notify-send" else None,
                            exists=lambda p: False)
        self.assertTrue(ok)
        self.assertEqual(started[0][0], "notify-send")

    def test_silence_is_not_an_error(self):
        self.assertFalse(classroom.ding(popen=lambda *a, **k: None, which=lambda n: None, exists=lambda p: False))


if __name__ == "__main__":
    unittest.main()
