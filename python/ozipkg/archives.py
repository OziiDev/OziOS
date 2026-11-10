"""Look inside package files without running or unpacking them.

Reads Debian packages (.deb), Arch packages (.pkg.tar.*) and AppImages. Only
metadata and file lists are read; nothing is extracted to disk and no script
is ever executed.
"""
import bz2
import gzip
import hashlib
import io
import lzma
import tarfile
from dataclasses import dataclass, field

try:                                   # Python 3.14 and later
    from compression import zstd
except ImportError:                    # pragma: no cover
    zstd = None

MAX_SCRIPT = 256 * 1024
MAX_ENTRIES = 200000


class ArchiveError(Exception):
    pass


class _Slice(io.RawIOBase):
    """A read-only window onto part of a file."""

    def __init__(self, fh, start, size):
        self.fh, self.start, self.size, self.pos = fh, start, size, 0

    def readable(self):
        return True

    def readinto(self, buffer):
        want = min(len(buffer), self.size - self.pos)
        if want <= 0:
            return 0
        self.fh.seek(self.start + self.pos)
        got = self.fh.readinto(memoryview(buffer)[:want])
        self.pos += got
        return got


def _decompress(stream, name):
    name = name.lower()
    if name.endswith(".xz"):
        return lzma.LZMAFile(stream)
    if name.endswith((".gz", ".tgz")):
        return gzip.GzipFile(fileobj=stream)
    if name.endswith(".bz2"):
        return bz2.BZ2File(stream)
    if name.endswith((".zst", ".zstd")):
        if zstd is None:
            raise ArchiveError("this Python cannot read zstd files")
        return zstd.ZstdFile(stream)
    return stream


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ar_members(fh):
    """Yield (name, offset, size) for every member of an ar archive."""
    if fh.read(8) != b"!<arch>\n":
        raise ArchiveError("not a Debian package")
    while True:
        header = fh.read(60)
        if len(header) < 60:
            return
        if header[58:60] != b"`\n":
            raise ArchiveError("damaged package header")
        name = header[:16].decode("ascii", "replace").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError:
            raise ArchiveError("damaged package header") from None
        offset = fh.tell()
        yield name, offset, size
        fh.seek(offset + size + (size & 1))


def parse_control(text):
    """Parse a Debian control file into a dict (first paragraph only)."""
    fields, last = {}, None
    for line in text.splitlines():
        if not line.strip():
            if fields:
                break
            continue
        if line[0] in " \t" and last:
            fields[last] += "\n" + line.strip()
        elif ":" in line:
            last, _, value = line.partition(":")
            fields[last] = value.strip()
    return fields


@dataclass
class PackageFacts:
    kind: str                         # "deb" | "arch" | "appimage"
    path: str
    sha256: str
    name: str = ""
    version: str = ""
    arch: str = ""
    description: str = ""
    maintainer: str = ""
    homepage: str = ""
    size_installed: int = 0
    depends: list = field(default_factory=list)
    scripts: dict = field(default_factory=dict)       # script name -> text
    entries: list = field(default_factory=list)       # (path, mode, is_file)
    desktop_files: list = field(default_factory=list)
    signed: bool = False
    notes: list = field(default_factory=list)


def _read_tar_scripts(stream, facts, script_names):
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for member in tar:
            base = member.name.lstrip("./")
            if base == "control":
                data = tar.extractfile(member).read(MAX_SCRIPT)
                control = parse_control(data.decode("utf-8", "replace"))
                facts.name = control.get("Package", "")
                facts.version = control.get("Version", "")
                facts.arch = control.get("Architecture", "")
                facts.description = control.get("Description", "").split("\n")[0]
                facts.maintainer = control.get("Maintainer", "")
                facts.homepage = control.get("Homepage", "")
                try:
                    facts.size_installed = int(control.get("Installed-Size", "0")) * 1024
                except ValueError:
                    pass
                depends = control.get("Depends", "")
                facts.depends = [d.strip().split(" ")[0] for d in depends.split(",") if d.strip()]
            elif base in script_names:
                facts.scripts[base] = tar.extractfile(member).read(MAX_SCRIPT).decode("utf-8", "replace")


def inspect_deb(path):
    facts = PackageFacts("deb", path, sha256_file(path))
    with open(path, "rb") as fh:
        for name, offset, size in ar_members(fh):
            if name.startswith("control.tar"):
                _read_tar_scripts(_decompress(_Slice(fh, offset, size), name), facts,
                                  {"preinst", "postinst", "prerm", "postrm"})
            elif name.startswith("data.tar"):
                stream = _decompress(_Slice(fh, offset, size), name)
                with tarfile.open(fileobj=stream, mode="r|") as tar:
                    for member in tar:
                        if len(facts.entries) >= MAX_ENTRIES:
                            facts.notes.append("file list cut after %d entries" % MAX_ENTRIES)
                            break
                        facts.entries.append((member.name, member.mode, member.isfile()))
                        clean = member.name.lstrip("./")
                        if member.isfile() and clean.startswith("usr/share/applications/") and clean.endswith(".desktop"):
                            facts.desktop_files.append(clean)
    if not facts.name:
        raise ArchiveError("the package has no control information")
    return facts


def parse_pkginfo(text):
    info = {}
    for line in text.splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        info.setdefault(key.strip(), []).append(value.strip())
    return info


def inspect_arch(path):
    facts = PackageFacts("arch", path, sha256_file(path))
    with open(path, "rb") as raw:
        stream = _decompress(raw, path)
        with tarfile.open(fileobj=stream, mode="r|") as tar:
            for member in tar:
                if len(facts.entries) >= MAX_ENTRIES:
                    facts.notes.append("file list cut after %d entries" % MAX_ENTRIES)
                    break
                if member.name == ".PKGINFO":
                    info = parse_pkginfo(tar.extractfile(member).read(MAX_SCRIPT).decode("utf-8", "replace"))
                    first = lambda key: (info.get(key) or [""])[0]
                    facts.name, facts.version, facts.arch = first("pkgname"), first("pkgver"), first("arch")
                    facts.description, facts.homepage = first("pkgdesc"), first("url")
                    facts.depends = [d.split("=")[0].split(">")[0].split("<")[0] for d in info.get("depend", [])]
                    try:
                        facts.size_installed = int(first("size") or 0)
                    except ValueError:
                        pass
                elif member.name == ".INSTALL":
                    facts.scripts[".INSTALL"] = tar.extractfile(member).read(MAX_SCRIPT).decode("utf-8", "replace")
                elif member.name.startswith("."):
                    continue
                else:
                    facts.entries.append((member.name, member.mode, member.isfile()))
                    if member.isfile() and member.name.startswith("usr/share/applications/") and member.name.endswith(".desktop"):
                        facts.desktop_files.append(member.name)
    import os
    facts.signed = os.path.exists(path + ".sig")
    if not facts.name:
        raise ArchiveError("the package has no .PKGINFO")
    return facts


def inspect_appimage(path):
    """AppImages are programs; they are never run to inspect them."""
    facts = PackageFacts("appimage", path, sha256_file(path))
    import os
    facts.name = os.path.basename(path).rsplit(".", 1)[0]
    facts.notes.append("AppImage contents are not inspected; run it only in a sandbox")
    return facts


def inspect(path):
    lower = path.lower()
    if lower.endswith(".deb"):
        return inspect_deb(path)
    if ".pkg.tar" in lower:
        return inspect_arch(path)
    if lower.endswith(".appimage"):
        return inspect_appimage(path)
    raise ArchiveError("unknown package type")
