"""What an app is allowed to reach, in one vocabulary for every kind of box.

The same Permissions record drives boxed .deb apps (podman), Flatpak apps
(`flatpak override`) and sandboxed AppImages (bubblewrap).
"""
import json
import os
import posixpath
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import paths
from .i18n import tr

APP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}$")


@dataclass
class Permissions:
    network: bool = False
    files: str = "none"                 # none | chosen | home
    folders: list = field(default_factory=list)
    gpu: bool = True
    sound: bool = True
    camera: bool = False
    devices: bool = False               # USB and other raw devices
    x11: bool = False                   # old-style display access
    nested_sandbox: bool = False        # apps with a sandbox of their own (Chrome, Electron)

    def as_dict(self):
        return asdict(self)


DEFAULTS = Permissions()
FILE_MODES = ("none", "chosen", "home")


def check_app_id(app_id):
    if not APP_ID.match(app_id or ""):
        raise ValueError("invalid app id: %r" % (app_id,))
    return app_id


def clean_folders(folders, home=None):
    """Absolute, existing-or-not folder paths without surprises."""
    home = home or os.path.expanduser("~")
    out = []
    for folder in folders or []:
        if not isinstance(folder, str) or not folder:
            continue
        folder = posixpath.normpath(os.path.expanduser(folder))
        if not posixpath.isabs(folder) or folder in ("/", "/etc", "/usr", "/boot", "/proc", "/sys", "/dev"):
            continue
        if folder not in out:
            out.append(folder)
    return out


def from_dict(data, home=None):
    """Build Permissions from untrusted JSON, ignoring anything unexpected."""
    perms = Permissions()
    if not isinstance(data, dict):
        return perms
    for name in ("network", "gpu", "sound", "camera", "devices", "x11", "nested_sandbox"):
        if isinstance(data.get(name), bool):
            setattr(perms, name, data[name])
    if data.get("files") in FILE_MODES:
        perms.files = data["files"]
    perms.folders = clean_folders(data.get("folders"), home)
    return perms


def profile_path(app_id):
    return paths.config_dir() / "permissions" / (check_app_id(app_id) + ".json")


def load(app_id, home=None):
    try:
        with open(profile_path(app_id), encoding="utf-8") as fh:
            return from_dict(json.load(fh), home)
    except (OSError, ValueError):
        return Permissions()


def save(app_id, perms):
    path = profile_path(app_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(perms.as_dict(), indent=2), encoding="utf-8")
    os.replace(tmp, path)


def describe(perms):
    """Plain-language list of (name, state) pairs for the permissions page."""
    if perms.files == "none":
        files = tr("None")
    elif perms.files == "chosen":
        files = ", ".join(perms.folders) if perms.folders else tr("None chosen yet")
    else:
        files = tr("Your whole home folder")
    yes, no = tr("Allowed"), tr("Blocked")
    return [
        (tr("Internet"), yes if perms.network else no),
        (tr("Files"), files),
        (tr("Graphics acceleration"), yes if perms.gpu else no),
        (tr("Sound and microphone"), yes if perms.sound else no),
        (tr("Camera"), yes if perms.camera else no),
        (tr("Other devices"), yes if perms.devices else no),
        (tr("Old-style display access"), yes if perms.x11 else no),
        (tr("Apps with their own sandbox"), yes if perms.nested_sandbox else no),
    ]


def flatpak_overrides(perms):
    """Arguments for `flatpak override --user <app>`."""
    args = ["--share=network" if perms.network else "--unshare=network",
            "--device=dri" if perms.gpu else "--nodevice=dri",
            "--socket=pulseaudio" if perms.sound else "--nosocket=pulseaudio",
            "--socket=x11" if perms.x11 else "--nosocket=x11",
            "--socket=fallback-x11" if perms.x11 else "--nosocket=fallback-x11",
            "--device=all" if (perms.camera or perms.devices) else "--nodevice=all"]
    if perms.files == "home":
        args += ["--filesystem=home"]
    else:
        args += ["--nofilesystem=host", "--nofilesystem=home"]
        if perms.files == "chosen":
            args += ["--filesystem=%s" % folder for folder in perms.folders]
    return args


def runtime_dir():
    return os.environ.get("XDG_RUNTIME_DIR") or "/run/user/%d" % os.getuid()


def private_home(app_id):
    return paths.share_dir() / "apps" / check_app_id(app_id) / "home"


def bwrap_command(app_id, perms, argv, env=None, exists=os.path.exists, ro_binds=()):
    """A bubblewrap command line that runs `argv` with exactly these rights.

    `ro_binds` are (host path, path inside) pairs made visible read-only, for
    the program itself. `exists` is injectable so tests can describe a machine
    without having one.
    """
    env = env if env is not None else os.environ
    home = os.path.expanduser("~")
    run = runtime_dir()
    cmd = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
    if perms.network:
        cmd.append("--share-net")
    cmd += ["--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", run]
    for item in ("ld.so.cache", "ld.so.conf", "ld.so.conf.d", "alternatives", "fonts", "ssl", "ca-certificates",
                 "pki", "resolv.conf", "hosts", "nsswitch.conf", "localtime", "passwd", "group", "os-release",
                 "mime.types", "xdg", "vulkan", "drirc", "machine-id"):
        if exists("/etc/" + item):
            cmd += ["--ro-bind", "/etc/" + item, "/etc/" + item]
    cmd += ["--bind", str(private_home(app_id)), home, "--setenv", "HOME", home,
            "--setenv", "XDG_RUNTIME_DIR", run, "--chdir", home]
    for source, target in ro_binds:
        cmd += ["--ro-bind", str(source), target]
    wayland = env.get("WAYLAND_DISPLAY")
    if wayland and exists(posixpath.join(run, wayland)):
        cmd += ["--ro-bind", posixpath.join(run, wayland), posixpath.join(run, wayland),
                "--setenv", "WAYLAND_DISPLAY", wayland]
    if perms.x11 and env.get("DISPLAY"):
        cmd += ["--ro-bind-try", "/tmp/.X11-unix", "/tmp/.X11-unix", "--setenv", "DISPLAY", env["DISPLAY"]]
        xauth = env.get("XAUTHORITY")
        if xauth and exists(xauth):
            cmd += ["--ro-bind", xauth, xauth, "--setenv", "XAUTHORITY", xauth]
    if perms.gpu:
        cmd += ["--dev-bind-try", "/dev/dri", "/dev/dri", "--ro-bind-try", "/sys", "/sys"]
    if perms.sound:
        for sock in ("pipewire-0", "pulse/native"):
            path = posixpath.join(run, sock)
            if exists(path):
                cmd += ["--ro-bind", path, path]
    if perms.camera:
        for n in range(8):
            node = "/dev/video%d" % n
            if exists(node):
                cmd += ["--dev-bind", node, node]
    if perms.devices:
        cmd += ["--dev-bind-try", "/dev/bus/usb", "/dev/bus/usb"]
    if perms.files == "home":
        cmd += ["--bind", home, home]
    elif perms.files == "chosen":
        for folder in perms.folders:
            cmd += ["--bind", folder, folder]
    for name in ("LANG", "LC_ALL", "TERM", "XCURSOR_THEME", "XCURSOR_SIZE", "QT_QPA_PLATFORM", "XDG_SESSION_TYPE"):
        if env.get(name):
            cmd += ["--setenv", name, env[name]]
    cmd.append("--")
    return cmd + list(argv)
