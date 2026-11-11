"""AUR support: look packages up, review their build recipe, build in a box.

Nothing from the AUR is run on the host. The recipe (PKGBUILD and any .install
file) is fetched as a snapshot, read by the same risk rules as a .deb script,
and then built inside a throwaway Arch container that sees only the build
folder. The finished package goes through the privileged helper like any
other file, with the SHA-256 of what was built.

Network and process access is injected (`fetch`, `runner`) so every step can be
tested without the internet or podman.
"""
import io
import json
import os
import re
import tarfile
import urllib.parse
import urllib.request

from . import box, risk
from .i18n import tr

RPC = "https://aur.archlinux.org/rpc/v5/"
SNAPSHOT = "https://aur.archlinux.org/cgit/aur.git/snapshot/%s.tar.gz"
BUILD_IMAGE = "docker.io/library/archlinux:base-devel"
MAX_SNAPSHOT = 20 * 1024 * 1024
MAX_RECIPE_FILE = 1024 * 1024
MAX_DEPTH = 8
POPULAR = {
    "yay", "paru", "google-chrome", "brave-bin", "visual-studio-code-bin", "spotify", "discord", "slack-desktop",
    "zoom", "teams", "onlyoffice-bin", "obs-studio", "vlc", "firefox", "chromium", "steam", "heroic-games-launcher-bin",
    "timeshift", "dropbox", "nordvpn-bin", "protonvpn", "teamviewer", "anydesk-bin", "mullvad-vpn-bin", "ventoy-bin",
}
PACKAGE_NAME = re.compile(r"^[a-z0-9@._+][a-z0-9@._+-]{0,99}$")


class AurError(Exception):
    pass


def default_fetch(url, limit=MAX_SNAPSHOT):
    request = urllib.request.Request(url, headers={"User-Agent": "ozi-pkg"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise AurError("the download is larger than %d bytes" % limit)
    return data


def rpc(kind, args, fetch=default_fetch):
    if kind == "info":
        url = RPC + "info?" + "&".join("arg[]=" + urllib.parse.quote(a) for a in args)
    else:
        url = RPC + "search/" + urllib.parse.quote(args[0], safe="") + "?by=name-desc"
    try:
        data = json.loads(fetch(url, 2 * 1024 * 1024))
    except (ValueError, OSError) as err:
        raise AurError(tr("The AUR did not answer: {err}", err=err)) from None
    if data.get("type") == "error":
        raise AurError(data.get("error", "AUR error"))
    return data.get("results", [])


def info(names, fetch=default_fetch):
    """AUR records for `names`, keyed by name."""
    for name in names:
        if not PACKAGE_NAME.match(name):
            raise AurError("invalid package name: %r" % (name,))
    return {r["Name"]: r for r in rpc("info", list(names), fetch)}


def search(term, fetch=default_fetch):
    return sorted(rpc("search", [term], fetch), key=lambda r: -r.get("NumVotes", 0))


def dependency_names(record):
    """Bare names from the Depends and MakeDepends lists (version ranges removed)."""
    names = []
    for key in ("Depends", "MakeDepends"):
        for dep in record.get(key, []) or []:
            name = re.split(r"[<>=]", dep, maxsplit=1)[0].strip()
            if name and name not in names:
                names.append(name)
    return names


def resolve(names, fetch=default_fetch, in_repo=lambda name: False):
    """Build order for `names` and the AUR packages they need, dependencies first.

    `in_repo(name)` says whether a name is satisfied by the normal repositories
    (or already installed). Returns a list of AUR records.
    """
    order, seen = [], set()

    def visit(name, depth, trail):
        if name in seen:
            return
        if depth > MAX_DEPTH:
            raise AurError(tr("The dependencies of {name} go deeper than {n} levels.", name=name, n=MAX_DEPTH))
        if name in trail:
            raise AurError(tr("{name} depends on itself.", name=name))
        found = info([name], fetch).get(name)
        if found is None:
            raise AurError(tr("{name} was not found in the AUR.", name=name))
        for dep in dependency_names(found):
            if not in_repo(dep) and dep not in seen:
                if info([dep], fetch).get(dep):
                    visit(dep, depth + 1, trail + [name])
        seen.add(name)
        order.append(found)

    for name in names:
        if in_repo(name):
            continue
        visit(name, 0, [])
    return order


# --- recipe ---------------------------------------------------------------

def read_snapshot(data, base):
    """{filename: text} for the files in an AUR snapshot, unsafe members skipped."""
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar:
            parts = member.name.split("/")
            if not member.isfile() or len(parts) != 2 or parts[0] != base:
                continue
            clean = parts[1]
            if not clean or clean.startswith(".") or ".." in clean:
                continue
            if member.size > MAX_RECIPE_FILE:
                raise AurError(tr("{name} in the recipe is too large.", name=clean))
            files[clean] = tar.extractfile(member).read().decode("utf-8", "replace")
    if "PKGBUILD" not in files:
        raise AurError(tr("The snapshot of {name} has no PKGBUILD.", name=base))
    return files


def fetch_recipe(base, fetch=default_fetch):
    if not PACKAGE_NAME.match(base):
        raise AurError("invalid package base: %r" % (base,))
    try:
        return read_snapshot(fetch(SNAPSHOT % base), base)
    except (tarfile.TarError, OSError, EOFError) as err:
        raise AurError(tr("Could not read the recipe of {name}: {err}", name=base, err=err)) from None


def scan_pkgbuild(text):
    """Findings specific to a PKGBUILD, on top of the shell rules."""
    findings = []
    sources = re.findall(r"""(?:https?|ftp|git\+https?)://[^\s'")]+""", text)
    plain = [u for u in sources if u.startswith(("http://", "ftp://", "git+http://"))]
    if plain:
        findings.append(risk.Finding(
            "plain-source", "warning", tr("Downloads source code over an unencrypted connection"),
            tr("Anyone on the network path could swap the download for something else."), plain[0], "PKGBUILD", "behaviour"))
    bare_ip = [u for u in sources if re.match(r"\w+(\+\w+)?://\d{1,3}(\.\d{1,3}){3}[:/]", u)]
    if bare_ip:
        findings.append(risk.Finding(
            "ip-source", "warning", tr("Downloads from a bare IP address"),
            tr("Legitimate projects almost always use a domain name."), bare_ip[0], "PKGBUILD", "behaviour"))
    if re.search(r"^\s*(sha\d+|md5|b2)sums(_\w+)?=\(\s*('SKIP'|\"SKIP\")\s*\)", text, re.M) and not re.search(r"git\+|svn\+|hg\+", text):
        findings.append(risk.Finding(
            "no-checksum", "notice", tr("The download is not checked against a fingerprint"),
            tr("The recipe skips the checksum, so a changed download would go unnoticed."), "", "PKGBUILD", "behaviour"))
    return findings


def review_recipe(files, record=None, now=0):
    """All findings for a recipe: shell rules, PKGBUILD rules and AUR metadata."""
    findings = []
    for name, text in sorted(files.items()):
        if name == "PKGBUILD" or name.endswith(".install"):
            findings += risk.scan_script(text, name, contained=False)
    findings += scan_pkgbuild(files["PKGBUILD"])
    if record is not None:
        findings += risk.scan_aur_meta(record, POPULAR, now)
    return risk.sort_findings(findings)


# --- building -------------------------------------------------------------

def build_script(needs_local):
    """The shell script run inside the build container."""
    lines = ["set -e",
             "pacman -Syu --noconfirm --needed base-devel git sudo",
             "useradd -m builder",
             "echo 'builder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builder"]
    if needs_local:
        lines.append("pacman -U --noconfirm --needed /deps/*.pkg.tar.*")
    lines += ["chown -R builder:builder /build",
              "su builder -c 'cd /build && makepkg --syncdeps --noconfirm --needed --clean'"]
    return "; ".join(lines)


def build_command(build_dir, dep_dir=None, driver=None, image=BUILD_IMAGE, name="ozi-aur-build"):
    """The podman command that builds the recipe in `build_dir`.

    The container sees the build folder (read-write) and, when earlier AUR
    packages are needed, their built files (read-only). No home folder, no
    devices, no sockets; the network is on because the sources and the
    dependencies come from there.
    """
    cmd = box.podman(driver) + [
        "run", "--rm", "--name", name, "--security-opt", "no-new-privileges", "--cap-drop", "all",
        "--cap-add", "CHOWN,DAC_OVERRIDE,FOWNER,SETUID,SETGID,KILL,FSETID,SETFCAP,MKNOD,SYS_CHROOT,AUDIT_WRITE",
        "--pids-limit", "4096", "-v", "%s:/build" % build_dir]
    if dep_dir:
        cmd += ["-v", "%s:/deps:ro" % dep_dir]
    return cmd + [image, "sh", "-c", build_script(bool(dep_dir))]


def built_packages(build_dir):
    """Package files makepkg left in the build folder."""
    return sorted(os.path.join(build_dir, f) for f in os.listdir(build_dir)
                  if ".pkg.tar" in f and not f.endswith(".sig"))
