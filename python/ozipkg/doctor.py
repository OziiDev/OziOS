"""`ozi doctor`: is this system in good shape, and if not, what to do about it.

Every check asks a Probe (the machine) and returns plain findings, so the rules
can be tested with a made-up machine. Nothing here changes the system; where
something is wrong the finding says which command would fix it.
"""
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict

from .i18n import tr

LEVELS = ("ok", "info", "warn", "fail")
GIB = 1024 ** 3
MIB = 1024 ** 2


@dataclass
class Check:
    id: str
    level: str            # ok | info | warn | fail
    title: str
    detail: str = ""
    hint: str = ""        # a command or step that would fix it

    def as_dict(self):
        return asdict(self)


class Probe:
    """What the checks may ask the machine. Reads and runs, never writes."""

    def read(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return None

    def exists(self, path):
        return os.path.exists(path)

    def which(self, name):
        return shutil.which(name) is not None

    def run(self, argv, timeout=15):
        """(exit status, standard output); (127, "") when the program is not there."""
        try:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, errors="replace")
        except FileNotFoundError:
            return 127, ""
        except (OSError, subprocess.SubprocessError):
            return 126, ""
        return done.returncode, done.stdout

    def usage(self, path):
        """(total, free) bytes of the file system holding `path`, or None."""
        try:
            data = shutil.disk_usage(path)
        except OSError:
            return None
        return data.total, data.free

    def release(self):
        return os.uname().release if hasattr(os, "uname") else ""

    def user(self):
        return os.environ.get("USER") or os.environ.get("LOGNAME") or ""


# --- helpers -----------------------------------------------------------------

def parse_keyvalue(text):
    """The KEY=value lines of os-release and friends, quotes removed."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def human_size(count):
    for unit, size in (("GiB", GIB), ("MiB", MIB)):
        if count >= size:
            return "%.1f %s" % (count / size, unit)
    return "%d KiB" % (count // 1024)


def pci_gpus(lspci_text):
    """[(vendor, description)] for the display controllers in `lspci -nn` output."""
    found = []
    for line in (lspci_text or "").splitlines():
        if not re.search(r"\b(VGA compatible controller|3D controller|Display controller)\b", line):
            continue
        match = re.search(r"\[([0-9a-f]{4}):[0-9a-f]{4}\]", line)
        vendor_id = match.group(1) if match else ""
        vendor = {"10de": "nvidia", "1002": "amd", "8086": "intel"}.get(vendor_id, "other")
        description = re.sub(r"^\S+\s+[^:]+:\s*", "", line).strip()
        found.append((vendor, description))
    return found


# --- the checks ----------------------------------------------------------------

def check_kernel(p):
    release = p.release()
    if not release:
        return [Check("kernel", "info", tr("The kernel version could not be read"))]
    out = []
    if release.endswith("-ozios"):
        out.append(Check("kernel", "ok", tr("Kernel {release}", release=release)))
    else:
        out.append(Check("kernel", "warn", tr("Running kernel {release}, not the OziOS kernel", release=release),
                         tr("The OziOS kernel is tuned for desktop and gaming use and carries the NVIDIA modules."),
                         "sudo pacman -S linux-ozios"))
    if not p.exists("/usr/lib/modules/" + release):
        out.append(Check("kernel-modules", "warn", tr("The modules of the running kernel are gone"),
                         tr("A kernel update replaced them. Hardware that was not loaded yet will not work until a restart."),
                         tr("Restart the computer")))
    return out


def check_identity(p):
    info = parse_keyvalue(p.read("/etc/os-release"))
    name = info.get("NAME", "")
    if name != "OziOS":
        return [Check("identity", "warn", tr("This does not identify itself as OziOS ({name})", name=name or "?"),
                      tr("Something rewrote /etc/os-release."), "sudo /usr/lib/ozios/identity")]
    edition = info.get("VARIANT", "")
    version = info.get("OZIOS_VERSION", "")
    text = "OziOS %s" % version if version else "OziOS"
    if edition:
        text += " (%s)" % edition
    return [Check("identity", "ok", text)]


def check_virtualization(p):
    flags = p.read("/proc/cpuinfo") or ""
    capable = re.search(r"\b(vmx|svm)\b", flags) is not None
    has_kvm = p.exists("/dev/kvm")
    if capable and has_kvm:
        return [Check("kvm", "ok", tr("Hardware virtualization is on"))]
    if capable:
        return [Check("kvm", "warn", tr("The processor can virtualize but /dev/kvm is missing"),
                      tr("Virtualization may be switched off in the firmware setup. The Windows layer needs it."),
                      tr("Turn on VT-x or SVM in the firmware setup"))]
    return [Check("kvm", "info", tr("No hardware virtualization"),
                  tr("The Windows layer can not run without it. Everything else is unaffected."))]


def check_gpu(p):
    code, text = p.run(["lspci", "-nn"])
    if code == 127:
        return [Check("gpu", "info", tr("lspci is not installed, so the graphics card was not checked"))]
    gpus = pci_gpus(text)
    if not gpus:
        return [Check("gpu", "info", tr("No graphics card was found"))]
    modules = {line.split()[0] for line in (p.read("/proc/modules") or "").splitlines() if line.strip()}
    wanted = {"nvidia": {"nvidia"}, "amd": {"amdgpu", "radeon"}, "intel": {"i915", "xe"}}
    out = []
    for vendor, description in gpus:
        if vendor in wanted and not (wanted[vendor] & modules):
            hint = {"nvidia": "sudo chwd -a", "amd": "sudo pacman -S mesa vulkan-radeon",
                    "intel": "sudo pacman -S mesa vulkan-intel"}[vendor]
            level = "warn"
            out.append(Check("gpu", level, tr("The driver for {gpu} is not loaded", gpu=description),
                             tr("The screen works, but without acceleration or with a generic driver."), hint))
        else:
            out.append(Check("gpu", "ok", description))
    if len(gpus) > 1:
        out.append(Check("gpu-hybrid", "info", tr("Two graphics cards"),
                         tr("A game can ask for the stronger one."), "ozi play --gpu discrete -- <game>"))
    return out


def check_disk(p):
    out = []
    root = p.usage("/")
    if root:
        total, free = root
        share = free / total if total else 0
        if free < 2 * GIB:
            out.append(Check("disk", "fail", tr("The system disk is almost full: {free} left", free=human_size(free)),
                             tr("Updates and boxes need room to work."), "ozi clean"))
        elif share < 0.10 or free < 5 * GIB:
            out.append(Check("disk", "warn", tr("The system disk is getting full: {free} left", free=human_size(free)),
                             "", "ozi clean"))
        else:
            out.append(Check("disk", "ok", tr("{free} free on the system disk", free=human_size(free))))
    boot = p.usage("/boot")
    if boot and root and boot[0] != root[0] and boot[1] < 100 * MIB:
        out.append(Check("boot-space", "warn", tr("The boot partition has only {free} left", free=human_size(boot[1])),
                         tr("A kernel update needs room for a new initramfs."), "ozi clean"))
    return out


def check_packages(p):
    out = []
    if p.exists("/var/lib/pacman/db.lck"):
        code, _ = p.run(["pgrep", "-x", "pacman"])
        if code == 1:                                           # no pacman process is running
            out.append(Check("pacman-lock", "warn", tr("A package operation left its lock behind"),
                             tr("Nothing can be installed or updated until it is removed."),
                             "sudo rm /var/lib/pacman/db.lck"))
    conf = p.read("/etc/pacman.conf") or ""
    repos = re.findall(r"^\[([^\]]+)\]\s*$", conf, re.M)
    repos = [r for r in repos if r != "options"]
    if repos:
        out.append(Check("repos", "ok", tr("Repositories: {names}", names=", ".join(repos))))
    else:
        out.append(Check("repos", "fail", tr("pacman has no repositories"), "", "/etc/pacman.conf"))
    if p.which("checkupdates"):
        code, text = p.run(["checkupdates"], timeout=90)
        if code == 0:
            count = len([line for line in text.splitlines() if line.strip()])
            out.append(Check("updates", "info", tr("{n} updates waiting", n=count), "", "ozi update"))
        elif code == 2:
            out.append(Check("updates", "ok", tr("Up to date")))
        else:
            out.append(Check("updates", "info", tr("Could not look for updates (offline?)")))
    code, text = p.run(["pacman", "-Qdtq"])
    orphans = [line for line in text.splitlines() if line.strip()] if code == 0 else []
    if orphans:
        out.append(Check("orphans", "info", tr("{n} packages are no longer needed", n=len(orphans)), "", "ozi clean"))
    return out


def check_boxes(p):
    out = []
    if p.which("podman"):
        out.append(Check("podman", "ok", tr("Boxes for Debian and Ubuntu packages are available")))
        user = p.user()
        if user:
            ranges = [(p.read("/etc/subuid") or ""), (p.read("/etc/subgid") or "")]
            if not all(re.search(r"^%s:" % re.escape(user), text, re.M) for text in ranges):
                out.append(Check("subids", "info", tr("{user} has no user-id range for boxes yet", user=user),
                                 tr("It is set up the first time a box is made."), ""))
    else:
        out.append(Check("podman", "info", tr("podman is not installed, so .deb packages can not be boxed"), "",
                         "sudo pacman -S podman"))
    if not p.which("bwrap"):
        out.append(Check("bwrap", "info", tr("bubblewrap is not installed, so AppImages can not be sandboxed"), "",
                         "sudo pacman -S bubblewrap"))
    if not (p.exists("/usr/lib/ozios/ozi-pkg-helper") and
            p.exists("/usr/share/polkit-1/actions/org.ozios.pkg.manage.policy")):
        out.append(Check("helper", "fail", tr("The package helper is missing"),
                         tr("Installing and removing software through Software will not work."),
                         "sudo pacman -S ozios-settings"))
    return out


def check_snapshots(p):
    fs = ""
    for line in (p.read("/proc/mounts") or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "/":
            fs = parts[2]
    if fs != "btrfs":
        return [Check("snapshots", "info", tr("The system disk is {fs}; snapshots need btrfs", fs=fs or "?"))]
    if not p.which("snapper"):
        return [Check("snapshots", "warn", tr("No snapshots: a bad update can not be rolled back"), "",
                      "sudo pacman -S snapper")]
    code, text = p.run(["snapper", "list-configs"])
    if code == 0 and re.search(r"^root\b", text, re.M):
        return [Check("snapshots", "ok", tr("Snapshots are set up"))]
    return [Check("snapshots", "info", tr("snapper is installed but has no configuration for the system disk"), "",
                  "sudo snapper -c root create-config /")]


def check_time(p):
    code, text = p.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    if code != 0:
        return []
    if text.strip() == "yes":
        return [Check("time", "ok", tr("The clock is synchronized"))]
    return [Check("time", "warn", tr("The clock is not synchronized"),
                  tr("A wrong clock makes secure connections and package signatures fail."),
                  "sudo timedatectl set-ntp true")]


def check_services(p):
    code, text = p.run(["systemctl", "--failed", "--no-legend", "--plain"])
    if code != 0:
        return []
    units = [line.split()[0] for line in text.splitlines() if line.strip()]
    if not units:
        return [Check("services", "ok", tr("No service has failed"))]
    shown = ", ".join(units[:5]) + (" ..." if len(units) > 5 else "")
    return [Check("services", "warn", tr("{n} services have failed: {names}", n=len(units), names=shown), "",
                  "systemctl status " + units[0])]


def check_network(p):
    table = p.read("/proc/net/route")
    if table is None:
        return []
    for line in table.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 2 and fields[1] == "00000000":
            return [Check("network", "ok", tr("The computer has a network route"))]
    return [Check("network", "info", tr("There is no network route"), tr("Updates and downloads need a connection."))]


def check_memory(p):
    meminfo = parse_meminfo(p.read("/proc/meminfo"))
    total = meminfo.get("MemTotal", 0)
    if not total:
        return []
    out = []
    if total < 3 * GIB:
        out.append(Check("memory", "warn", tr("Only {size} of memory", size=human_size(total)),
                         tr("The Windows layer and boxes need more to run well.")))
    else:
        out.append(Check("memory", "ok", tr("{size} of memory", size=human_size(total))))
    if "zram" in (p.read("/proc/swaps") or ""):
        out.append(Check("zram", "ok", tr("Compressed swap in memory (zram) is on")))
    return out


def parse_meminfo(text):
    out = {}
    for line in (text or "").splitlines():
        match = re.match(r"^(\w+):\s+(\d+)\s*kB", line)
        if match:
            out[match.group(1)] = int(match.group(2)) * 1024
    return out


def check_firmware(p):
    if p.exists("/sys/firmware/efi"):
        return [Check("firmware", "ok", tr("Started in UEFI mode"))]
    return [Check("firmware", "info", tr("Started in BIOS mode"))]


def check_edition(p):
    if (p.read("/usr/share/ozios/edition") or "").strip() != "edu":
        return []
    missing = [name for name in ("ozi-pen", "ozi-classroom", "xournalpp", "okular") if not p.which(name)]
    if missing:
        return [Check("edu", "warn", tr("The Education edition is missing programs: {names}", names=", ".join(missing)),
                      "", "sudo pacman -S ozios-edu")]
    return [Check("edu", "ok", tr("The Education edition is complete"))]


CHECKS = (check_identity, check_kernel, check_firmware, check_memory, check_disk, check_gpu, check_virtualization,
          check_packages, check_boxes, check_snapshots, check_time, check_services, check_network, check_edition)


def run_checks(probe=None):
    probe = probe or Probe()
    results = []
    for check in CHECKS:
        try:
            results.extend(check(probe))
        except Exception as err:                    # a broken probe must not hide the other checks
            results.append(Check(check.__name__[len("check_"):], "info", tr("This check could not run: {err}", err=err)))
    return results


def worst(checks):
    return max((c.level for c in checks), key=LEVELS.index, default="ok")


MARK = {"ok": "ok  ", "info": "info", "warn": "WARN", "fail": "FAIL"}


def format_text(checks, quiet=False):
    lines = []
    for c in checks:
        if quiet and c.level in ("ok", "info"):
            continue
        lines.append("%s  %s" % (MARK[c.level], c.title))
        if c.detail and c.level != "ok":
            lines.append("      " + c.detail)
        if c.hint and c.level in ("warn", "fail", "info"):
            lines.append("      -> " + c.hint)
    counts = {level: sum(1 for c in checks if c.level == level) for level in LEVELS}
    lines.append("")
    if counts["fail"]:
        lines.append(tr("{n} problems need attention.", n=counts["fail"]))
    elif counts["warn"]:
        lines.append(tr("{n} things are worth a look.", n=counts["warn"]))
    else:
        lines.append(tr("Everything looks fine."))
    return "\n".join(lines)


def main(argv=None, out=print, probe=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi doctor", description=tr("Check that this system is in good shape."))
    parser.add_argument("--json", action="store_true", help=tr("machine-readable output"))
    parser.add_argument("--quiet", action="store_true", help=tr("show only warnings and problems"))
    args = parser.parse_args(argv)
    checks = run_checks(probe)
    if args.json:
        out(json.dumps({"worst": worst(checks), "checks": [c.as_dict() for c in checks]}, indent=2, ensure_ascii=False))
    else:
        out(format_text(checks, quiet=args.quiet))
    return 1 if worst(checks) == "fail" else 0
