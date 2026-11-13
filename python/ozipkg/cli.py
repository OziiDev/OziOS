"""The `ozi-pkg` command: review a package, install it into a box, manage boxes.

    ozi-pkg review FILE            what is inside, and what deserves a look
    ozi-pkg install FILE.deb       install a Debian/Ubuntu package into its own box
    ozi-pkg install FILE.AppImage  keep an AppImage and run it only in a sandbox
    ozi-pkg install FILE.pkg.tar.* install a reviewed Arch package on the system
    ozi-pkg get|uninstall NAME...  repository packages, through the privileged helper
    ozi-pkg aur NAME...            build AUR packages in a throwaway container, then install
    ozi-pkg search TERM            search the AUR
    ozi-pkg upgrade | undo N       update the system, or roll back to snapshot N
    ozi-pkg list                   installed boxes
    ozi-pkg perms APP [options]    show or change what an app may reach
    ozi-pkg run APP [args]         start a boxed app
    ozi-pkg remove APP             delete the box and its menu entries

System changes go through the privileged helper (helper.py) with pkexec, after
a snapshot.
"""
import argparse
import json
import os
import subprocess
import sys

import shutil
import time

from . import archives, aur, box, paths, perms as permissions, risk
from .i18n import tr


class CliError(Exception):
    pass


# --- review ---------------------------------------------------------------

def review(facts, contained=False):
    """All findings for a package, worst first."""
    findings = []
    for name, text in sorted(facts.scripts.items()):
        findings += risk.scan_script(text, name, contained)
    findings += risk.scan_paths(facts.entries, contained)
    return risk.sort_findings(findings)


def format_review(facts, findings):
    lines = [
        "%s %s" % (facts.name, facts.version),
        "  " + tr("Type: {kind}", kind=facts.kind),
        "  SHA-256: " + facts.sha256,
    ]
    if facts.description:
        lines.append("  " + facts.description.splitlines()[0])
    if facts.maintainer:
        lines.append("  " + tr("Maintainer: {who}", who=facts.maintainer))
    if facts.kind == "arch":
        lines.append("  " + (tr("Signature file found") if facts.signed else tr("No signature file next to the package")))
    lines.append("")
    if not findings:
        lines.append(tr("Nothing known-bad was found."))
    for finding in findings:
        lines.append("[%s] %s" % (finding.severity, finding.title))
        if finding.detail:
            lines.append("    " + finding.detail)
        if finding.evidence:
            lines.append("    %s: %s" % (finding.where, finding.evidence))
    for note in facts.notes:
        lines.append(tr("Note: {text}", text=note))
    lines.append("")
    lines.append(tr("This is a check for known bad patterns. A package that passes can still be harmful."))
    return "\n".join(lines)


# --- permissions flags ----------------------------------------------------

BOOL_FLAGS = ("network", "gpu", "sound", "camera", "devices", "x11", "nested_sandbox")


def add_permission_flags(parser):
    for name in BOOL_FLAGS:
        parser.add_argument("--" + name.replace("_", "-"), dest=name, action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--files", choices=permissions.FILE_MODES)
    parser.add_argument("--folder", action="append", default=None, metavar="DIR",
                        help="a folder the app may use (implies --files chosen)")


def apply_flags(perms, args):
    for name in BOOL_FLAGS:
        value = getattr(args, name, None)
        if value is not None:
            setattr(perms, name, value)
    if args.folder:
        perms.folders = permissions.clean_folders(perms.folders + args.folder)
        if not args.files:
            perms.files = "chosen"
    if args.files:
        perms.files = args.files
    return perms


def print_permissions(perms, out=print):
    for name, state in permissions.describe(perms):
        out("  %-30s %s" % (name, state))


# --- the privileged helper ------------------------------------------------

def call_helper(verb, args, out=print, runner=subprocess.Popen, snapshot=True):
    """Run one helper verb through pkexec; print its output. Returns the exit status."""
    def once(parts):
        try:
            proc = runner(["pkexec", paths.HELPER] + parts, stdout=subprocess.PIPE, text=True)
        except FileNotFoundError:
            raise CliError(tr("pkexec is not installed.")) from None
        status = 1
        for raw in proc.stdout:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            kind = event.get("event")
            if kind == "output":
                out(event.get("line", ""))
            elif kind == "error":
                out("ozi-pkg: " + event.get("message", ""))
            elif kind == "done":
                status = event.get("status", 1)
        proc.wait()
        return status
    if snapshot and verb in ("install-repo", "install-file", "remove", "upgrade"):
        once(["snapshot", "ozi-pkg " + verb])       # a failed snapshot must not block the change
    return once([verb] + list(args))


def ensure_subids(out=print, caller=call_helper, check=box.has_subids):
    """Boxes need a sub-id range for the user; ask the helper for one if it is missing."""
    if check():
        return
    out(tr("Setting up the user ids that boxes need..."))
    if caller("subids", [], out=out, snapshot=False) or not check():
        raise CliError(tr("Could not set up the user ids that boxes need."))


def install_arch(path, out=print, ask=input, yes=False, force=False, caller=call_helper):
    """Install a reviewed Arch package on the host through the helper."""
    path = os.path.abspath(path)
    try:
        facts = archives.inspect(path)
    except (OSError, archives.ArchiveError) as err:
        raise CliError(tr("Cannot read {path}: {err}", path=path, err=err)) from None
    if facts.kind != "arch":
        raise CliError(tr("This is not an Arch package."))
    findings = review(facts, contained=False)
    out(format_review(facts, findings))
    if risk.verdict(findings) == "danger" and not force:
        raise CliError(tr("The review found something dangerous. Use --force to install anyway."))
    out("")
    out(tr("This installs {name} on the system itself, with full rights.", name=facts.name))
    if not yes and ask(tr("Install {app}? [y/N] ", app=facts.name)).strip().lower() not in ("y", "yes", "e", "evet"):
        raise CliError(tr("Cancelled."))
    status = caller("install-file", [path, facts.sha256], out=out)
    if status:
        raise CliError(tr("The install failed."))
    return facts.name


def pacman_has(name):
    """True when a repository (or an installed package) provides `name`."""
    for flags in ("-Si", "-Qi", "-Sp"):
        try:
            if subprocess.run(["pacman", flags, "--", name], capture_output=True, timeout=60).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def install_aur(names, out=print, ask=input, yes=False, force=False, fetch=aur.default_fetch, runner=box.run,
                caller=call_helper, in_repo=pacman_has, workdir=None, now=None, driver=None, ensure=ensure_subids):
    """Review, build in a box and install AUR packages. Returns the installed file names."""
    now = time.time() if now is None else now
    order = aur.resolve(names, fetch, in_repo)
    if not order:
        raise CliError(tr("Everything asked for is already in the repositories. Use: ozi-pkg get"))
    recipes, worst = {}, "normal"
    for record in order:
        base = record["PackageBase"]
        files = aur.fetch_recipe(base, fetch)
        findings = aur.review_recipe(files, record, now)
        recipes[base] = files
        out("== %s %s (AUR)" % (record["Name"], record.get("Version", "")))
        if not findings:
            out(tr("Nothing known-bad was found."))
        for finding in findings:
            out("[%s] %s" % (finding.severity, finding.title))
            if finding.evidence:
                out("    %s: %s" % (finding.where, finding.evidence))
        if risk.verdict(findings) == "danger":
            worst = "danger"
    if worst == "danger" and not force:
        raise CliError(tr("The review found something dangerous. Use --force to build anyway."))
    out("")
    out(tr("The recipes run in a throwaway container. The built packages are then installed on the system with full rights."))
    if not yes and ask(tr("Build and install {n} package(s)? [y/N] ", n=len(order))).strip().lower() not in ("y", "yes", "e", "evet"):
        raise CliError(tr("Cancelled."))

    ensure(out)
    root = workdir or str(paths.state_dir() / "aur")
    deps = os.path.join(root, "deps")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(deps, exist_ok=True)
    driver = driver or box.storage_driver()
    installed, done = [], set()
    for record in order:
        base = record["PackageBase"]
        if base in done:
            continue
        done.add(base)
        build_dir = os.path.join(root, base)
        os.makedirs(build_dir)
        for name, text in recipes[base].items():
            with open(os.path.join(build_dir, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        out(tr("Building {name}...", name=record["Name"]))
        built = runner(aur.build_command(build_dir, deps if os.listdir(deps) else None, driver=driver))
        if built.returncode != 0:
            raise CliError(tr("The build of {name} failed.", name=record["Name"]))
        packages = [p for p in aur.built_packages(build_dir) if "-debug-" not in os.path.basename(p)]
        if not packages:
            raise CliError(tr("The build of {name} produced no package.", name=record["Name"]))
        for package in packages:
            shutil.copy(package, deps)
            status = caller("install-file", [package, archives.sha256_file(package)], out=out)
            if status:
                raise CliError(tr("Installing {name} failed.", name=os.path.basename(package)))
            installed.append(os.path.basename(package))
    shutil.rmtree(root, ignore_errors=True)
    return installed


# --- install --------------------------------------------------------------

def applications_dir():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "applications")


def install_deb(path, perms, runner=box.run, ask=input, out=print, yes=False, force=False, driver=None, ensure=ensure_subids):
    """Install a .deb into a new box. Returns the app id."""
    path = os.path.abspath(path)
    try:
        facts = archives.inspect(path)
    except (OSError, archives.ArchiveError) as err:
        raise CliError(tr("Cannot read {path}: {err}", path=path, err=err)) from None
    if facts.kind != "deb":
        raise CliError(tr("Only .deb packages can be installed into a box."))
    findings = review(facts, contained=True)
    verdict = risk.verdict(findings)
    out(format_review(facts, findings))
    out("")
    out(tr("The app would get these rights:"))
    print_permissions(perms, out)
    if verdict == "danger" and not force:
        raise CliError(tr("The review found something dangerous. Use --force to install anyway."))
    app_id = box.app_id_for(facts.name)
    if app_id in box.installed():
        raise CliError(tr("{app} is already installed. Remove it first.", app=app_id))
    if not yes and ask(tr("Install {app} into its own box? [y/N] ", app=app_id)).strip().lower() not in ("y", "yes", "e", "evet"):
        raise CliError(tr("Cancelled."))

    ensure(out)
    driver = driver or box.storage_driver()
    image = box.image_name(app_id)
    container = "ozi-build-" + app_id
    out(tr("Building the box (this downloads the dependencies)..."))
    built = runner(box.build_command(path, app_id, driver=driver))
    if built.returncode != 0:
        runner(box.podman(driver) + ["rm", "-f", container], capture_output=True)
        raise CliError(tr("The install inside the box failed."))
    committed = runner(box.podman(driver) + ["commit", container, image], capture_output=True)
    runner(box.podman(driver) + ["rm", "-f", container], capture_output=True)
    if committed.returncode != 0:
        raise CliError(tr("Could not save the box image."))

    command, entries = [facts.name], []
    os.makedirs(applications_dir(), exist_ok=True)
    for desktop in facts.desktop_files:
        got = runner(box.podman(driver) + ["run", "--rm", "--network", "none", image, "cat", "/" + desktop],
                     capture_output=True, text=True)
        if got.returncode != 0 or not got.stdout:
            continue
        if not entries:
            command = box.desktop_exec(got.stdout) or command
        target = os.path.join(applications_dir(), "ozi-box-%s-%s" % (app_id, os.path.basename(desktop)))
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(box.host_desktop_entry(app_id, got.stdout))
        entries.append(target)
    permissions.save(app_id, perms)
    box.record(app_id, {"name": facts.name, "version": facts.version, "sha256": facts.sha256,
                        "exec": command, "desktop": entries})
    out(tr("Installed {app}. Start it from the menu or with: ozi-pkg run {app}", app=app_id))
    return app_id


def install_appimage(path, perms, out=print, ask=input, yes=False, force=False):
    """Keep an AppImage under OziOS's own data folder and give it a menu entry.

    It is never run here. Starting it goes through bubblewrap with `perms`.
    """
    path = os.path.abspath(path)
    try:
        facts = archives.inspect(path)
    except (OSError, archives.ArchiveError) as err:
        raise CliError(tr("Cannot read {path}: {err}", path=path, err=err)) from None
    if facts.kind != "appimage":
        raise CliError(tr("This is not an AppImage."))
    findings = review(facts, contained=True)
    out(format_review(facts, findings))
    out("")
    out(tr("The app would get these rights:"))
    print_permissions(perms, out)
    if risk.verdict(findings) == "danger" and not force:
        raise CliError(tr("The review found something dangerous. Use --force to install anyway."))
    app_id = box.app_id_for(facts.name)
    if app_id in box.installed():
        raise CliError(tr("{app} is already installed. Remove it first.", app=app_id))
    if not yes and ask(tr("Install {app} in a sandbox? [y/N] ", app=app_id)).strip().lower() not in ("y", "yes", "e", "evet"):
        raise CliError(tr("Cancelled."))

    target = box.appimage_path(app_id)
    os.makedirs(target.parent, exist_ok=True)
    shutil.copyfile(path, target)
    os.chmod(target, 0o755)
    if archives.sha256_file(str(target)) != facts.sha256:
        os.remove(target)
        raise CliError(tr("The file changed while it was being copied."))
    os.makedirs(applications_dir(), exist_ok=True)
    entry = os.path.join(applications_dir(), "ozi-box-%s.desktop" % app_id)
    base = "[Desktop Entry]\nType=Application\nName=%s\nIcon=application-x-executable\nCategories=Utility;\n" % facts.name
    with open(entry, "w", encoding="utf-8") as fh:
        fh.write(box.host_desktop_entry(app_id, base))
    permissions.save(app_id, perms)
    box.record(app_id, {"name": facts.name, "version": facts.version, "sha256": facts.sha256,
                        "kind": "appimage", "desktop": [entry]})
    out(tr("Installed {app}. Start it from the menu or with: ozi-pkg run {app}", app=app_id))
    return app_id


def remove_box(app_id, runner=box.run, out=print, driver=None):
    permissions.check_app_id(app_id)
    info = box.installed().get(app_id)
    if info is None:
        raise CliError(tr("{app} is not installed.", app=app_id))
    if info.get("kind") == "appimage":
        try:
            os.remove(box.appimage_path(app_id))
        except OSError:
            pass
    else:
        runner(box.podman(driver or box.storage_driver()) + ["rmi", "-f", box.image_name(app_id)], capture_output=True)
    for entry in info.get("desktop", []):
        try:
            os.remove(entry)
        except OSError:
            pass
    box.forget(app_id)
    try:
        os.remove(permissions.profile_path(app_id))
    except OSError:
        pass
    out(tr("Removed {app}. Its private home folder was kept: {home}", app=app_id, home=permissions.private_home(app_id)))


def run_box(app_id, extra, runner=box.run, driver=None, uid=None, gid=None):
    permissions.check_app_id(app_id)
    info = box.installed().get(app_id)
    if info is None:
        raise CliError(tr("{app} is not installed.", app=app_id))
    perms = permissions.load(app_id)
    os.makedirs(permissions.private_home(app_id), exist_ok=True)
    return runner(box.start_command(app_id, info, perms, extra, driver=driver, uid=uid, gid=gid)).returncode


# --- command line ---------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="ozi-pkg", description="Review and install software the careful way.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("review", help="show what is inside a package and what deserves a look")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("install", help="install a .deb into its own box")
    p.add_argument("file")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask")
    p.add_argument("--force", action="store_true", help="install even if the review found something dangerous")
    add_permission_flags(p)

    p = sub.add_parser("get", help="install packages from the Arch repositories")
    p.add_argument("names", nargs="+")

    p = sub.add_parser("uninstall", help="remove packages from the system")
    p.add_argument("names", nargs="+")

    p = sub.add_parser("aur", help="build packages from the AUR in a box and install them")
    p.add_argument("names", nargs="+")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask")
    p.add_argument("--force", action="store_true", help="build even if the review found something dangerous")

    p = sub.add_parser("search", help="search the AUR")
    p.add_argument("term")

    sub.add_parser("upgrade", help="update the whole system")

    p = sub.add_parser("undo", help="roll the system back to a snapshot")
    p.add_argument("number")

    sub.add_parser("list", help="installed boxes")

    p = sub.add_parser("perms", help="show or change what an app may reach")
    p.add_argument("app")
    add_permission_flags(p)

    p = sub.add_parser("run", help="start a boxed app")
    p.add_argument("app")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("remove", help="delete a box")
    p.add_argument("app")
    return parser


def main(argv=None, out=print):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "review":
            try:
                facts = archives.inspect(args.file)
            except (OSError, archives.ArchiveError) as err:
                raise CliError(tr("Cannot read {path}: {err}", path=args.file, err=err)) from None
            findings = review(facts, contained=facts.kind in ("deb", "appimage"))
            if args.json:
                out(json.dumps({"name": facts.name, "version": facts.version, "kind": facts.kind, "sha256": facts.sha256,
                                "verdict": risk.verdict(findings), "findings": [f.as_dict() for f in findings]}, indent=2))
            else:
                out(format_review(facts, findings))
            return 1 if risk.verdict(findings) == "danger" else 0
        if args.command == "install":
            if ".pkg.tar" in args.file.lower():
                install_arch(args.file, out=out, yes=args.yes, force=args.force)
            elif args.file.lower().endswith(".appimage"):
                install_appimage(args.file, apply_flags(permissions.Permissions(), args), out=out, yes=args.yes, force=args.force)
            else:
                install_deb(args.file, apply_flags(permissions.Permissions(), args), yes=args.yes, force=args.force, out=out)
        elif args.command == "aur":
            install_aur(args.names, out=out, yes=args.yes, force=args.force)
        elif args.command == "search":
            for record in aur.search(args.term)[:30]:
                out("%-32s %-14s %4d votes  %s" % (record["Name"], record.get("Version", ""), record.get("NumVotes", 0),
                                                   record.get("Description") or ""))
        elif args.command in ("get", "uninstall", "upgrade", "undo"):
            verb = {"get": "install-repo", "uninstall": "remove"}.get(args.command, args.command)
            rest = getattr(args, "names", None) or ([args.number] if args.command == "undo" else [])
            return call_helper(verb, rest, out=out)
        elif args.command == "list":
            boxes = box.installed()
            if not boxes:
                out(tr("No boxed apps installed."))
            for app_id, info in sorted(boxes.items()):
                out("%-28s %s" % (app_id, info.get("version", "")))
        elif args.command == "perms":
            permissions.check_app_id(args.app)
            if args.app not in box.installed():
                raise CliError(tr("{app} is not installed.", app=args.app))
            perms = apply_flags(permissions.load(args.app), args)
            if any(getattr(args, name) is not None for name in BOOL_FLAGS) or args.files or args.folder:
                permissions.save(args.app, perms)
            print_permissions(perms, out)
        elif args.command == "run":
            extra = args.args[1:] if args.args[:1] == ["--"] else args.args
            return run_box(args.app, extra)
        elif args.command == "remove":
            remove_box(args.app, out=out)
    except (CliError, box.BoxError, aur.AurError, ValueError) as err:
        print("ozi-pkg: %s" % err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
