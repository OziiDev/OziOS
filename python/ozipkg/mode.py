"""Yetkili and Kısıtlı: the two modes of the Education edition.

Kısıtlı (restricted) is how every board starts: what a class needs works, but
the terminal, settings, the store and admin rights do not, so students
cannot change the board. The teacher's password ("ogretmen" until it is
changed) turns on Yetkili (authorised) mode until the next restart or until
they lock it again.

Dondurma (freeze): when the teacher turns it on, the board's home folder goes
back to the saved state at every start, so whatever students changed or left
on the desktop is gone the next morning. The lesson's notes are kept.

The mode lives in /run (gone at every start, so a board always wakes up
restricted). The password's hash and the freeze settings are root's, in
/etc/ozios; the root helper (`ozi-mode-helper`, reached through pkexec without
a password prompt) checks the password itself. Other editions are always
authorised and none of this applies.
"""
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time

EDITION_FILE = "/usr/share/ozios/edition"
MODE_FILE = "/run/ozios/mode"
TRIES_FILE = "/run/ozios/mode-tries"
PASSWORD_FILE = "/etc/ozios/ogretmen.sifre"
FREEZE_FILE = "/etc/ozios/dondurma.json"
FREEZE_DIR = "/var/lib/ozios/dondurma"
DEFAULT_PASSWORD = "ogretmen"
HELPER = "/usr/lib/ozios/ozi-mode-helper"

AUTHORISED = "yetkili"
RESTRICTED = "kisitli"

# Programs a restricted board does not start (by file name), and the launcher
# entries that start them.
BLOCKED_PROGRAMS = frozenset((
    "ozi-terminal", "konsole", "xterm", "alacritty", "kitty", "foot", "gnome-terminal", "kgx", "xfce4-terminal",
    "ozi-store", "ozi-look", "systemsettings", "ozi-welcome", "calamares", "pamac-manager", "octopi", "gparted",
    "btrfs-assistant", "partitionmanager", "ozi", "pkexec", "sudo", "su",
))
BLOCKED_APPS = frozenset((
    "ozi-terminal", "org.kde.konsole", "ozi-store", "ozi-look", "systemsettings", "ozi-welcome",
    "calamares", "org.cachyos.hello", "btrfs-assistant", "gparted", "org.kde.partitionmanager",
))

# Kept when the home folder goes back to its frozen state: the lesson's work.
KEEP = ("Belgeler/Ders Notları", "Resimler/ozi-pen", ".cache")

# Admin actions a restricted board refuses (polkit ids, by prefix). Joining
# Wi-Fi, mounting a USB stick, sound and power stay allowed.
DENIED_ACTIONS = (
    "org.freedesktop.policykit.exec", "org.freedesktop.packagekit.", "org.freedesktop.systemd1.manage-",
    "org.freedesktop.accounts.", "org.freedesktop.timedate1.", "org.freedesktop.hostname1.",
    "org.freedesktop.locale1.", "org.freedesktop.udisks2.modify-device", "org.freedesktop.udisks2.open-device",
    "org.freedesktop.udisks2.encrypted-", "org.freedesktop.udisks2.loop-", "org.freedesktop.udisks2.rescan",
    "org.freedesktop.login1.set-", "org.freedesktop.NetworkManager.settings.modify.hostname",
    "org.freedesktop.Flatpak.", "com.ubuntu.pkexec.", "org.ozios.admin",
)


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def is_education(edition_file=EDITION_FILE):
    return _read(edition_file) == "edu"


def current(edition_file=EDITION_FILE, mode_file=MODE_FILE):
    """"yetkili" or "kisitli". Outside the Education edition always "yetkili"."""
    if not is_education(edition_file):
        return AUTHORISED
    return AUTHORISED if _read(mode_file) == AUTHORISED else RESTRICTED


def restricted(**paths):
    return current(**paths) == RESTRICTED


def program_allowed(argv, **paths):
    """May this command start now? Only the program's file name counts."""
    if not argv:
        return True
    name = os.path.basename(argv[0])
    if name in ("sh", "bash", "env") and len(argv) > 2:
        # A program started through a shell or env: look at what it runs.
        inner = argv[2].split() if name != "env" else argv[1:]
        name = os.path.basename(inner[0]) if inner else name
    return name not in BLOCKED_PROGRAMS or not restricted(**paths)


def app_allowed(app_id, exec_line="", terminal=False, **paths):
    if not restricted(**paths):
        return True
    if app_id in BLOCKED_APPS or terminal:
        return False
    first = exec_line.split()[0] if exec_line.split() else ""
    return os.path.basename(first) not in BLOCKED_PROGRAMS


# ---- the password ------------------------------------------------------------

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return "pbkdf2-sha256$200000$%s$%s" % (salt, digest)


def check_password(password, stored):
    try:
        kind, rounds, salt, digest = stored.split("$")
    except ValueError:
        return False
    if kind != "pbkdf2-sha256":
        return False
    mine = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
    return hmac.compare_digest(mine, digest)


def stored_password(password_file=PASSWORD_FILE):
    """The teacher password's hash; the default one when none was set yet."""
    return _read(password_file) or hash_password(DEFAULT_PASSWORD, salt="ozios-varsayilan")


def _write_private(path, text, mode=0o600):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".yeni"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


# ---- what the root helper does ----------------------------------------------

WAIT_AFTER = 5          # wrong passwords in a row before the helper makes them wait
WAIT_SECONDS = 30


def unlock(password, mode_file=MODE_FILE, tries_file=TRIES_FILE, password_file=PASSWORD_FILE, now=time.time):
    """Yetkili mode when the password is right. Raises ValueError with what to say."""
    try:
        tries = json.loads(_read(tries_file) or "{}")
    except ValueError:
        tries = {}
    count, last = tries.get("count", 0), tries.get("last", 0)
    if count >= WAIT_AFTER and now() - last < WAIT_SECONDS:
        raise ValueError("Çok fazla yanlış deneme. %d saniye sonra yeniden dene." % (WAIT_SECONDS - int(now() - last)))
    if not check_password(password, stored_password(password_file)):
        _write_private(tries_file, json.dumps({"count": count + 1, "last": now()}), 0o644)
        raise ValueError("Şifre yanlış.")
    _write_private(tries_file, json.dumps({"count": 0, "last": 0}), 0o644)
    _write_private(mode_file, AUTHORISED, 0o644)
    return AUTHORISED


def lock(mode_file=MODE_FILE):
    _write_private(mode_file, RESTRICTED, 0o644)
    return RESTRICTED


def set_password(new, mode_file=MODE_FILE, password_file=PASSWORD_FILE, edition_file=EDITION_FILE):
    if current(edition_file, mode_file) != AUTHORISED:
        raise ValueError("Önce yetkili moda geç.")
    if len(new) < 4:
        raise ValueError("Şifre en az 4 karakter olmalı.")
    _write_private(password_file, hash_password(new))
    return {}


# ---- freezing ------------------------------------------------------------------

def freeze_settings(freeze_file=FREEZE_FILE):
    try:
        data = json.loads(_read(freeze_file) or "{}")
    except ValueError:
        data = {}
    return {"enabled": bool(data.get("enabled")), "user": data.get("user", ""), "saved": data.get("saved", 0)}


def rsync_argv(source, target):
    """Make `target` the same as `source`, leaving the kept folders alone."""
    argv = ["rsync", "-aHAX", "--delete", "--one-file-system"]
    for keep in KEEP:
        argv += ["--exclude", "/" + keep]
    return argv + [source.rstrip("/") + "/", target.rstrip("/") + "/"]


def freeze_save(user, home, freeze_dir=FREEZE_DIR, freeze_file=FREEZE_FILE, run=subprocess.run, now=time.time):
    """Keep the home folder as it is now: the state it goes back to at every start."""
    snapshot = os.path.join(freeze_dir, user)
    os.makedirs(snapshot, mode=0o700, exist_ok=True)
    out = run(rsync_argv(home, snapshot), capture_output=True, text=True)
    if out.returncode != 0:
        raise ValueError("Kaydedilemedi: " + (out.stderr.strip() or "rsync"))
    settings = freeze_settings(freeze_file)
    settings.update(user=user, saved=now())
    _write_private(freeze_file, json.dumps(settings), 0o644)
    return settings


def freeze_enable(on, user, home, freeze_dir=FREEZE_DIR, freeze_file=FREEZE_FILE, run=subprocess.run):
    settings = freeze_settings(freeze_file)
    if on and not (settings["saved"] and settings["user"] == user and os.path.isdir(os.path.join(freeze_dir, user))):
        settings = freeze_save(user, home, freeze_dir, freeze_file, run)
    settings["enabled"] = bool(on)
    _write_private(freeze_file, json.dumps(settings), 0o644)
    return settings


def freeze_restore(freeze_dir=FREEZE_DIR, freeze_file=FREEZE_FILE, run=subprocess.run, home_of=None):
    """At start (before anyone logs in): the home folder back to its saved state."""
    settings = freeze_settings(freeze_file)
    if not settings["enabled"] or not settings["user"]:
        return False
    snapshot = os.path.join(freeze_dir, settings["user"])
    if not os.path.isdir(snapshot):
        return False
    if home_of is None:
        import pwd
        home_of = lambda u: pwd.getpwnam(u).pw_dir  # noqa: E731
    home = home_of(settings["user"])
    return run(rsync_argv(snapshot, home), capture_output=True, text=True).returncode == 0


# ---- for the apps (no root) ------------------------------------------------------

def helper(*args, password=None, run=subprocess.run):
    """Ask the root helper; the password goes on its standard input, never the command line."""
    out = run(["pkexec", HELPER, *args], input=(password or "") + "\n", capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        message = (out.stderr or out.stdout).strip().splitlines()
        raise ValueError(message[-1] if message else "İzin verilmedi")
    return json.loads(out.stdout or "{}")


def status():
    return {"education": is_education(), "mode": current(), "freeze": freeze_settings()}
