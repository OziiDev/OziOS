"""Debian and Ubuntu packages in a box: rootless podman, one image per app.

Installing runs the package's own scripts, but inside a container that sees
only the package file (read-only). Starting an app uses a fresh container
that gets exactly the rights in its Permissions record. Nothing in a box can
change the host system.

Functions that only build command lines are separate from the ones that run
them, so the command lines can be checked without podman.
"""
import json
import os
import posixpath
import re
import shlex
import subprocess
from pathlib import Path

from . import paths, perms as permissions
from .i18n import tr

BASE_IMAGE = "docker.io/library/ubuntu:24.04"
IMAGE_PREFIX = "localhost/ozi/"
SAFE_FILESYSTEMS = {"btrfs", "xfs", "ext2/ext3", "ext4", "f2fs"}


class BoxError(Exception):
    pass


def storage_driver(directory=None):
    """overlay where the filesystem supports it, vfs otherwise (live sessions)."""
    directory = directory or os.path.expanduser("~")
    try:
        out = subprocess.run(["stat", "-f", "-c", "%T", directory], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    return "overlay" if out in SAFE_FILESYSTEMS else "vfs"


def has_subids(uid=None, files=("/etc/subuid", "/etc/subgid")):
    """True when this user can map more than one id in a rootless container.

    Without a range in /etc/subuid and /etc/subgid podman cannot unpack an
    image (its files belong to many different users). Root needs none, and
    systems without a POSIX user database are not asked.
    """
    if not hasattr(os, "getuid"):
        return True
    uid = os.getuid() if uid is None else uid
    if uid == 0:
        return True
    try:
        import pwd
        name = pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return True
    for path in files:
        try:
            with open(path, encoding="ascii", errors="replace") as fh:
                if not any(line.split(":")[0] in (name, str(uid)) for line in fh):
                    return False
        except FileNotFoundError:
            return False
        except OSError:
            return True
    return True


def podman(driver=None):
    return ["podman", "--storage-driver", driver or storage_driver()]


def image_name(app_id):
    return IMAGE_PREFIX + permissions.check_app_id(app_id).lower()


def app_id_for(package_name):
    """A stable id from a Debian package name."""
    clean = re.sub(r"[^a-z0-9.+-]", "-", package_name.lower()).strip("-")
    if not clean:
        raise BoxError("cannot make an id from %r" % package_name)
    return clean


def build_command(deb_path, app_id, base=BASE_IMAGE, driver=None):
    """The podman command that installs a .deb into a new image's layer.

    The container gets the package file read-only and the network (apt needs
    it for dependencies) and nothing else: no home, no devices, no sockets.
    """
    script = ("set -e; export DEBIAN_FRONTEND=noninteractive; apt-get update -qq; "
              "apt-get install -y --no-install-recommends /in/package.deb; apt-get clean; "
              "rm -rf /var/lib/apt/lists/*")
    return podman(driver) + [
        "run", "--name", "ozi-build-" + app_id, "--security-opt", "no-new-privileges",
        "--cap-drop", "all", "--cap-add", "CHOWN,DAC_OVERRIDE,FOWNER,SETUID,SETGID,KILL,FSETID,SETFCAP,MKNOD,SYS_CHROOT,AUDIT_WRITE",
        "-v", "%s:/in/package.deb:ro" % deb_path, base, "sh", "-c", script]


def run_command(app_id, perms, argv, env=None, driver=None, exists=os.path.exists, uid=None, gid=None):
    """The podman command that starts an app from its image with `perms`."""
    env = env if env is not None else os.environ
    uid = os.getuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    run = permissions.runtime_dir()
    home = "/home/box"
    cmd = podman(driver) + [
        "run", "--rm", "--replace", "--name", "ozi-" + app_id, "--userns", "keep-id", "--user", "%d:%d" % (uid, gid),
        "--security-opt", "no-new-privileges", "--cap-drop", "all", "--pids-limit", "4096",
        "--hostname", "ozios", "--workdir", home, "-e", "HOME=" + home, "-e", "XDG_RUNTIME_DIR=" + run,
        "-v", "%s:%s" % (permissions.private_home(app_id), home), "--tmpfs", "/tmp"]
    cmd += ["--network", "pasta" if perms.network else "none"]
    if perms.nested_sandbox:
        cmd += ["--security-opt", "seccomp=unconfined", "--cap-add", "SYS_ADMIN"]
    wayland = env.get("WAYLAND_DISPLAY")
    if wayland and exists(posixpath.join(run, wayland)):
        sock = posixpath.join(run, wayland)
        cmd += ["-v", "%s:%s" % (sock, sock), "-e", "WAYLAND_DISPLAY=" + wayland]
    if perms.x11 and env.get("DISPLAY"):
        cmd += ["-v", "/tmp/.X11-unix:/tmp/.X11-unix", "-e", "DISPLAY=" + env["DISPLAY"]]
        xauth = env.get("XAUTHORITY")
        if xauth and exists(xauth):
            cmd += ["-v", "%s:%s:ro" % (xauth, xauth), "-e", "XAUTHORITY=" + xauth]
    if perms.gpu and exists("/dev/dri"):
        cmd += ["--device", "/dev/dri"]
    if perms.sound:
        for sock in ("pipewire-0", "pulse/native"):
            path = posixpath.join(run, sock)
            if exists(path):
                cmd += ["-v", "%s:%s" % (path, path)]
    if perms.camera:
        for n in range(8):
            node = "/dev/video%d" % n
            if exists(node):
                cmd += ["--device", node]
    if perms.devices and exists("/dev/bus/usb"):
        cmd += ["--device", "/dev/bus/usb"]
    if perms.files == "home":
        cmd += ["-v", "%s:%s" % (os.path.expanduser("~"), os.path.expanduser("~"))]
    elif perms.files == "chosen":
        for folder in perms.folders:
            cmd += ["-v", "%s:%s" % (folder, folder)]
    for name in ("LANG", "LC_ALL", "XCURSOR_THEME", "XCURSOR_SIZE", "QT_QPA_PLATFORM", "XDG_SESSION_TYPE"):
        if env.get(name):
            cmd += ["-e", "%s=%s" % (name, env[name])]
    return cmd + [image_name(app_id)] + list(argv)


def desktop_exec(desktop_text):
    """The command of a .desktop file's main entry, field codes removed."""
    exec_line = ""
    in_main = False
    for line in desktop_text.splitlines():
        line = line.strip()
        if line.startswith("["):
            in_main = line == "[Desktop Entry]"
        elif in_main and line.startswith("Exec=") and not exec_line:
            exec_line = line[5:]
    cleaned = re.sub(r"%[a-zA-Z%]", "", exec_line).strip()
    try:
        return shlex.split(cleaned)
    except ValueError:
        return cleaned.split()


def host_desktop_entry(app_id, desktop_text, icon_name=None):
    """A .desktop file for the host menu that starts the app through ozi-box."""
    out, in_main = [], False
    for line in desktop_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_main = stripped == "[Desktop Entry]"
            out.append(line)
            continue
        key = stripped.split("=", 1)[0]
        if in_main and key in ("Exec", "TryExec", "DBusActivatable", "Actions"):
            continue
        out.append(line)
    text = "\n".join(out)
    marker = "[Desktop Entry]"
    text = text.replace(marker, marker + "\nExec=ozi-box run %s\nX-OziOS-Box=%s" % (app_id, app_id), 1)
    return text + "\n"


def run(cmd, **kwargs):
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        raise BoxError(tr("Boxes need podman, which is not installed yet.")) from None


def installed():
    """App ids that have an image, from our own records."""
    path = paths.share_dir() / "boxes.json"
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record(app_id, info):
    path = paths.share_dir() / "boxes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = installed()
    data[app_id] = info
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def forget(app_id):
    path = paths.share_dir() / "boxes.json"
    data = installed()
    if data.pop(app_id, None) is not None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
