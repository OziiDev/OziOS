"""`ozi report`: collect what a bug report needs, without what it must not carry.

Nothing is sent anywhere. The report is a text file the person reads, then
attaches to an issue if they want to. Names, addresses and serial numbers are
replaced before the file is written, and the file is private to the user.
"""
import datetime
import os
import re

from . import doctor
from .i18n import tr

PACKAGES = ("linux-ozios", "linux-ozios-nvidia-open", "ozios-settings", "ozios-edu", "mesa", "nvidia-utils",
            "vulkan-icd-loader", "plasma-desktop", "qt6-base", "podman", "bubblewrap", "pacman", "systemd", "grub",
            "limine", "mkinitcpio")
OS_KEYS = ("NAME", "VERSION", "VARIANT", "VARIANT_ID", "ID", "ID_LIKE", "BUILD_ID", "OZIOS_VERSION")

MAC = re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6 = re.compile(r"(?<![\w:])(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?![\w:])")
UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
SERIAL = re.compile(r"(?i)(serial(?:\s*(?:number|no\.?))?\s*[:=]\s*)\S+")
HOME = re.compile(r"/(?:home|Users)/([^/\s]+)")
KEEP_IPV4 = ("127.0.0.1", "0.0.0.0", "255.255.255.255", "255.255.255.0", "255.255.0.0", "255.0.0.0")


def _word(name):
    """A pattern for `name` as a whole word, so 'ozi' does not match inside 'ozios' or 'ozi-pkg'."""
    return re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(name))


def redact(text, user="", host="", home=""):
    """The text with everything that names the person or their network removed."""
    out = text
    if home:
        out = out.replace(home, "~")
    out = HOME.sub("/home/<user>", out)
    for name, label in ((user, "<user>"), (host, "<host>")):
        if name and len(name) >= 2:
            out = _word(name).sub(label, out)
    out = MAC.sub("<mac>", out)
    out = UUID.sub("<uuid>", out)
    out = EMAIL.sub("<email>", out)
    out = SERIAL.sub(lambda m: m.group(1) + "<serial>", out)

    def v6(match):
        value = match.group(0)
        # Times (12:21:47) and the like have neither letters nor a double colon.
        if "::" in value or re.search(r"[a-fA-F]", value):
            return "<ip6>"
        return value
    out = IPV6.sub(v6, out)
    out = IPV4.sub(lambda m: m.group(0) if m.group(0) in KEEP_IPV4 else "<ip>", out)
    return out


def section(title, body):
    body = (body or "").strip("\n")
    return "== %s ==\n%s\n" % (title, body if body else "(nothing)")


def collect(probe, now=None):
    """The raw report text, before redaction."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    parts = ["OziOS report, %s UTC\n" % now.strftime("%Y-%m-%d %H:%M")]

    info = doctor.parse_keyvalue(probe.read("/etc/os-release"))
    parts.append(section("System", "\n".join("%s=%s" % (k, info[k]) for k in OS_KEYS if k in info)))

    cmdline = (probe.read("/proc/cmdline") or "").strip()
    parts.append(section("Kernel", "release: %s\ncommand line: %s" % (probe.release(), cmdline)))

    cpu = ""
    for line in (probe.read("/proc/cpuinfo") or "").splitlines():
        if line.startswith("model name"):
            cpu = line.split(":", 1)[1].strip()
            break
    meminfo = doctor.parse_meminfo(probe.read("/proc/meminfo"))
    boot = "UEFI" if probe.exists("/sys/firmware/efi") else "BIOS"
    parts.append(section("Machine", "cpu: %s\nmemory: %s\nfirmware: %s" % (
        cpu or "?", doctor.human_size(meminfo.get("MemTotal", 0)) if meminfo else "?", boot)))

    code, text = probe.run(["lspci", "-nn"])
    parts.append(section("PCI devices", text if code == 0 else "(lspci is not available)"))

    versions = []
    for name in PACKAGES:
        code, text = probe.run(["pacman", "-Q", name])
        if code == 0 and text.strip():
            versions.append(text.strip())
    parts.append(section("Packages", "\n".join(versions)))

    code, text = probe.run(["systemctl", "--failed", "--no-legend", "--plain"])
    parts.append(section("Failed services", text if code == 0 else ""))

    code, text = probe.run(["journalctl", "-b", "-p", "3", "--no-pager", "-n", "80"])
    parts.append(section("Errors in this boot (last 80)", text if code == 0 else "(the journal could not be read)"))

    checks = doctor.run_checks(probe)
    parts.append(section("ozi doctor", doctor.format_text(checks)))
    return "\n".join(parts)


def default_path(home, now=None):
    now = now or datetime.datetime.now()
    return os.path.join(home, "ozios-report-%s.txt" % now.strftime("%Y%m%d-%H%M"))


def main(argv=None, out=print, probe=None, home=None, host=None, now=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi report", description=tr("Write a report for a bug report, with names and addresses removed."))
    parser.add_argument("--output", "-o", help=tr("where to write the report"))
    parser.add_argument("--stdout", action="store_true", help=tr("print the report instead of writing a file"))
    args = parser.parse_args(argv)

    probe = probe or doctor.Probe()
    home = home or os.path.expanduser("~")
    if host is None:
        code, text = probe.run(["hostname"])
        host = text.strip() if code == 0 else ""
    text = redact(collect(probe, now=None), user=probe.user(), host=host, home=home)
    if args.stdout:
        out(text)
        return 0
    path = args.output or default_path(home, now)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    out(tr("Report written to {path}", path=path))
    out(tr("Names, addresses and serial numbers were removed. Read it before you share it."))
    return 0
