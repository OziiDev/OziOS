import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.dirname(__file__))

from ozipkg import box, perms, service  # noqa: E402
from test_archives import build_deb  # noqa: E402
from test_cli import FakeRunner  # noqa: E402


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = {k: os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME")}
        os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "config")
        os.environ["XDG_DATA_HOME"] = os.path.join(self.tmp.name, "data")
        self.deb = os.path.join(self.tmp.name, "demo.deb")

    def tearDown(self):
        for key, value in self.old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()


class Review(Fixtures):
    def test_result_is_json_ready(self):
        build_deb(self.deb, scripts={"postinst": "#!/bin/sh\nsystemctl enable demo\n"})
        result = service.review_file(self.deb)
        json.dumps(result)
        self.assertEqual((result["name"], result["kind"], result["boxed"], result["installable"]), ("demo-app", "deb", True, True))
        self.assertEqual(result["permissions"]["network"], False)
        self.assertTrue(result["permission_rows"])

    def test_unreadable_file_becomes_a_service_error(self):
        with open(self.deb, "wb") as fh:
            fh.write(b"junk")
        with self.assertRaises(service.ServiceError):
            service.review_file(self.deb)
        with self.assertRaises(service.ServiceError):
            service.review_file(os.path.join(self.tmp.name, "missing.deb"))


class Apps(Fixtures):
    def install(self):
        build_deb(self.deb)
        with mock.patch.object(box, "run", FakeRunner()), mock.patch.object(box, "storage_driver", lambda *a: "vfs"):
            return service.install_file(self.deb, {"network": True, "files": "chosen", "folders": ["/home/u/Docs", "/etc"]})

    def test_install_list_change_remove(self):
        self.assertEqual(self.install(), {"app": "demo-app"})
        apps = service.list_apps()
        self.assertEqual([a["id"] for a in apps], ["demo-app"])
        self.assertTrue(apps[0]["permissions"]["network"])
        self.assertEqual(apps[0]["permissions"]["folders"], ["/home/u/Docs"])      # /etc was refused
        changed = service.set_permissions("demo-app", {"network": False, "camera": True})
        self.assertEqual((changed["permissions"]["network"], changed["permissions"]["camera"]), (False, True))
        with mock.patch.object(box, "run", FakeRunner()), mock.patch.object(box, "storage_driver", lambda *a: "vfs"):
            service.remove_app("demo-app")
        self.assertEqual(service.list_apps(), [])

    def test_unknown_app_and_bad_id(self):
        for call in (lambda: service.set_permissions("nothing", {}), lambda: service.set_permissions("../x", {}),
                     lambda: service.remove_app("nothing")):
            with self.assertRaises(service.ServiceError):
                call()

    def test_wrong_file_type(self):
        path = os.path.join(self.tmp.name, "notes.txt")
        with open(path, "w") as fh:
            fh.write("x")
        with self.assertRaises(service.ServiceError):
            service.install_file(path)


class Search(unittest.TestCase):
    OUTPUT = ("extra/vlc 3.0.21-1 [installed]\n    Multi-platform MPEG, VCD/DVD, and DivX player\n"
              "extra/vlc-plugins-all 3.0.21-1\n    Metapackage\n")

    def test_parses_pacman_output(self):
        with mock.patch("subprocess.run", return_value=SimpleNamespace(stdout=self.OUTPUT)):
            result = service.search_repos("vlc")
        self.assertEqual([r["name"] for r in result], ["vlc", "vlc-plugins-all"])
        self.assertTrue(result[0]["installed"])
        self.assertFalse(result[1]["installed"])
        self.assertIn("player", result[0]["description"])

    def test_options_and_blank_terms_are_never_passed_on(self):
        with mock.patch("subprocess.run") as run:
            self.assertEqual(service.search_repos("--help"), [])
            self.assertEqual(service.search_repos("  "), [])
        run.assert_not_called()

    def test_missing_pacman_gives_an_empty_list(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(service.search_repos("vlc"), [])

    def test_aur_results_are_trimmed(self):
        record = {"Name": "demo", "Version": "1-1", "NumVotes": 9, "Description": None, "Maintainer": None, "Extra": 1}
        with mock.patch("ozipkg.aur.search", return_value=[record]):
            self.assertEqual(service.search_aur("demo"),
                             [{"name": "demo", "version": "1-1", "votes": 9, "description": "", "maintainer": ""}])


if __name__ == "__main__":
    unittest.main()
