import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import gaming  # noqa: E402
from test_doctor import Fake  # noqa: E402

AMD = "01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 23 [1002:73ff]\n"
INTEL = "00:02.0 VGA compatible controller [0300]: Intel Corporation UHD Graphics [8086:9bc4]\n"
NVIDIA = "01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA104 [10de:2484]\n"


def machine(lspci, installed=()):
    return Fake(commands={("lspci", "-nn"): (0, lspci), ("pacman", "-Qq"): (0, "\n".join(installed))})


class Plan(unittest.TestCase):
    def test_amd_gets_the_amd_drivers_in_both_widths(self):
        result = gaming.plan(machine(AMD))
        for name in ("steam", "gamemode", "lib32-gamemode", "mangohud", "vulkan-radeon", "lib32-vulkan-radeon", "lib32-mesa"):
            self.assertIn(name, result["missing"])
        self.assertNotIn("lib32-vulkan-intel", result["wanted"])

    def test_intel_gets_the_intel_drivers(self):
        wanted = gaming.plan(machine(INTEL))["wanted"]
        self.assertIn("lib32-vulkan-intel", wanted)
        self.assertNotIn("lib32-vulkan-radeon", wanted)

    def test_two_cards_get_both_sets_once(self):
        wanted = gaming.plan(machine(INTEL + AMD))["wanted"]
        self.assertIn("lib32-vulkan-intel", wanted)
        self.assertIn("lib32-vulkan-radeon", wanted)
        self.assertEqual(len(wanted), len(set(wanted)))

    def test_nvidia_waits_for_its_driver(self):
        result = gaming.plan(machine(NVIDIA))
        self.assertNotIn("lib32-nvidia-utils", result["wanted"])
        self.assertTrue(any("chwd" in note for note in result["notes"]))

    def test_nvidia_with_its_driver_gets_the_32_bit_libraries(self):
        result = gaming.plan(machine(NVIDIA, installed=["nvidia-utils"]))
        self.assertIn("lib32-nvidia-utils", result["missing"])
        self.assertEqual(result["notes"], [])

    def test_what_is_installed_is_not_listed_again(self):
        result = gaming.plan(machine(AMD, installed=["steam", "mesa", "gamemode"]))
        for name in ("steam", "mesa", "gamemode"):
            self.assertNotIn(name, result["missing"])
            self.assertIn(name, result["wanted"])

    def test_without_lspci_only_the_programs_are_listed(self):
        result = gaming.plan(Fake(commands={("pacman", "-Qq"): (0, "")}))
        self.assertEqual(result["wanted"], list(gaming.BASE))
        self.assertTrue(result["notes"])


class Command(unittest.TestCase):
    def run_main(self, argv, probe):
        lines, calls = [], []

        def caller(verb, names, out=print, **kw):
            calls.append((verb, list(names)))
            return 0

        code = gaming.main(argv, out=lines.append, probe=probe, caller=caller)
        return code, "\n".join(lines), calls

    def test_nothing_is_installed_without_yes(self):
        code, text, calls = self.run_main([], machine(AMD))
        self.assertEqual((code, calls), (0, []))
        self.assertIn("steam", text)
        self.assertIn("ozi gaming --yes", text)

    def test_yes_hands_the_missing_names_to_the_helper(self):
        code, _, calls = self.run_main(["--yes"], machine(AMD, installed=["steam"]))
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], "install-repo")
        self.assertNotIn("steam", calls[0][1])
        self.assertIn("lib32-vulkan-radeon", calls[0][1])

    def test_a_failing_install_is_reported(self):
        code = gaming.main(["--yes"], out=lambda t: None, probe=machine(AMD), caller=lambda *a, **k: 1)
        self.assertEqual(code, 1)

    def test_a_complete_machine_says_so(self):
        everything = list(gaming.BASE) + list(gaming.DRIVERS["intel"])
        code, text, calls = self.run_main(["--yes"], machine(INTEL, installed=everything))
        self.assertEqual((code, calls), (0, []))
        self.assertIn("installed", text)


if __name__ == "__main__":
    unittest.main()
