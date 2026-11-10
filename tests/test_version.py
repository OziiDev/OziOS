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

    def test_package_matches_version(self):
        pkgver = re.search(r"^pkgver=(\S+)$", read("packages", "ozios-settings", "PKGBUILD"), re.M).group(1)
        self.assertEqual(pkgver, read("VERSION").strip())

    def test_changelog_has_the_current_version(self):
        self.assertIn("## " + read("VERSION").strip(), read("CHANGELOG.md"))


if __name__ == "__main__":
    unittest.main()
