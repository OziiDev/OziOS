"""Where things live, installed or in a source checkout."""
import os
from pathlib import Path

_here = Path(__file__).resolve()


def _checkout_root():
    """The repository root when running from a checkout, else None."""
    root = _here.parents[2]
    return root if (root / "python" / "ozipkg").is_dir() and (root / "data").is_dir() else None


def data_dir():
    override = os.environ.get("OZIOS_DATA")
    if override:
        return Path(override)
    root = _checkout_root()
    return root / "data" if root else Path("/usr/share/ozios/data")


def data_file(*parts):
    return str(data_dir().joinpath(*parts))


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return Path(base) / "ozios"


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "ozios"


def share_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "ozios"


HELPER = "/usr/lib/ozios/ozi-pkg-helper"
