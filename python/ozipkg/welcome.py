"""Logic behind the welcome app: which programs its buttons start, the
installed version, and whether it opens at login. No Qt.
"""
import os
import subprocess

from . import paths
from .i18n import tr

# The live image's own launcher: it prepares the keyring and mirrors, then starts Calamares.
INSTALLER = "/usr/local/bin/calamares-online.sh"

# Button name -> command. A fixed table: the interface can only pick a name.
ACTIONS = {
    "store": ["ozi-store"],
    "windows": ["ozi-winsetup", "--gui"],
    "theme": ["bash", "/usr/share/ozios/tools/apply-branding.sh"],
    "settings": ["systemsettings"],
    "terminal": ["konsole"],
    "network": ["systemsettings", "kcm_networkmanagement"],
    "display": ["systemsettings", "kcm_kscreen"],
    "install": [INSTALLER],
}
MARKER = "ozi-welcome-hidden"


def version():
    for path in ("/usr/share/ozios/VERSION", os.path.join(paths.data_dir().parent, "VERSION")):
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            continue
    return ""


def launch(name, log=lambda line: None, popen=subprocess.Popen):
    if name not in ACTIONS:
        raise ValueError("unknown action: %r" % (name,))
    try:
        popen(ACTIONS[name], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              start_new_session=True)
    except OSError:
        raise ValueError(tr("{program} is not installed.", program=ACTIONS[name][0])) from None
    return {"started": name}


def show_at_login():
    return not os.path.exists(paths.config_dir() / MARKER)


def set_show_at_login(value):
    marker = paths.config_dir() / MARKER
    if value:
        try:
            os.remove(marker)
        except OSError:
            pass
    else:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
    return {"show": bool(value)}


def is_live(root="/run/archiso", installer=INSTALLER):
    """True in a live session that can install the system."""
    return os.path.isdir(root) and os.access(installer, os.X_OK)


def info(log=lambda line: None):
    return {"version": version(), "show": show_at_login(), "live": is_live()}
