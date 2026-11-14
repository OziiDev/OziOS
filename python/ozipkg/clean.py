"""`ozi clean`: free disk space without touching anything that matters.

Without arguments it only shows what could be freed. With `--yes` it does it:
old package versions (the two newest of each are kept), journal entries older
than two weeks, packages nothing needs any more, and caches that rebuild
themselves (thumbnails, shader caches, the trash). The parts that need
administrator rights go through the privileged helper.
"""
import os
import re
import shutil

from . import cli, doctor
from .i18n import tr

# Folders under the home directory whose contents are rebuilt when needed.
USER_CACHES = (".cache/thumbnails", ".cache/mesa_shader_cache", ".cache/nvidia/GLCache", ".cache/fontconfig",
               ".local/share/Trash/files", ".local/share/Trash/info")


def dir_size(path, limit=2000000):
    """Bytes under a directory, without following links. Stops counting after `limit` entries."""
    total = seen = 0
    stack = [path]
    while stack and seen < limit:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    seen += 1
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def parse_size(text):
    """Bytes from '1.55 GiB', '300 MiB', '1.2G' and similar."""
    match = re.search(r"([\d.,]+)\s*([KMGT]?)(?:i?B)?", text or "")
    if not match:
        return 0
    number = float(match.group(1).replace(",", "."))
    power = "KMGT".find(match.group(2)) + 1 if match.group(2) else 0
    return int(number * 1024 ** power)


def paccache_saving(output):
    """Bytes a dry run of paccache says it would free."""
    match = re.search(r"disk space saved:\s*([\d.,]+\s*[KMGT]i?B)", output or "")
    return parse_size(match.group(1)) if match else 0


def survey(probe=None, home=None):
    """What could be freed: a list of dicts with id, title, bytes and detail."""
    probe = probe or doctor.Probe()
    home = home or os.path.expanduser("~")
    items = []

    saved = 0
    for flags in (["-dk2"], ["-duk0"]):
        code, text = probe.run(["paccache"] + flags)
        if code == 0:
            saved += paccache_saving(text)
    items.append({"id": "cache", "title": tr("Old package versions"), "bytes": saved,
                  "detail": "" if probe.which("paccache") else tr("paccache is not installed (package pacman-contrib)")})

    code, text = probe.run(["journalctl", "--disk-usage"])
    items.append({"id": "journal", "title": tr("System journal"), "bytes": parse_size(text) if code == 0 else 0,
                  "detail": tr("Entries older than two weeks are dropped.")})

    code, text = probe.run(["pacman", "-Qdtq"])
    names = [line.strip() for line in text.splitlines() if line.strip()] if code == 0 else []
    items.append({"id": "orphans", "title": tr("Packages nothing needs any more"), "bytes": 0,
                  "detail": ", ".join(names[:8]) + (" ..." if len(names) > 8 else ""), "count": len(names)})

    size = sum(dir_size(os.path.join(home, rel)) for rel in USER_CACHES)
    items.append({"id": "user", "title": tr("Caches and the trash in your home folder"), "bytes": size, "detail": ""})
    return items


def clear_user_caches(home, remove=shutil.rmtree):
    """Empty the folders in USER_CACHES. Returns how many entries were removed."""
    count = 0
    for rel in USER_CACHES:
        base = os.path.join(home, rel)
        try:
            names = os.listdir(base)
        except OSError:
            continue
        for name in names:
            path = os.path.join(base, name)
            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    remove(path)
                else:
                    os.remove(path)
                count += 1
            except OSError:
                continue
    return count


def format_survey(items):
    lines = []
    for item in items:
        size = doctor.human_size(item["bytes"]) if item["bytes"] else "-"
        count = " (%d)" % item["count"] if item.get("count") else ""
        lines.append("%-42s %10s%s" % (item["title"], size, count))
        if item["detail"]:
            lines.append("    " + item["detail"])
    return "\n".join(lines)


def main(argv=None, out=print, probe=None, home=None, caller=cli.call_helper):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi clean", description=tr("Free disk space. Shows what could be freed unless --yes is given."))
    parser.add_argument("--yes", "-y", action="store_true", help=tr("do it"))
    parser.add_argument("--only", help=tr("only these, separated by commas: cache, journal, orphans, user"))
    args = parser.parse_args(argv)
    wanted = {part.strip() for part in (args.only or "cache,journal,orphans,user").split(",") if part.strip()}
    unknown = wanted - {"cache", "journal", "orphans", "user"}
    if unknown:
        parser.error(tr("unknown item: {names}", names=", ".join(sorted(unknown))))
    home = home or os.path.expanduser("~")

    items = [item for item in survey(probe, home) if item["id"] in wanted]
    out(format_survey(items))
    if not args.yes:
        out("")
        out(tr("Run `ozi clean --yes` to do this."))
        return 0

    status = 0
    for verb, key in (("clean-cache", "cache"), ("clean-journal", "journal"), ("clean-orphans", "orphans")):
        if key in wanted:
            out("")
            out(tr("Working on: {what}", what=key))
            code = caller(verb, [], out=out, snapshot=False)
            status = status or code
    if "user" in wanted:
        out(tr("Removed {n} entries from your caches and trash.", n=clear_user_caches(home)))
    return 1 if status else 0
