import datetime
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

from ozipkg import report  # noqa: E402
from test_doctor import Fake  # noqa: E402


class Redact(unittest.TestCase):
    def test_user_and_host_names_are_whole_words_only(self):
        text = "ozi logged in on osbox; ozios and ozi-pkg stay; /home/ozi/x"
        out = report.redact(text, user="ozi", host="osbox", home="/home/ozi")
        self.assertEqual(out, "<user> logged in on <host>; ozios and ozi-pkg stay; ~/x")

    def test_other_users_home_folders(self):
        self.assertEqual(report.redact("see /home/anna/file and /Users/Bob/x"), "see /home/<user>/file and /home/<user>/x")

    def test_addresses(self):
        text = "ip 192.168.1.20 lo 127.0.0.1 mac aa:bb:cc:dd:ee:ff v6 fe80::1ff:fe23:4567:890a and ::1"
        out = report.redact(text)
        self.assertEqual(out, "ip <ip> lo 127.0.0.1 mac <mac> v6 <ip6> and <ip6>")

    def test_times_and_versions_survive(self):
        text = "12:21:47 [2]: kernel 6.18.42-1 and python 3.14.6 build 2026.02.25"
        self.assertEqual(report.redact(text), text)

    def test_identifiers(self):
        text = "UUID=3a4b5c6d-1111-2222-3333-444455556666 Serial Number: ABC123 mail me@example.com"
        out = report.redact(text)
        self.assertEqual(out, "UUID=<uuid> Serial Number: <serial> mail <email>")

    def test_empty_names_do_nothing(self):
        self.assertEqual(report.redact("a b c", user="", host=""), "a b c")


class Collect(unittest.TestCase):
    def machine(self):
        return Fake(files={"/etc/os-release": 'NAME="OziOS"\nOZIOS_VERSION=0.1.1\nHOME_URL="x"\n', "/proc/cmdline": "quiet root=UUID=3a4b5c6d-1111-2222-3333-444455556666",
                           "/proc/cpuinfo": "model name\t: Intel(R) Core(TM) i5\nflags : vmx\n", "/proc/meminfo": "MemTotal: 8000000 kB\n"},
                    commands={("lspci", "-nn"): (0, "00:02.0 VGA compatible controller [0300]: Intel Corporation [8086:1616]\n"),
                              ("pacman", "-Q", "linux-ozios"): (0, "linux-ozios 7.1.6-1\n"),
                              ("journalctl", "-b", "-p", "3", "--no-pager", "-n", "80"): (0, "Nov 14 ozi sudo[1]: pam error for ozi\n")},
                    user="ozi")

    def test_sections_are_there(self):
        text = report.collect(self.machine(), now=datetime.datetime(2026, 11, 14, 9, 30, tzinfo=datetime.timezone.utc))
        for title in ("System", "Kernel", "Machine", "PCI devices", "Packages", "Failed services", "ozi doctor"):
            self.assertIn("== %s ==" % title, text)
        self.assertIn("OziOS report, 2026-11-14 09:30 UTC", text)
        self.assertIn("NAME=OziOS", text)
        self.assertNotIn("HOME_URL", text)                 # only the keys that help
        self.assertIn("linux-ozios 7.1.6-1", text)

    def test_missing_tools_are_said_so(self):
        text = report.collect(Fake())
        self.assertIn("(lspci is not available)", text)


class Main(unittest.TestCase):
    def test_writes_a_private_redacted_file(self):
        with tempfile.TemporaryDirectory() as home:
            lines = []
            probe = Collect().machine()
            code = report.main([], out=lines.append, probe=probe, home=home, host="osbox",
                               now=datetime.datetime(2026, 11, 14, 9, 30))
            self.assertEqual(code, 0)
            path = os.path.join(home, "ozios-report-20261114-0930.txt")
            self.assertTrue(os.path.isfile(path))
            self.assertIn(path, lines[0])
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotIn("3a4b5c6d", text)
            self.assertIn("<user>", text)
            self.assertNotIn("pam error for ozi", text)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_stdout_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as home:
            lines = []
            report.main(["--stdout"], out=lines.append, probe=Collect().machine(), home=home, host="osbox")
            self.assertIn("== System ==", lines[0])
            self.assertEqual(os.listdir(home), [])


if __name__ == "__main__":
    unittest.main()
