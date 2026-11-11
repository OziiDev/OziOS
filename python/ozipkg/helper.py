"""The privileged helper: the only code in OziOS that runs as root.

It is started through pkexec (polkit action org.ozios.pkg.manage) and knows a
fixed set of verbs. Nothing a caller passes is ever handed to a shell: every
argument is checked against a strict pattern and turned into a fixed command
line. A package file is first copied into a directory only root can write,
and the copy's SHA-256 must equal the one the user was shown in the review,
so the file cannot change between review and install.

Output is one JSON object per line.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

STAGING = "/var/lib/ozios/staging"
MAX_FILE = 4 * 1024 ** 3
SAFE_ENV = {"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C", "LANG": "C"}

NAME = re.compile(r"^[a-z0-9@._+][a-z0-9@._+-]{0,99}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PKGFILE = re.compile(r"^[^\0]+\.pkg\.tar\.(zst|xz|gz|bz2|lz4)$")
NUMBER = re.compile(r"^[0-9]{1,9}$")
VERBS = ("install-repo", "install-file", "remove", "upgrade", "snapshot", "undo", "subids")
USERNAME = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
SUBID_FILES = ("/etc/subuid", "/etc/subgid")
SUBID_FIRST, SUBID_COUNT = 100000, 65536


class HelperError(Exception):
    pass


def check_names(names):
    if not names:
        raise HelperError("no package names given")
    for name in names:
        if not NAME.match(name):
            raise HelperError("invalid package name: %r" % (name,))
    return list(names)


def clean_description(text):
    text = "".join(ch for ch in (text or "ozi") if ch.isprintable())[:80].strip()
    return text.lstrip("-") or "ozi"


def stage_file(source, expected, staging=STAGING):
    """Copy `source` into the private directory; return the copy's path.

    The copy is read exactly once while being written, so the digest is that
    of the bytes pacman will see. A mismatch removes the copy.
    """
    if not SHA256.match(expected or ""):
        raise HelperError("the expected SHA-256 is not valid")
    if not os.path.isabs(source) or not PKGFILE.match(source):
        raise HelperError("not an absolute path to a package file")
    os.makedirs(staging, mode=0o700, exist_ok=True)
    os.chmod(staging, 0o700)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(source, flags)
    except OSError as err:
        raise HelperError("cannot open the package: %s" % err.strerror) from None
    digest = hashlib.sha256()
    target = os.path.join(staging, expected + source[source.rindex(".pkg.tar"):])
    size = 0
    try:
        with os.fdopen(fd, "rb") as src:
            info = os.fstat(src.fileno())
            if not os.path.isfile(source) or info.st_size > MAX_FILE:
                raise HelperError("not a regular file or too large")
            out_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)
            with os.fdopen(out_fd, "wb") as dst:
                for block in iter(lambda: src.read(1 << 20), b""):
                    size += len(block)
                    if size > MAX_FILE:
                        raise HelperError("package is too large")
                    digest.update(block)
                    dst.write(block)
    except BaseException:
        _remove(target)
        raise
    if digest.hexdigest() != expected:
        _remove(target)
        raise HelperError("the package changed since it was reviewed (SHA-256 differs)")
    return target


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def grant_subids(uid, files=SUBID_FILES, lookup=None):
    """Give the user that called pkexec a range of sub-ids, if they have none.

    Rootless containers need one to map more than a single user. The user is
    taken from PKEXEC_UID, never from an argument, and only ordinary accounts
    qualify. Returns True when a range was added.
    """
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        raise HelperError("sub-ids can only be granted through pkexec") from None
    if not 1000 <= uid < 60000:
        raise HelperError("sub-ids are only granted to ordinary user accounts")
    if lookup is None:
        import pwd
        lookup = pwd.getpwuid
    try:
        name = lookup(uid).pw_name
    except KeyError:
        raise HelperError("no such user") from None
    if not USERNAME.match(name):
        raise HelperError("unusual user name %r" % (name,))
    added = False
    for path in files:
        taken, top = False, SUBID_FIRST
        try:
            with open(path, encoding="ascii", errors="replace") as fh:
                for line in fh:
                    parts = line.strip().split(":")
                    if len(parts) != 3 or not (parts[1].isdigit() and parts[2].isdigit()):
                        continue
                    taken = taken or parts[0] in (name, str(uid))
                    top = max(top, int(parts[1]) + int(parts[2]))
        except FileNotFoundError:
            pass
        if not taken:
            with open(path, "a", encoding="ascii") as fh:
                fh.write("%s:%d:%d\n" % (name, top, SUBID_COUNT))
            added = True
    return added


def plan(argv, staging=STAGING, stage=stage_file):
    """Turn a verb and its arguments into (commands, cleanup_paths).

    Raises HelperError for anything outside the fixed set.
    """
    if not argv or argv[0] not in VERBS:
        raise HelperError("unknown verb; expected one of: " + ", ".join(VERBS))
    verb, args = argv[0], argv[1:]
    if verb == "subids":
        if args:
            raise HelperError("subids takes no arguments")
        return [], []                      # done by main(), which knows who called
    if verb == "install-repo":
        return [["pacman", "-S", "--needed", "--noconfirm", "--"] + check_names(args)], []
    if verb == "remove":
        return [["pacman", "-Rns", "--noconfirm", "--"] + check_names(args)], []
    if verb == "install-file":
        if len(args) != 2:
            raise HelperError("install-file needs a path and a SHA-256")
        copy = stage(args[0], args[1], staging)
        return [["pacman", "-U", "--noconfirm", "--", copy]], [copy]
    if verb == "upgrade":
        if args:
            raise HelperError("upgrade takes no arguments")
        return [["pacman", "-Syu", "--noconfirm"]], []
    if verb == "snapshot":
        return [["snapper", "-c", "root", "create", "-d", clean_description(" ".join(args))]], []
    if verb == "undo":
        if len(args) != 1 or not NUMBER.match(args[0]):
            raise HelperError("undo needs a snapshot number")
        return [["snapper", "-c", "root", "undochange", "%s..0" % args[0]]], []
    raise HelperError("unhandled verb")


def emit(obj, out):
    out.write(json.dumps(obj) + "\n")
    out.flush()


def run_streaming(cmd, out):
    """Run a command with the fixed environment, one JSON line per output line."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                env=SAFE_ENV, stdin=subprocess.DEVNULL, errors="replace")
    except FileNotFoundError:
        emit({"event": "error", "message": "%s is not installed" % cmd[0]}, out)
        return 127
    for line in proc.stdout:
        emit({"event": "output", "line": line.rstrip("\n")}, out)
    return proc.wait()


def main(argv=None, out=None, runner=run_streaming, geteuid=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = out or sys.stdout
    geteuid = geteuid or getattr(os, "geteuid", lambda: 0)
    if geteuid() != 0:
        emit({"event": "error", "message": "must run as root, through pkexec"}, out)
        return 1
    cleanup = []
    try:
        commands, cleanup = plan(argv)
        emit({"event": "start", "verb": argv[0]}, out)
        if argv[0] == "subids":
            added = grant_subids(os.environ.get("PKEXEC_UID"))
            emit({"event": "output", "line": "sub-id range added" if added else "sub-id range already there"}, out)
        code = 0
        for cmd in commands:
            code = runner(cmd, out)
            if code:
                break
        emit({"event": "done", "status": code}, out)
        return code
    except HelperError as err:
        emit({"event": "error", "message": str(err)}, out)
        return 2
    finally:
        for path in cleanup:
            _remove(path)


if __name__ == "__main__":
    sys.exit(main())
