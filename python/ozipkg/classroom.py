"""Classroom helpers for the Education edition: class lists, picking a student,
making groups, and a sound for the end of a timer. No Qt.

A class is a named list of students kept in the user's state folder, with the
names already picked in the current round, so everybody gets a turn before
anybody is picked twice.
"""
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile

from . import paths
from .i18n import tr

MAX_NAMES = 200
MAX_NAME_LENGTH = 60
CLASS_NAME = re.compile(r"^[^\W_][\w .'-]{0,39}$")
SOUNDS = ("/usr/share/sounds/freedesktop/stereo/complete.oga", "/usr/share/sounds/freedesktop/stereo/bell.oga")


def class_dir():
    return paths.state_dir() / "classes"


def check_class_name(name):
    name = (name or "").strip()
    if not CLASS_NAME.match(name):
        raise ValueError(tr("A class name has letters, numbers, spaces and . - ' and is at most 40 characters."))
    return name


def parse_names(text):
    """The students in a text, one per line: trimmed, without blanks, comments or repeats, in order."""
    seen, names = set(), []
    for line in (text or "").splitlines():
        name = re.sub(r"\s+", " ", line).strip()
        if not name or name.startswith("#"):
            continue
        name = name[:MAX_NAME_LENGTH]
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names[:MAX_NAMES]


def _path(name):
    return class_dir() / (check_class_name(name) + ".json")


def list_classes():
    try:
        return sorted(p.stem for p in class_dir().glob("*.json") if CLASS_NAME.match(p.stem))
    except OSError:
        return []


def load(name):
    """{"name", "names", "picked"} for a class; empty lists if it does not exist."""
    name = check_class_name(name)
    try:
        with open(_path(name), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    names = parse_names("\n".join(n for n in data.get("names", []) if isinstance(n, str)))
    picked = [n for n in data.get("picked", []) if isinstance(n, str) and n in names]
    return {"name": name, "names": names, "picked": picked}


def _write(name, names, picked):
    path = _path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"names": names, "picked": picked}, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save(name, text):
    """Replace a class's students with the names in `text`. Names already picked stay picked."""
    name = check_class_name(name)
    old = load(name)
    names = parse_names(text)
    _write(name, names, [n for n in old["picked"] if n in names])
    return load(name)


def delete(name):
    try:
        os.remove(_path(name))
    except OSError:
        pass
    return {"classes": list_classes()}


def pick(name, rng=random):
    """The next student. A round ends when everybody has been picked once; the next pick starts a new one."""
    data = load(name)
    if not data["names"]:
        raise ValueError(tr("This class has no students yet."))
    remaining = [n for n in data["names"] if n not in data["picked"]]
    new_round = not remaining
    if new_round:
        remaining, data["picked"] = list(data["names"]), []
    chosen = rng.choice(remaining)
    data["picked"].append(chosen)
    _write(data["name"], data["names"], data["picked"])
    return {"student": chosen, "left": len(data["names"]) - len(data["picked"]), "new_round": new_round}


def reset_picks(name):
    data = load(name)
    _write(data["name"], data["names"], [])
    return load(name)


def make_groups(names, count=None, size=None, rng=random):
    """The names shuffled into groups whose sizes differ by at most one.

    Give either the number of groups or the size of a group.
    """
    names = list(names)
    if not names:
        raise ValueError(tr("This class has no students yet."))
    if count is None and size is None:
        raise ValueError(tr("Say how many groups or how big they should be."))
    if count is None:
        count = math.ceil(len(names) / max(1, int(size)))
    count = max(1, min(int(count), len(names)))
    rng.shuffle(names)
    groups = [[] for _ in range(count)]
    for i, student in enumerate(names):
        groups[i % count].append(student)
    return groups


def groups_for(name, count):
    return {"groups": make_groups(load(name)["names"], count=int(count))}


def ding(popen=subprocess.Popen, which=shutil.which, exists=os.path.exists):
    """Make a sound for the end of a timer, if the system has a way to. Returns True when one was started."""
    player = which("paplay") or which("pw-play")
    for sound in SOUNDS:
        if player and exists(sound):
            popen([player, sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    if which("notify-send"):
        popen(["notify-send", tr("Time is up")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False
