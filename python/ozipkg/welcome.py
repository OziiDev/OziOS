"""Logic behind the welcome app: which programs its buttons start, the
installed version, and whether it opens at login. No Qt.
"""
import os
import subprocess
import tempfile
import time

from . import paths, themes
from .i18n import tr

# Our wrapper around the live image's own launcher (which prepares the keyring and mirrors, then starts Calamares).
INSTALLER = "/usr/lib/ozios/start-installer"

# Button name -> command. A fixed table: the interface can only pick a name.
ACTIONS = {
    "gaming": ["konsole", "--hold", "-e", "ozi", "gaming", "--yes"],
    "store": ["ozi-store"],
    "windows": ["ozi-winsetup", "--gui"],
    "theme": ["bash", "/usr/share/ozios/tools/apply-branding.sh"],
    "settings": ["systemsettings"],
    "terminal": ["konsole"],
    "network": ["systemsettings", "kcm_networkmanagement"],
    "display": ["systemsettings", "kcm_kscreen"],
    "install": [INSTALLER],
    # Education edition
    "pen": ["ozi-pen"],
    "whiteboard": ["xournalpp"],
    "classroom": ["ozi-classroom"],
    "eba": ["xdg-open", "https://eba.gov.tr"],
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


def blocker(name, live=None, kvm_path="/dev/kvm"):
    """A reason a button can not work on this machine right now, or an empty string."""
    if name == "windows":
        if (is_live() if live is None else live):
            return tr("The Windows layer needs a disk to live on, and this is a live session. Install OziOS first, then set it up from here.")
        if not os.path.exists(kvm_path):
            return tr("Hardware virtualization is not available. Turn on VT-x or SVM in the firmware setup.")
    return ""


def launch(name, log=lambda line: None, popen=subprocess.Popen, live=None, kvm_path="/dev/kvm", wait=1.0):
    if name not in ACTIONS:
        raise ValueError("unknown action: %r" % (name,))
    reason = blocker(name, live, kvm_path)
    if reason:
        raise ValueError(reason)
    with tempfile.TemporaryFile() as errors:           # the program keeps its own copy of the handle
        try:
            proc = popen(ACTIONS[name], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors,
                         start_new_session=True)
        except OSError:
            raise ValueError(tr("{program} is not installed.", program=ACTIONS[name][0])) from None
        # A program that stops at once has something to say; without this the button just does nothing.
        poll = getattr(proc, "poll", None)
        if poll:
            time.sleep(wait)
            code = poll()
            if code not in (None, 0):
                errors.seek(0)
                lines = errors.read().decode("utf-8", "replace").strip().splitlines()
                why = lines[-1][:200] if lines else ""
                raise ValueError(tr("{program} stopped right away: {why}", program=ACTIONS[name][0], why=why) if why
                                 else tr("{program} stopped right away.", program=ACTIONS[name][0]))
    return {"started": name}


def theme_choices(log=lambda line: None):
    """The colour themes, the one in use marked, for the swatches."""
    return themes.listing()


def set_theme(theme_id, log=lambda line: None, run=subprocess.run, home=None, config=None):
    """Switch the desktop to a theme; the window takes on its palette from the answer.
    A theme picked here ends the day and night switching, as `ozi theme <name>` does."""
    if theme_id not in themes.BY_ID:
        raise ValueError("unknown theme: %r" % (theme_id,))
    code = themes.apply(theme_id, run=run, home=home)
    if code == 127:
        raise ValueError(tr("plasma-apply-colorscheme is missing; run this inside the desktop session"))
    if code != 0:
        raise ValueError(tr("The colours could not be changed"))
    themes.stop_auto(run, config)
    return {"theme": theme_id, "palette": themes.app_palette(theme_id)}


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


def edition(path="/usr/share/ozios/edition"):
    """"edu" on the Education edition, "" on the ordinary one."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def is_live(root="/run/archiso", installer=INSTALLER):
    """True in a live session that can install the system."""
    return os.path.isdir(root) and os.access(installer, os.X_OK)


def info(log=lambda line: None):
    return {"version": version(), "show": show_at_login(), "live": is_live(), "edu": edition() == "edu"}
