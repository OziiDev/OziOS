import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

from ozipkg import play  # noqa: E402
from test_doctor import Fake, LSPCI_NVIDIA_INTEL  # noqa: E402


def has(*names):
    return lambda name: ("/usr/bin/" + name) if name in names else None


class Plan(unittest.TestCase):
    def test_plain(self):
        plan = play.plan(["game", "-x"], which=has())
        self.assertEqual((plan.argv, plan.env, plan.notes), (["game", "-x"], {}, []))

    def test_gamemode_is_used_when_it_exists(self):
        self.assertEqual(play.plan(["game"], which=has("gamemoderun")).argv, ["gamemoderun", "game"])
        self.assertEqual(play.plan(["game"], gamemode=False, which=has("gamemoderun")).argv, ["game"])

    def test_mangohud_goes_inside_gamemode(self):
        plan = play.plan(["game"], mangohud=True, which=has("gamemoderun", "mangohud"))
        self.assertEqual(plan.argv, ["gamemoderun", "mangohud", "game"])

    def test_mangohud_missing_is_a_note_not_an_error(self):
        plan = play.plan(["game"], mangohud=True, which=has())
        self.assertEqual(plan.argv, ["game"])
        self.assertEqual(len(plan.notes), 1)

    def test_discrete_nvidia_on_a_laptop(self):
        plan = play.plan(["game"], gpu="discrete", vendors=["intel", "nvidia"], which=has())
        self.assertEqual(plan.env["__NV_PRIME_RENDER_OFFLOAD"], "1")
        self.assertEqual(plan.env["__GLX_VENDOR_LIBRARY_NAME"], "nvidia")

    def test_discrete_amd_uses_dri_prime(self):
        plan = play.plan(["game"], gpu="discrete", vendors=["intel", "amd"], which=has())
        self.assertEqual(plan.env, {"DRI_PRIME": "1"})

    def test_integrated(self):
        self.assertEqual(play.plan(["g"], gpu="integrated", vendors=["intel", "amd"], which=has()).env, {"DRI_PRIME": "0"})
        self.assertEqual(play.plan(["g"], gpu="integrated", vendors=["intel", "nvidia"], which=has()).env, {})

    def test_one_card_has_nothing_to_choose(self):
        plan = play.plan(["game"], gpu="discrete", vendors=["intel"], which=has())
        self.assertEqual(plan.env, {})
        self.assertEqual(len(plan.notes), 1)


class Main(unittest.TestCase):
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

    def run_main(self, argv, result=0, **kwargs):
        calls, modes = [], []
        code = play.main(argv, out=lambda text: calls.append(("out", text)), probe=kwargs.get("probe", Fake()),
                         run=lambda command, env: calls.append(("run", command, env)) or result,
                         set_mode=modes.append, which=has())
        return code, calls, modes

    def test_game_mode_goes_on_and_off_around_the_game(self):
        code, calls, modes = self.run_main(["--", "game", "--fast"], result=3)
        self.assertEqual(code, 3)
        self.assertEqual(modes, ["on", "off"])
        self.assertEqual(calls[0][1], ["game", "--fast"])

    def test_game_mode_already_on_is_left_on(self):
        os.makedirs(os.path.join(self.tmp.name, "ozios"))
        open(os.path.join(self.tmp.name, "ozios", "game-mode"), "w").close()
        _, _, modes = self.run_main(["--", "game"])
        self.assertEqual(modes, [])

    def test_no_mode_leaves_it_alone(self):
        _, _, modes = self.run_main(["--no-mode", "--", "game"])
        self.assertEqual(modes, [])

    def test_the_mode_is_turned_off_even_when_the_game_crashes(self):
        modes = []

        def boom(command, env):
            raise RuntimeError("crash")

        with self.assertRaises(RuntimeError):
            play.main(["--", "game"], out=print, probe=Fake(), run=boom, set_mode=modes.append, which=has())
        self.assertEqual(modes, ["on", "off"])

    def test_a_missing_program_is_reported(self):
        modes, lines = [], []

        def missing(command, env):
            raise FileNotFoundError

        code = play.main(["--", "nosuchgame"], out=lines.append, probe=Fake(), run=missing, set_mode=modes.append, which=has())
        self.assertEqual(code, 127)
        self.assertIn("nosuchgame", lines[0])
        self.assertEqual(modes, ["on", "off"])

    def test_the_gpu_choice_reaches_the_environment(self):
        probe = Fake(commands={("lspci", "-nn"): (0, LSPCI_NVIDIA_INTEL)})
        _, calls, _ = self.run_main(["--gpu", "discrete", "--", "game"], probe=probe)
        env = [c for c in calls if c[0] == "run"][0][2]
        self.assertEqual(env["__NV_PRIME_RENDER_OFFLOAD"], "1")

    def test_a_command_is_required(self):
        with self.assertRaises(SystemExit):
            play.main([], out=print, probe=Fake(), run=lambda *a: 0, set_mode=lambda s: None, which=has())


if __name__ == "__main__":
    unittest.main()
