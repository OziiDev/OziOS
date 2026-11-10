import io
import lzma
import gzip
import os
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import archives  # noqa: E402

try:
    from compression import zstd
except ImportError:
    zstd = None


def make_tar(files):
    """files: list of (name, bytes, mode). Returns tar bytes."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data, mode in files:
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def ar(members):
    out = b"!<arch>\n"
    for name, data in members:
        header = ("%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (name + "/", 0, 0, 0, "100644", len(data))).encode()
        out += header + data + (b"\n" if len(data) & 1 else b"")
    return out


CONTROL = (b"Package: demo-app\nVersion: 1.2-3\nArchitecture: amd64\nMaintainer: A Person <a@example.org>\n"
           b"Installed-Size: 42\nDepends: libc6 (>= 2.34), libgtk-3-0\nHomepage: https://example.org\n"
           b"Description: A demo\n and more text\n")


def build_deb(path, data_compression="xz", scripts=None):
    control = make_tar([("./control", CONTROL, 0o644)] +
                       [("./" + n, t.encode(), 0o755) for n, t in (scripts or {}).items()])
    data = make_tar([
        ("./usr/bin/demo", b"#!/bin/sh\n", 0o755),
        ("./usr/share/applications/demo.desktop", b"[Desktop Entry]\n", 0o644),
        ("./usr/lib/systemd/system/demo.service", b"[Service]\n", 0o644),
        ("./usr/bin/helper", b"x", 0o4755),
    ])
    if data_compression == "xz":
        packed, name = lzma.compress(data), "data.tar.xz"
    elif data_compression == "gz":
        packed, name = gzip.compress(data), "data.tar.gz"
    elif data_compression == "zst":
        packed, name = zstd.compress(data), "data.tar.zst"
    else:
        packed, name = data, "data.tar"
    with open(path, "wb") as fh:
        fh.write(ar([("debian-binary", b"2.0\n"), ("control.tar.gz", gzip.compress(control)), (name, packed)]))


class Deb(unittest.TestCase):
    def check(self, compression):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "demo.deb")
            build_deb(path, compression, {"postinst": "#!/bin/sh\nsystemctl enable demo\n"})
            facts = archives.inspect(path)
        self.assertEqual((facts.kind, facts.name, facts.version, facts.arch), ("deb", "demo-app", "1.2-3", "amd64"))
        self.assertEqual(facts.description, "A demo")
        self.assertEqual(facts.size_installed, 42 * 1024)
        self.assertEqual(facts.depends, ["libc6", "libgtk-3-0"])
        self.assertIn("systemctl enable demo", facts.scripts["postinst"])
        self.assertEqual([e[0] for e in facts.entries][:2], ["./usr/bin/demo", "./usr/share/applications/demo.desktop"])
        self.assertEqual(facts.desktop_files, ["usr/share/applications/demo.desktop"])
        self.assertEqual(len(facts.sha256), 64)

    def test_xz(self):
        self.check("xz")

    def test_gz(self):
        self.check("gz")

    def test_plain(self):
        self.check("none")

    @unittest.skipIf(zstd is None, "needs Python 3.14")
    def test_zst(self):
        self.check("zst")

    def test_not_a_deb(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.deb")
            with open(path, "wb") as fh:
                fh.write(b"hello")
            with self.assertRaises(archives.ArchiveError):
                archives.inspect(path)

    def test_unknown_type(self):
        with self.assertRaises(archives.ArchiveError):
            archives.inspect("/tmp/file.rpm")


@unittest.skipIf(zstd is None, "needs Python 3.14")
class Arch(unittest.TestCase):
    def test_pkg(self):
        info = (b"# Generated\npkgname = demo\npkgver = 1.0-1\narch = x86_64\npkgdesc = Demo tool\n"
                b"url = https://example.org\nsize = 1234\ndepend = glibc\ndepend = gtk3>=3.24\n")
        tar = make_tar([
            (".PKGINFO", info, 0o644),
            (".INSTALL", b"post_install() { systemctl enable demo; }\n", 0o644),
            ("usr/bin/demo", b"x", 0o755),
            ("usr/share/applications/demo.desktop", b"x", 0o644),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "demo-1.0-1-x86_64.pkg.tar.zst")
            with open(path, "wb") as fh:
                fh.write(zstd.compress(tar))
            facts = archives.inspect(path)
        self.assertEqual((facts.kind, facts.name, facts.version, facts.size_installed), ("arch", "demo", "1.0-1", 1234))
        self.assertEqual(facts.depends, ["glibc", "gtk3"])
        self.assertIn("systemctl", facts.scripts[".INSTALL"])
        self.assertEqual([e[0] for e in facts.entries], ["usr/bin/demo", "usr/share/applications/demo.desktop"])
        self.assertFalse(facts.signed)


class AppImage(unittest.TestCase):
    def test_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "Tool-1.0.AppImage")
            with open(path, "wb") as fh:
                fh.write(b"\x7fELF")
            facts = archives.inspect(path)
        self.assertEqual((facts.kind, facts.name), ("appimage", "Tool-1.0"))


if __name__ == "__main__":
    unittest.main()
