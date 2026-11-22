#!/usr/bin/env python3
"""Watch an oziwm session from outside it: every few seconds write its frame
statistics and a screenshot into a folder. Used while a session runs on
another console (tools/ozi-dev-session).

    tools/watch-session.py OUT_DIR [SECONDS]

Waits for a new oziwm socket to appear, follows it until it goes away.
"""
import glob
import json
import os
import socket
import sys
import time

out = sys.argv[1]
every = float(sys.argv[2]) if len(sys.argv) > 2 else 15
os.makedirs(out, exist_ok=True)
runtime = os.environ.get("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())


def ask(path, request):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(2)
        s.connect(path)
        s.sendall((json.dumps(request) + "\n").encode())
        return json.loads(s.recv(65536))


seen = set(glob.glob(os.path.join(runtime, "oziwm-*.sock")))
while True:
    new = [p for p in set(glob.glob(os.path.join(runtime, "oziwm-*.sock"))) - seen if os.path.exists(p)]
    if new:
        sock = new[0]
        break
    time.sleep(1)
print("connected", sock, flush=True)
n = 0
while os.path.exists(sock):
    line = time.strftime("%H:%M:%S ")
    try:
        stats = ask(sock, {"get": "stats"}).get("ok")
        windows = ask(sock, {"get": "windows"}).get("ok") or []
        ask(sock, {"do": "screenshot", "path": os.path.join(out, "shot-%03d.png" % n)})
        line += json.dumps(stats) + " windows=%d" % len(windows)
        n += 1
    except (OSError, ValueError) as err:
        line += "error " + repr(err)
    with open(os.path.join(out, "stats.log"), "a") as f:
        f.write(line + "\n")
    time.sleep(every)
print("session ended", flush=True)
