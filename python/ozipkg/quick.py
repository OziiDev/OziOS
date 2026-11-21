"""`ozi quick`: the quick settings of the control centre in the bar. Sound, Wi-Fi,
Bluetooth, night light and do not disturb are read and set with the system's own
tools, so the panel, a terminal and Plasma's own settings all see the same state.

    volume       wpctl (PipeWire), the default output
    wifi         nmcli (NetworkManager); left out without a Wi-Fi device
    bluetooth    rfkill; left out without a Bluetooth device
    night        KWin's night light: kwinrc [NightColor], announced so KWin rereads it
    dnd          do not disturb: a kde-inhibit that holds Plasma's notifications back
                 until it is turned off again, or the session ends

A setting the machine does not have is null in `ozi quick --json`, and the control
centre leaves its tile out.
"""
import json
import re
import subprocess
import time

from .i18n import tr

SINK = "@DEFAULT_AUDIO_SINK@"
LOUDEST = 150                      # per cent; wpctl's limit, past 100 is amplified
DND = ["kde-inhibit", "--notifications", "sleep", "infinity"]
NIGHT = ["qdbus6", "org.kde.KWin", "/org/kde/KWin/NightLight"]
NAMES = ("volume", "mute", "wifi", "bluetooth", "night", "dnd")


def run(argv, timeout=5):
    """(exit status, standard output); (127, "") when the program is not there."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, ""
    except (OSError, subprocess.SubprocessError):
        return 126, ""
    return done.returncode, done.stdout


def start(argv):
    """Start a program that outlives this one (do not disturb)."""
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


# --- reading -------------------------------------------------------------------------------------

def volume(runner=run):
    """(per cent, muted) of the default output, or (None, None) without one."""
    code, out = runner(["wpctl", "get-volume", SINK])
    match = re.search(r"Volume:\s*([0-9.]+)", out) if code == 0 else None
    if not match:
        return None, None
    return int(round(float(match.group(1)) * 100)), "[MUTED]" in out


def wifi(runner=run):
    """True or False, or None without a Wi-Fi device."""
    code, out = runner(["nmcli", "-t", "-f", "WIFI-HW,WIFI", "radio"])
    hardware, _, software = out.strip().partition(":")
    if code != 0 or hardware == "missing" or not software:
        return None
    return hardware == "enabled" and software == "enabled"


def wifi_network(runner=run):
    """The name of the Wi-Fi network in use, or ""."""
    code, out = runner(["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "--rescan", "no"])
    for line in out.splitlines() if code == 0 else ():
        active, _, name = line.partition(":")
        if active == "yes" and name:
            return name.replace("\\:", ":")
    return ""


def bluetooth(runner=run):
    """True when every Bluetooth device may send, None without one."""
    code, out = runner(["rfkill", "--output", "TYPE,SOFT,HARD", "--noheadings"])
    rows = [line.split() for line in out.splitlines() if code == 0 and line.split()[:1] == ["bluetooth"]]
    if not rows:
        return None
    return all(row[1:3] == ["unblocked", "unblocked"] for row in rows)


def night(runner=run):
    """Whether KWin's night light is on; None where KWin cannot do it."""
    code, out = runner(NIGHT + ["org.kde.KWin.NightLight.available"])
    if code != 0 or out.strip() != "true":
        return None
    code, out = runner(NIGHT + ["org.kde.KWin.NightLight.enabled"])
    return code == 0 and out.strip() == "true"


def dnd(runner=run):
    """Whether Plasma holds notifications back now, for us or for another program."""
    code, out = runner(["busctl", "--user", "get-property", "org.freedesktop.Notifications",
                        "/org/freedesktop/Notifications", "org.freedesktop.Notifications", "Inhibited"])
    return code == 0 and out.split() == ["b", "true"]


def state(runner=run):
    level, muted = volume(runner)
    on = wifi(runner)
    return {"volume": level, "muted": muted, "wifi": on, "wifi_network": wifi_network(runner) if on else "",
            "bluetooth": bluetooth(runner), "night": night(runner), "dnd": dnd(runner)}


# --- setting -------------------------------------------------------------------------------------

def switch(value):
    """'on' / 'off' (and their Turkish) as True / False."""
    text = str(value).strip().lower()
    if text in ("on", "1", "true", "yes", "açık", "aç"):
        return True
    if text in ("off", "0", "false", "no", "kapalı", "kapat"):
        return False
    raise ValueError(tr("Say on or off, not {value}", value=value))


def set_volume(value, runner=run):
    """'40' sets 40 per cent, '+5' and '-5' move by five; a louder sound is not muted."""
    text = str(value).strip().rstrip("%")
    match = re.fullmatch(r"([+-]?)(\d{1,3})", text)
    if not match:
        raise ValueError(tr("A volume is a number of per cent, like 40, +5 or -5"))
    sign, amount = match.group(1), int(match.group(2))
    if sign:
        target = "%d%%%s" % (amount, sign)
    else:
        target = "%d%%" % min(amount, LOUDEST)
    runner(["wpctl", "set-volume", "-l", "%.2f" % (LOUDEST / 100), SINK, target])
    if sign != "-" and (sign or amount > 0):
        runner(["wpctl", "set-mute", SINK, "0"])


def set_mute(value, runner=run):
    flag = "toggle" if str(value).strip().lower() == "toggle" else ("1" if switch(value) else "0")
    runner(["wpctl", "set-mute", SINK, flag])


def set_wifi(value, runner=run):
    runner(["nmcli", "radio", "wifi", "on" if switch(value) else "off"])


def set_bluetooth(value, runner=run):
    runner(["rfkill", "unblock" if switch(value) else "block", "bluetooth"])


def settle(check, wanted, wait=time.sleep, tries=15):
    """Give a change a moment to arrive (up to 1.5 s), so the state shown next is the new one."""
    for _ in range(tries):
        if check() == wanted:
            return True
        wait(0.1)
    return False


def set_night(value, runner=run, wait=time.sleep):
    """On means warm now: unless the night light has a schedule of its own, it is set
    to stay on. --notify makes KWin read the change at once."""
    on = switch(value)
    write = ["kwriteconfig6", "--notify", "--file", "kwinrc", "--group", "NightColor", "--key"]
    if on:
        code, mode = runner(["kreadconfig6", "--file", "kwinrc", "--group", "NightColor", "--key", "Mode"])
        if not mode.strip():
            runner(write + ["Mode", "Constant"])
    runner(write + ["Active", "true" if on else "false"])
    settle(lambda: night(runner), on, wait)


def set_dnd(value, runner=run, starter=start, wait=time.sleep):
    on = switch(value)
    runner(["pkill", "-f", " ".join(DND)])          # never two of them
    if on:
        starter(DND)
    settle(lambda: dnd(runner), on, wait)


SETTERS = {"volume": set_volume, "mute": set_mute, "wifi": set_wifi, "bluetooth": set_bluetooth,
           "night": set_night, "dnd": set_dnd}


def title(name):
    return {"volume": tr("Volume"), "mute": tr("Mute"), "wifi": tr("Wi-Fi"), "bluetooth": tr("Bluetooth"),
            "night": tr("Night light"), "dnd": tr("Do not disturb")}[name]


def shown(name, now):
    value = now.get(name)
    if name == "volume":
        return tr("none") if value is None else "%d%%%s" % (value, " (%s)" % tr("muted") if now.get("muted") else "")
    if value is None:
        return tr("none")
    text = tr("on") if value else tr("off")
    if name == "wifi" and now.get("wifi_network"):
        text += " (%s)" % now["wifi_network"]
    return text


def main(argv=None, out=print, runner=run, starter=start, wait=time.sleep):
    import argparse
    parser = argparse.ArgumentParser(
        prog="ozi quick", description=tr("Quick settings: sound, Wi-Fi, Bluetooth, night light and do not disturb."),
        epilog=tr("Settings: {names}.", names=", ".join(NAMES)))
    parser.add_argument("name", nargs="?", choices=NAMES, metavar="setting")
    parser.add_argument("value", nargs="?", help=tr("on, off, or for volume a per cent like 40, +5 or -5"))
    parser.add_argument("--json", action="store_true", help=tr("machine-readable output"))
    args = parser.parse_args(argv)

    if args.name and args.value is not None:
        try:
            if args.name == "dnd":
                set_dnd(args.value, runner=runner, starter=starter, wait=wait)
            elif args.name == "night":
                set_night(args.value, runner=runner, wait=wait)
            else:
                SETTERS[args.name](args.value, runner=runner)
        except ValueError as err:
            out(str(err))
            return 2
    now = state(runner)
    if args.json:
        out(json.dumps(now, ensure_ascii=False))
        return 0
    names = [args.name if args.name != "mute" else "volume"] if args.name else [n for n in NAMES if n != "mute"]
    for name in names:
        out("%-16s %s" % (title(name), shown(name, now)))
    return 0
