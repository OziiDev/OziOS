"""Discord Rich Presence: friends on Discord see "Using OziOS" under your name.

Nothing about what you run is sent: no program names, no window titles. (A
name like a modded Discord client showing up there could get an account in
trouble, and it is nobody's business anyway.)

Talks to the Discord app on this computer (Discord, Vesktop, the Flatpak or
Snap) over its local socket; nothing goes anywhere else. Started with the
desktop by ozi-session-start; off with {"discord_presence": false} in
~/.config/ozios/desktop.json or `ozi-presence --off`.

    ozi-presence           run (waits for Discord, follows the windows)
    ozi-presence --once    set it once and exit (for trying it out)
    ozi-presence --off / --on
"""
import json
import os
import socket
import struct
import sys
import time
import uuid

from . import shell
from .i18n import tr

# The "OziOS" application on the Discord developer portal: its name is what
# Discord shows, its art assets are "ozios" (large) and the program icons.
CLIENT_ID = "1575365659410309210"
LINK = "https://github.com/OziiDev/OziOS"
MIN_GAP = 15.0          # Discord accepts about one change every 15 seconds

HANDSHAKE, FRAME, CLOSE = 0, 1, 2


def sockets(environ=os.environ):
    """Where a Discord app may listen, most likely first."""
    runtime = environ.get("XDG_RUNTIME_DIR") or "/run/user/%d" % os.getuid()
    bases = [runtime, os.path.join(runtime, "app", "com.discordapp.Discord"),
             os.path.join(runtime, "app", "dev.vencord.Vesktop"), os.path.join(runtime, "snap.discord"),
             environ.get("TMPDIR", "/tmp")]
    return [os.path.join(b, "discord-ipc-%d" % i) for b in bases for i in range(10)]


def pack(op, payload):
    data = json.dumps(payload, separators=(",", ":")).encode()
    return struct.pack("<II", op, len(data)) + data


def unpack(sock):
    head = _read(sock, 8)
    op, length = struct.unpack("<II", head)
    return op, json.loads(_read(sock, length) or b"{}")


def _read(sock, n):
    out = b""
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise ConnectionError("Discord closed the connection")
        out += chunk
    return out


def enabled(environ=os.environ):
    return shell.read_config(environ).get("discord_presence", True) is not False


def client_id(environ=os.environ):
    value = str(shell.read_config(environ).get("discord_client_id") or environ.get("OZI_DISCORD_CLIENT_ID") or CLIENT_ID)
    return value if value.isdigit() else ""


def activity(started, version):
    """What Discord shows: OziOS and since when; never which programs run."""
    return {
        "details": tr("Using OziOS"),
        "state": tr("Its own Linux desktop"),
        "timestamps": {"start": int(started)},
        "assets": {"large_image": "ozios", "large_text": tr("OziOS: its own desktop, from scratch")},
        "buttons": [{"label": tr("See OziOS"), "url": LINK}],
    }


class Discord:
    def __init__(self, cid, environ=os.environ):
        self.cid = cid
        self.environ = environ
        self.sock = None

    def connect(self):
        for path in sockets(self.environ):
            if not os.path.exists(path):
                continue
            s = socket.socket(socket.AF_UNIX)
            s.settimeout(5)
            try:
                s.connect(path)
                s.sendall(pack(HANDSHAKE, {"v": 1, "client_id": self.cid}))
                op, data = unpack(s)
            except OSError:
                s.close()
                continue
            if op == FRAME and data.get("evt") == "READY":
                self.sock = s
                return True
            s.close()
        return False

    def set(self, act):
        if self.sock is None:
            return False
        message = {"cmd": "SET_ACTIVITY", "args": {"pid": os.getpid(), "activity": act}, "nonce": str(uuid.uuid4())}
        try:
            self.sock.sendall(pack(FRAME, message))
            op, data = unpack(self.sock)
        except (OSError, ValueError, struct.error):
            self.close()
            return False
        if data.get("evt") == "ERROR":
            print("ozi-presence: Discord said:", data.get("data"), file=sys.stderr)
        return op == FRAME

    def close(self):
        if self.sock is not None:
            try:
                self.sock.sendall(pack(CLOSE, {}))
            except OSError:
                pass
            self.sock.close()
            self.sock = None


def run(once=False):
    if not enabled():
        return 0
    started = time.time()
    version = shell_version()
    cid = client_id()
    if not cid:
        print("ozi-presence: no Discord application id yet", file=sys.stderr)
        return 0
    discord = Discord(cid)
    shown, last_sent, last_try = None, 0.0, 0.0
    while True:
        if not enabled():
            discord.close()
            return 0
        now = time.time()
        if discord.sock is None and now - last_try > 20:
            last_try = now
            if discord.connect():
                shown = None
        if discord.sock is not None:
            act = activity(started, version)
            if act != shown and now - last_sent >= MIN_GAP:
                if discord.set(act):
                    shown, last_sent = act, now
        if once:
            discord.close()
            return 0 if shown else 1
        time.sleep(10)


def shell_version():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VERSION_ID="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def main(argv=()):
    if "--off" in argv or "--on" in argv:
        shell.write_config({"discord_presence": "--on" in argv})
        return 0
    return run(once="--once" in argv)
