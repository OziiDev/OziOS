import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class Version(unittest.TestCase):
    def test_version_is_semver(self):
        self.assertRegex(read("VERSION").strip(), r"^\d+\.\d+\.\d+$")

    def test_packages_match_version(self):
        for name in ("ozios-settings", "ozios-edu", "ozios-decoration"):
            pkgver = re.search(r"^pkgver=(\S+)$", read("packages", name, "PKGBUILD"), re.M).group(1)
            self.assertEqual(pkgver, read("VERSION").strip(), name)

    def test_the_window_frames_project_matches_version(self):
        cmake = read("desktop", "decoration", "CMakeLists.txt")
        self.assertIn("project(ozios-decoration VERSION %s " % read("VERSION").strip(), cmake)

    def test_the_bump_tool_sets_every_place(self):
        tool = read("tools", "bump-version.sh")
        for place in ("packages/ozios-settings/PKGBUILD", "packages/ozios-edu/PKGBUILD",
                      "packages/ozios-decoration/PKGBUILD", "desktop/decoration/CMakeLists.txt"):
            self.assertIn(place, tool)

    def test_changelog_has_the_current_version(self):
        self.assertIn("## " + read("VERSION").strip(), read("CHANGELOG.md"))


if __name__ == "__main__":
    unittest.main()
