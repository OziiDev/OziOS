import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "python"))

from ozipkg import cli, tools  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def ozi_commands():
    """The commands `ozi` lists in its own help text."""
    text = read("packages", "ozi-cli", "ozi")
    usage = text.split("usage: ozi <command>", 1)[1].split("EOF\n}", 1)[0]
    names = re.findall(r"^  ([a-z][a-z-]*)\b", usage, re.M)
    return set(names) | {"help"}


def pkg_commands():
    parser = cli.build_parser()
    for action in parser._actions:
        if getattr(action, "choices", None) and hasattr(action, "_name_parser_map"):
            return set(action.choices)
    return set()


class Ozi(unittest.TestCase):
    def test_the_help_text_lists_the_commands(self):
        commands = ozi_commands()
        self.assertGreater(len(commands), 12)
        for name in ("update", "doctor", "report", "clean", "play", "layout", "status"):
            self.assertIn(name, commands)

    def test_bash_knows_every_command(self):
        text = read("data", "completions", "ozi.bash")
        listed = set(re.search(r'local commands="([^"]*)"', text).group(1).split())
        self.assertEqual(listed, ozi_commands())

    def test_fish_knows_every_command(self):
        text = read("data", "completions", "ozi.fish")
        listed = set(re.search(r"set -l commands ([^\n]*)", text).group(1).split())
        self.assertEqual(listed, ozi_commands())

    def test_zsh_knows_every_command(self):
        text = read("data", "completions", "_ozi")
        listed = set(re.findall(r"^  '([a-z-]+):", text, re.M))
        self.assertEqual(listed, ozi_commands())

    def test_the_python_commands_are_all_handled_by_the_script(self):
        script = read("packages", "ozi-cli", "ozi")
        for name in tools.COMMANDS:
            self.assertIn(name, script.split("doctor | report | clean | play)")[0] + "doctor | report | clean | play)")
        self.assertIn("doctor | report | clean | play)", script)
        self.assertEqual(set(tools.COMMANDS), {"doctor", "report", "clean", "play"})


class OziPkg(unittest.TestCase):
    def test_every_command_is_completed(self):
        commands = pkg_commands()
        self.assertIn("review", commands)
        bash = set(re.search(r'local commands="([^"]*)"', read("data", "completions", "ozi-pkg.bash")).group(1).split())
        fish = set(re.search(r"set -l commands ([^\n]*)", read("data", "completions", "ozi-pkg.fish")).group(1).split())
        zsh = set(re.findall(r"^  '([a-z-]+):", read("data", "completions", "_ozi-pkg"), re.M))
        self.assertEqual(bash, commands)
        self.assertEqual(fish, commands)
        self.assertEqual(zsh, commands)

    def test_the_rights_flags_match_the_real_ones(self):
        flags = set(re.findall(r"--[a-z0-9-]+", read("data", "completions", "ozi-pkg.bash")))
        for name in cli.BOOL_FLAGS:
            self.assertIn("--" + name.replace("_", "-"), flags)
            self.assertIn("--no-" + name.replace("_", "-"), flags)


class Packaging(unittest.TestCase):
    def test_every_completion_is_installed(self):
        pkgbuild = read("packages", "ozios-settings", "PKGBUILD")
        for target in ("bash-completion/completions", "fish/vendor_completions.d", "zsh/site-functions"):
            self.assertIn(target, pkgbuild)
        names = os.listdir(os.path.join(ROOT, "data", "completions"))
        self.assertEqual(len(names), 6)
        for name in names:
            self.assertIn(name, pkgbuild)


if __name__ == "__main__":
    unittest.main()
