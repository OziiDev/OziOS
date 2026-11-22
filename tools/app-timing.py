#!/usr/bin/env python3
"""Start programs inside a running oziwm and time how long each takes to show
its first window. Used to find slow starts.

    tools/app-timing.py konsole dolphin firefox ...

Talks to the newest oziwm socket; prints seconds per program and closes the
window afterwards.
"""
import glob
import json
import os
import socket
import sys
import time

runtime = os.environ.get("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())
sock = max(glob.glob(os.path.join(runtime, "oziwm-*.sock")), key=os.path.getmtime)


def ask(request):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(3)
        s.connect(sock)
        s.sendall((json.dumps(request) + "\n").encode())
        return json.loads(s.recv(1 << 20)).get("ok")


def windows():
    return {w["id"]: w for w in ask({"get": "windows"}) or []}


for program in sys.argv[1:]:
    before = set(windows())
    start = time.monotonic()
    ask({"do": "spawn", "command": program.split()})
    shown = None
    while time.monotonic() - start < 40:
        new = [w for i, w in windows().items() if i not in before]
        if new:
            shown = new[0]
            break
        time.sleep(0.05)
    took = time.monotonic() - start
    if shown:
        print("%-28s %5.1f s  %s / %s" % (program, took, shown["app_id"], shown["title"][:40]), flush=True)
        time.sleep(1.5)
        ask({"do": "close", "id": shown["id"]})
        time.sleep(1.0)
    else:
        print("%-28s no window in 40 s" % program, flush=True)
