"""`ozi gaming`: the programs games need, chosen for this machine's graphics card.

Steam wants 32-bit Vulkan and OpenGL drivers, and when it is installed by hand
pacman asks which driver provides them; with --noconfirm it takes the first,
which may be for the wrong card. Here the drivers are named from the card that
is in the machine. Nothing is installed without --yes.
"""
from . import cli, doctor
from .i18n import tr

BASE = ("steam", "gamemode", "lib32-gamemode", "mangohud", "lib32-mangohud", "gamescope")
DRIVERS = {
    "amd": ("mesa", "lib32-mesa", "vulkan-radeon", "lib32-vulkan-radeon"),
    "intel": ("mesa", "lib32-mesa", "vulkan-intel", "lib32-vulkan-intel"),
}


def installed_packages(probe):
    code, text = probe.run(["pacman", "-Qq"], timeout=30)
    return set(text.split()) if code == 0 else set()


def graphics(probe):
    """The vendors of the graphics cards in the machine, without repeats."""
    code, text = probe.run(["lspci", "-nn"])
    vendors = []
    for vendor, _ in doctor.pci_gpus(text if code == 0 else ""):
        if vendor not in vendors:
            vendors.append(vendor)
    return vendors


def plan(probe):
    """{"wanted", "missing", "notes"}: what the machine needs and what is not installed yet."""
    have = installed_packages(probe)
    vendors = graphics(probe)
    wanted = list(BASE)
    notes = []
    for vendor in vendors:
        if vendor in DRIVERS:
            wanted += [name for name in DRIVERS[vendor] if name not in wanted]
        elif vendor == "nvidia":
            if "nvidia-utils" in have:
                if "lib32-nvidia-utils" not in wanted:
                    wanted.append("lib32-nvidia-utils")
            else:
                notes.append(tr("The NVIDIA driver is not installed yet. Run `sudo chwd -a` first, then run this again."))
    if not vendors:
        notes.append(tr("No graphics card was recognised, so only the game programs are listed."))
    return {"wanted": wanted, "missing": [n for n in wanted if n not in have], "notes": notes}


def main(argv=None, out=print, probe=None, caller=cli.call_helper):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi gaming", description=tr("Install what games need. Shows the list unless --yes is given."))
    parser.add_argument("--yes", "-y", action="store_true", help=tr("install them"))
    args = parser.parse_args(argv)
    probe = probe or doctor.Probe()

    result = plan(probe)
    for note in result["notes"]:
        out(note)
    if not result["missing"]:
        out(tr("Everything games need is installed."))
        return 0
    out(tr("Needed and not installed:"))
    for name in result["missing"]:
        out("  " + name)
    if not args.yes:
        out("")
        out(tr("Run `ozi gaming --yes` to install them."))
        return 0
    return 1 if caller("install-repo", result["missing"], out=out) else 0
