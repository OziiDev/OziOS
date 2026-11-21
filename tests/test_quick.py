"""`ozi quick`: the control centre's quick settings, against made-up system tools."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import quick  # noqa: E402

SINK = "@DEFAULT_AUDIO_SINK@"
NIGHT_AVAILABLE = tuple(quick.NIGHT + ["org.kde.KWin.NightLight.available"])
NIGHT_ENABLED = tuple(quick.NIGHT + ["org.kde.KWin.NightLight.enabled"])
INHIBITED = ("busctl", "--user", "get-property", "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
             "org.freedesktop.Notifications", "Inhibited")
RFKILL = ("rfkill", "--output", "TYPE,SOFT,HARD", "--noheadings")
RADIO = ("nmcli", "-t", "-f", "WIFI-HW,WIFI", "radio")
NETWORKS = ("nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "--rescan", "no")


class Tools:
    """The system's programs as the test says they answer; every call is kept."""

    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.calls = []

    def __call__(self, argv, timeout=5):
        self.calls.append(list(argv))
        return self.answers.get(tuple(argv), (127, ""))

    def made(self, first):
        """The calls that started with the given program."""
        return [call for call in self.calls if call[0] == first]


def laptop(changes=None):
    answers = {
        ("wpctl", "get-volume", SINK): (0, "Volume: 0.40\n"),
        RADIO: (0, "enabled:enabled\n"),
        NETWORKS: (0, "no:Cafe\nyes:Ev\\: 5G\n"),
        RFKILL: (0, "wlan unblocked unblocked\nbluetooth unblocked unblocked\n"),
        NIGHT_AVAILABLE: (0, "true\n"),
        NIGHT_ENABLED: (0, "false\n"),
        INHIBITED: (0, "b false\n"),
    }
    answers.update(changes or {})
    return Tools(answers)


class Reading(unittest.TestCase):
    def test_a_laptop(self):
        self.assertEqual(quick.state(laptop()), {"volume": 40, "muted": False, "wifi": True, "wifi_network": "Ev: 5G",
                                                 "bluetooth": True, "night": False, "dnd": False})

    def test_muted_sound(self):
        tools = laptop({("wpctl", "get-volume", SINK): (0, "Volume: 0.55 [MUTED]\n")})
        self.assertEqual(quick.volume(tools), (55, True))

    def test_what_the_machine_lacks_is_none(self):
        # A virtual machine: no Wi-Fi card, no Bluetooth, no sound server.
        tools = laptop({RADIO: (0, "missing:enabled\n"), RFKILL: (0, ""), ("wpctl", "get-volume", SINK): (1, "")})
        now = quick.state(tools)
        self.assertEqual((now["volume"], now["wifi"], now["wifi_network"], now["bluetooth"]), (None, None, "", None))
        self.assertNotIn(list(NETWORKS), tools.calls)           # no network list asked for without Wi-Fi

    def test_switched_off_and_blocked(self):
        tools = laptop({RADIO: (0, "enabled:disabled\n"),
                          RFKILL: (0, "bluetooth soft-blocked-is-not-a-word unblocked\nbluetooth blocked unblocked\n")})
        self.assertFalse(quick.wifi(tools))
        self.assertFalse(quick.bluetooth(tools))

    def test_night_light_where_kwin_cannot(self):
        self.assertIsNone(quick.night(laptop({NIGHT_AVAILABLE: (0, "false\n")})))
        self.assertTrue(quick.night(laptop({NIGHT_ENABLED: (0, "true\n")})))

    def test_do_not_disturb(self):
        self.assertTrue(quick.dnd(laptop({INHIBITED: (0, "b true\n")})))
        self.assertFalse(quick.dnd(Tools()))                    # no busctl, no session bus


class Setting(unittest.TestCase):
    def test_volume_in_per_cent_and_by_steps(self):
        tools = laptop()
        quick.set_volume("40", tools)
        quick.set_volume("+5", tools)
        quick.set_volume("-5%", tools)
        quick.set_volume("400", tools)
        self.assertEqual(tools.made("wpctl"), [
            ["wpctl", "set-volume", "-l", "1.50", SINK, "40%"], ["wpctl", "set-mute", SINK, "0"],
            ["wpctl", "set-volume", "-l", "1.50", SINK, "5%+"], ["wpctl", "set-mute", SINK, "0"],
            ["wpctl", "set-volume", "-l", "1.50", SINK, "5%-"],                  # quieter does not unmute
            ["wpctl", "set-volume", "-l", "1.50", SINK, "150%"], ["wpctl", "set-mute", SINK, "0"]])
        with self.assertRaises(ValueError):
            quick.set_volume("loud", tools)

    def test_mute(self):
        tools = laptop()
        for value in ("toggle", "on", "kapalı"):
            quick.set_mute(value, tools)
        self.assertEqual([call[-1] for call in tools.made("wpctl")], ["toggle", "1", "0"])

    def test_radios(self):
        tools = laptop()
        quick.set_wifi("off", tools)
        quick.set_bluetooth("on", tools)
        self.assertEqual(tools.made("nmcli"), [["nmcli", "radio", "wifi", "off"]])
        self.assertEqual(tools.made("rfkill"), [["rfkill", "unblock", "bluetooth"]])
        with self.assertRaises(ValueError):
            quick.set_wifi("maybe", tools)

    def test_night_light_on_stays_on_unless_it_has_a_schedule(self):
        mode = ("kreadconfig6", "--file", "kwinrc", "--group", "NightColor", "--key", "Mode")
        write = ["kwriteconfig6", "--notify", "--file", "kwinrc", "--group", "NightColor", "--key"]
        tools = laptop({mode: (0, "\n"), NIGHT_ENABLED: (0, "true\n")})
        quick.set_night("on", tools, wait=lambda s: None)
        self.assertEqual(tools.made("kwriteconfig6"), [write + ["Mode", "Constant"], write + ["Active", "true"]])

        tools = laptop({mode: (0, "Timings\n"), NIGHT_ENABLED: (0, "true\n")})
        quick.set_night("on", tools, wait=lambda s: None)
        self.assertEqual(tools.made("kwriteconfig6"), [write + ["Active", "true"]])

        tools = laptop()
        quick.set_night("off", tools, wait=lambda s: None)
        self.assertEqual(tools.made("kwriteconfig6"), [write + ["Active", "false"]])

    def test_do_not_disturb_holds_one_inhibitor(self):
        started = []
        tools = laptop({INHIBITED: (0, "b true\n")})
        quick.set_dnd("on", tools, starter=started.append, wait=lambda s: None)
        self.assertEqual(tools.made("pkill"), [["pkill", "-f", "kde-inhibit --notifications sleep infinity"]])
        self.assertEqual(started, [quick.DND])
        quick.set_dnd("off", laptop(), starter=started.append, wait=lambda s: None)
        self.assertEqual(len(started), 1)

    def test_a_change_that_does_not_arrive_is_waited_for_a_moment_only(self):
        waits = []
        quick.set_dnd("on", laptop(), starter=lambda argv: None, wait=waits.append)
        self.assertEqual(len(waits), 15)                         # 1.5 seconds, then the state as it is


class Command(unittest.TestCase):
    def test_json(self):
        printed = []
        self.assertEqual(quick.main(["--json"], out=printed.append, runner=laptop()), 0)
        self.assertEqual(json.loads(printed[0])["wifi_network"], "Ev: 5G")

    def test_set_then_show(self):
        printed = []
        tools = laptop()
        self.assertEqual(quick.main(["wifi", "off"], out=printed.append, runner=tools), 0)
        self.assertIn(["nmcli", "radio", "wifi", "off"], tools.calls)
        self.assertEqual(len(printed), 1)
        self.assertTrue(printed[0].startswith("Wi-Fi"))

    def test_everything(self):
        printed = []
        quick.main([], out=printed.append, runner=laptop({RFKILL: (0, "")}))
        text = "\n".join(printed)
        for word in ("Volume", "40%", "Wi-Fi", "on (Ev: 5G)", "Bluetooth", "none", "Night light", "Do not disturb"):
            self.assertIn(word, text)

    def test_a_wrong_value_is_said_and_changes_nothing(self):
        printed = []
        tools = laptop()
        self.assertEqual(quick.main(["night", "bright"], out=printed.append, runner=tools), 2)
        self.assertIn("bright", printed[0])
        self.assertEqual(tools.made("kwriteconfig6"), [])

    def test_ozi_hands_it_to_python(self):
        from ozipkg import tools
        self.assertIs(tools.COMMANDS["quick"], quick.main)


if __name__ == "__main__":
    unittest.main()
