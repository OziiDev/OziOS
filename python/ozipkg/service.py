"""What the graphical apps call: plain data in, plain data out, no Qt.

Every function returns dicts, lists and strings that can be turned into JSON,
and raises ServiceError with a message fit to show to a person. The apps run
these in a worker thread and pass the text lines a function produces to the
screen as they arrive (`log`).
"""
import os

from . import archives, aur, box, cli, perms as permissions, risk
from .i18n import tr


class ServiceError(Exception):
    pass


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (cli.CliError, box.BoxError, aur.AurError, archives.ArchiveError, ValueError, OSError) as err:
        raise ServiceError(str(err)) from None


def review_file(path):
    """Everything the review screen shows for a package file."""
    def work():
        facts = archives.inspect(path)
        contained = facts.kind == "deb"
        findings = cli.review(facts, contained=contained)
        default = permissions.Permissions()
        return {
            "name": facts.name, "version": facts.version, "kind": facts.kind, "sha256": facts.sha256,
            "description": facts.description.splitlines()[0] if facts.description else "",
            "maintainer": facts.maintainer, "signed": facts.signed, "notes": facts.notes,
            "verdict": risk.verdict(findings),
            "findings": [f.as_dict() for f in findings],
            "boxed": contained,
            "installable": facts.kind in ("deb", "arch"),
            "permissions": default.as_dict(),
            "permission_rows": permissions.describe(default),
        }
    return _guard(work)


def install_file(path, permission_values=None, force=False, log=lambda line: None):
    """Install a reviewed file. Boxed for .deb, on the system for Arch packages."""
    def work():
        lower = path.lower()
        if lower.endswith(".deb"):
            perms = permissions.from_dict(permission_values or {})
            return {"app": cli.install_deb(path, perms, runner=box.run, out=log, yes=True, force=force)}
        if ".pkg.tar" in lower:
            return {"app": cli.install_arch(path, out=log, yes=True, force=force)}
        raise cli.CliError(tr("This kind of file cannot be installed yet."))
    return _guard(work)


def list_apps():
    """Boxed apps with their current permissions."""
    apps = []
    for app_id, info in sorted(box.installed().items()):
        perms = permissions.load(app_id)
        apps.append({"id": app_id, "name": info.get("name", app_id), "version": info.get("version", ""),
                     "permissions": perms.as_dict(), "permission_rows": permissions.describe(perms)})
    return apps


def set_permissions(app_id, values):
    def work():
        permissions.check_app_id(app_id)
        if app_id not in box.installed():
            raise cli.CliError(tr("{app} is not installed.", app=app_id))
        perms = permissions.from_dict(values)
        permissions.save(app_id, perms)
        return {"permissions": perms.as_dict(), "permission_rows": permissions.describe(perms)}
    return _guard(work)


def remove_app(app_id, log=lambda line: None):
    return _guard(cli.remove_box, app_id, runner=box.run, out=log)


def run_app(app_id):
    """Start a boxed app without waiting for it. Returns the process id."""
    def work():
        import subprocess
        info = box.installed().get(app_id)
        if info is None:
            raise cli.CliError(tr("{app} is not installed.", app=app_id))
        perms = permissions.load(app_id)
        os.makedirs(permissions.private_home(app_id), exist_ok=True)
        argv = list(info.get("exec") or [info.get("name", app_id)])
        return {"pid": subprocess.Popen(box.run_command(app_id, perms, argv)).pid}
    return _guard(work)


def search_repos(term):
    """Repository packages matching `term` (name and description), as dicts."""
    def work():
        import subprocess
        if not term.strip() or term.startswith("-"):
            return []
        try:
            done = subprocess.run(["pacman", "-Ss", "--", term], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return []
        results, current = [], None
        for line in done.stdout.splitlines():
            if line.startswith(" "):
                if current:
                    current["description"] = line.strip()
                continue
            head = line.split()
            if len(head) >= 2 and "/" in head[0]:
                repo, name = head[0].split("/", 1)
                current = {"repo": repo, "name": name, "version": head[1], "description": "",
                           "installed": "[installed" in line}
                results.append(current)
        return results[:40]
    return _guard(work)


def search_aur(term):
    def work():
        return [{"name": r["Name"], "version": r.get("Version", ""), "votes": r.get("NumVotes", 0),
                 "description": r.get("Description") or "", "maintainer": r.get("Maintainer") or ""}
                for r in aur.search(term)[:40]]
    return _guard(work)


def install_repo(names, log=lambda line: None):
    def work():
        status = cli.call_helper("install-repo", names, out=log)
        if status:
            raise cli.CliError(tr("The install failed."))
        return {"installed": list(names)}
    return _guard(work)


def install_from_aur(names, force=False, log=lambda line: None):
    def work():
        return {"installed": cli.install_aur(names, out=log, yes=True, force=force)}
    return _guard(work)


def system_update(log=lambda line: None):
    def work():
        status = cli.call_helper("upgrade", [], out=log)
        if status:
            raise cli.CliError(tr("The install failed."))
        return {"updated": True}
    return _guard(work)
