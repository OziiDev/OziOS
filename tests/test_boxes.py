import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import box, perms  # noqa: E402

ENV = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0", "LANG": "tr_TR.UTF-8"}
EXISTING = {"/run/user/1000/wayland-0", "/dev/dri", "/run/user/1000/pipewire-0", "/dev/video0", "/dev/bus/usb",
            "/etc/fonts", "/etc/resolv.conf", "/etc/ssl"}


def exists(path):
    return path in EXISTING


def pairs(cmd):
    """Group a command line into flag/value pairs for easy membership tests."""
    return [tuple(cmd[i:i + 2]) for i in range(len(cmd) - 1)]


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = {k: os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME")}
        os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "config")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.tmp.name, "data")

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()


class Permissions(Fixtures):
    def test_defaults_are_closed(self):
        p = perms.Permissions()
        self.assertFalse(p.network)
        self.assertEqual(p.files, "none")
        self.assertFalse(p.camera or p.devices or p.x11 or p.nested_sandbox)

    def test_from_untrusted_json(self):
        p = perms.from_dict({"network": "yes", "files": "everything", "folders": ["/", "/etc", "rel", "/home/u/Docs", 5],
                             "gpu": False, "evil": True})
        self.assertFalse(p.network)                      # not a bool: ignored
        self.assertEqual(p.files, "none")                # not a known mode: ignored
        self.assertEqual(p.folders, ["/home/u/Docs"])    # root, system and relative paths dropped
        self.assertFalse(p.gpu)
        self.assertFalse(hasattr(p, "evil"))

    def test_save_and_load(self):
        p = perms.Permissions(network=True, files="chosen", folders=["/home/u/Pictures"])
        perms.save("demo-app", p)
        self.assertEqual(perms.load("demo-app"), p)
        self.assertEqual(perms.load("never-saved"), perms.Permissions())

    def test_app_id_is_checked(self):
        for bad in ("../x", "a/b", "", "-x", "x y"):
            with self.assertRaises(ValueError):
                perms.check_app_id(bad)
        self.assertEqual(perms.check_app_id("google-chrome-stable"), "google-chrome-stable")

    def test_flatpak_overrides(self):
        closed = perms.flatpak_overrides(perms.Permissions())
        self.assertIn("--unshare=network", closed)
        self.assertIn("--nofilesystem=home", closed)
        opened = perms.flatpak_overrides(perms.Permissions(network=True, files="chosen", folders=["/home/u/X"], camera=True))
        self.assertIn("--share=network", opened)
        self.assertIn("--filesystem=/home/u/X", opened)
        self.assertIn("--device=all", opened)
        self.assertIn("--filesystem=home", perms.flatpak_overrides(perms.Permissions(files="home")))

    def test_describe(self):
        rows = dict(perms.describe(perms.Permissions(files="chosen", folders=["/a"])))
        self.assertEqual(rows["Files"], "/a")
        self.assertEqual(rows["Internet"], "Blocked")


class Bwrap(Fixtures):
    def test_closed_by_default(self):
        cmd = perms.bwrap_command("tool", perms.Permissions(), ["/opt/tool"], ENV, exists)
        self.assertIn("--unshare-all", cmd)
        self.assertNotIn("--share-net", cmd)
        self.assertIn(("--ro-bind", "/run/user/1000/wayland-0"), pairs(cmd))
        self.assertNotIn(("--setenv", "DISPLAY"), pairs(cmd))
        self.assertNotIn("/dev/video0", cmd)
        self.assertEqual(cmd[-2:], ["--", "/opt/tool"])

    def test_each_permission_adds_exactly_its_own_things(self):
        full = perms.Permissions(network=True, camera=True, devices=True, x11=True, files="chosen", folders=["/home/u/Docs"])
        cmd = perms.bwrap_command("tool", full, ["x"], ENV, exists)
        self.assertIn("--share-net", cmd)
        self.assertIn(("--dev-bind", "/dev/video0"), pairs(cmd))
        self.assertIn(("--dev-bind-try", "/dev/bus/usb"), pairs(cmd))
        self.assertIn(("--setenv", "DISPLAY"), pairs(cmd))
        self.assertIn(("--bind", "/home/u/Docs"), pairs(cmd))

    def test_home_is_private_unless_allowed(self):
        cmd = perms.bwrap_command("tool", perms.Permissions(), ["x"], ENV, exists)
        home = os.path.expanduser("~")
        binds = [c for c in pairs(cmd) if c[0] == "--bind"]
        self.assertFalse(any(b[1] == home for b in binds))
        cmd = perms.bwrap_command("tool", perms.Permissions(files="home"), ["x"], ENV, exists)
        self.assertTrue(any(c == ("--bind", home) for c in pairs(cmd)))


class Podman(Fixtures):
    def test_build_command_isolates(self):
        cmd = box.build_command("/tmp/x.deb", "demo", driver="vfs")
        self.assertEqual(cmd[:3], ["podman", "--storage-driver", "vfs"])
        self.assertIn("no-new-privileges", cmd)
        self.assertIn("/tmp/x.deb:/in/package.deb:ro", cmd)
        self.assertEqual(sum(1 for part in cmd if part == "-v"), 1)       # only the package, nothing else
        self.assertFalse(any(part.startswith("--device") for part in cmd))
        self.assertNotIn("--privileged", cmd)

    def test_run_closed(self):
        cmd = box.run_command("demo", perms.Permissions(), ["demo-app"], ENV, "vfs", exists, 1000, 1000)
        self.assertIn(("--network", "none"), pairs(cmd))
        self.assertIn(("--cap-drop", "all"), pairs(cmd))
        self.assertIn(("--user", "1000:1000"), pairs(cmd))
        self.assertNotIn("SYS_ADMIN", cmd)
        self.assertNotIn("/dev/video0", cmd)
        self.assertNotIn(("-e", "DISPLAY=:0"), pairs(cmd))
        self.assertEqual(cmd[-2:], ["localhost/ozi/demo", "demo-app"])
        volumes = [c[1] for c in pairs(cmd) if c[0] == "-v"]
        self.assertTrue(all(":/home/box" in v or "/run/user/1000" in v for v in volumes), volumes)

    def test_run_open(self):
        p = perms.Permissions(network=True, camera=True, devices=True, x11=True, nested_sandbox=True,
                              files="chosen", folders=["/home/u/Docs"])
        cmd = box.run_command("demo", p, ["demo-app"], ENV, "vfs", exists, 1000, 1000)
        self.assertIn(("--network", "pasta"), pairs(cmd))
        self.assertIn(("--device", "/dev/video0"), pairs(cmd))
        self.assertIn(("-e", "DISPLAY=:0"), pairs(cmd))
        self.assertIn(("--cap-add", "SYS_ADMIN"), pairs(cmd))
        self.assertIn(("-v", "/home/u/Docs:/home/u/Docs"), pairs(cmd))

    def test_desktop_helpers(self):
        text = "[Desktop Entry]\nName=Demo\nExec=/usr/bin/demo --new-window %U\nIcon=demo\nTryExec=/usr/bin/demo\n[Desktop Action x]\nExec=other\n"
        self.assertEqual(box.desktop_exec(text), ["/usr/bin/demo", "--new-window"])
        host = box.host_desktop_entry("demo", text)
        self.assertIn("Exec=ozi-box run demo", host)
        self.assertNotIn("TryExec", host)
        self.assertIn("Name=Demo", host)

    def test_app_id(self):
        self.assertEqual(box.app_id_for("Google Chrome_Stable"), "google-chrome-stable")
        with self.assertRaises(box.BoxError):
            box.app_id_for("###")

    def test_records(self):
        box.record("demo", {"version": "1"})
        self.assertEqual(box.installed(), {"demo": {"version": "1"}})
        box.forget("demo")
        self.assertEqual(box.installed(), {})


if __name__ == "__main__":
    unittest.main()
