import json
import os
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import bridge  # noqa: E402


class Fake:
    """Stands in for oziwm: remembers the requests, answers like it."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if request.get("get") == "outputs":
            return {"ok": [{"name": "eDP-1", "x": 0, "y": 0, "width": 1000, "height": 600}]}
        if request.get("do") == "screenshot":
            with open(request["path"], "wb") as f:
                f.write(b"\x89PNG fake")
            return {"ok": request["path"]}
        return {"ok": None}


class BridgeServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.shared = os.path.join(self.tmp.name, "Ders Notları")
        self.pen = os.path.join(self.tmp.name, "ozi-pen")
        os.makedirs(self.pen)
        with open(os.path.join(self.pen, "ozi-pen-1.png"), "wb") as f:
            f.write(b"\x89PNG one")
        old = os.path.join(self.pen, "dun.png")
        with open(old, "wb") as f:
            f.write(b"\x89PNG old")
        os.utime(old, (time.time() - 3 * 86400,) * 2)
        with open(os.path.join(self.tmp.name, "secret.txt"), "w") as f:
            f.write("no")
        self.ipc = Fake()
        self.pdfs = []

        def make_pdf(images, out):
            self.pdfs.append(images)
            with open(out, "wb") as f:
                f.write(b"%PDF-1.4 fake")
            return True

        self.bridge = bridge.Bridge(dirs=[self.shared, self.pen], ipc=self.ipc, make_pdf=make_pdf,
                                    snapshot=lambda: b"JPEG", port=18765, host="127.0.0.1")
        self.port = self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.port

    def tearDown(self):
        self.bridge.stop()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, r.read()

    def post(self, path, data):
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def status(self, path, method="GET"):
        try:
            req = urllib.request.Request(self.base + path, method=method, data=b"{}" if method == "POST" else None)
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status
        except urllib.error.HTTPError as err:
            return err.code

    def test_students_see_todays_notes_only(self):
        code, body = self.get("/")
        page = body.decode()
        self.assertEqual(code, 200)
        self.assertIn("ozi-pen-1.png", page)
        self.assertNotIn("dun.png", page)
        self.assertEqual(self.get("/n/ozi-pen-1.png")[1], b"\x89PNG one")

    def test_nothing_outside_the_notes_is_served(self):
        for path in ("/n/../secret.txt", "/n/%2e%2e/secret.txt", "/n/dun.png", "/n/secret.txt", "/etc/passwd"):
            self.assertEqual(self.status(path), 404, path)

    def test_the_teacher_pages_need_the_key(self):
        self.assertEqual(self.status("/k/wrong"), 404)
        self.assertEqual(self.status("/k/wrong/do", "POST"), 404)
        self.assertEqual(self.status("/k/%s/tahta.jpg" % "x" * 3), 404)
        code, body = self.get("/k/" + self.bridge.token)
        self.assertEqual(code, 200)
        self.assertIn("Tahta kumandası", body.decode())
        self.assertEqual(self.get("/k/%s/tahta.jpg" % self.bridge.token)[1], b"JPEG")
        self.assertEqual(len(self.bridge.token), 12)

    def test_remote_buttons_press_keys_and_move_the_pointer(self):
        key = "/k/%s/do" % self.bridge.token
        self.post(key, {"action": "next"})
        self.assertIn({"do": "press", "keys": [109]}, self.ipc.requests)
        self.post(key, {"action": "move", "dx": 30, "dy": -10})
        self.post(key, {"action": "move", "dx": 5000, "dy": 0})
        self.post(key, {"action": "click"})
        pointers = [r for r in self.ipc.requests if r.get("do") == "pointer"]
        self.assertEqual(pointers[0], {"do": "pointer", "x": 530, "y": 290})
        self.assertEqual(pointers[1]["x"], 999, "the pointer stays on the screen")
        self.assertEqual(pointers[2]["button"], bridge.BTN_LEFT)
        self.assertEqual(self.status(key.replace("/do", "/do"), "POST"), 400)

    def test_sharing_the_board_puts_it_in_the_notes(self):
        r = self.post("/k/%s/do" % self.bridge.token, {"action": "share"})
        self.assertTrue(r["ok"])
        names = [n["name"] for n in self.bridge.notes()]
        self.assertTrue(any(n.startswith("Tahta ") for n in names))
        code, body = self.get("/notlar.pdf")
        self.assertEqual(body, b"%PDF-1.4 fake")
        self.assertEqual(len(self.pdfs[-1]), 2, "today's two pictures, oldest first")


class Helpers(unittest.TestCase):
    def test_addresses_prefer_wifi_and_skip_loopback(self):
        out = json.dumps([
            {"ifname": "lo", "addr_info": [{"local": "127.0.0.1"}]},
            {"ifname": "enp1s0", "addr_info": [{"local": "192.168.1.5"}]},
            {"ifname": "docker0", "addr_info": [{"local": "172.17.0.1"}]},
            {"ifname": "wlan0", "addr_info": [{"local": "10.0.0.7"}]},
        ])

        class R:
            stdout = out
        self.assertEqual(bridge.local_addresses(run=lambda *a, **k: R()), ["10.0.0.7", "192.168.1.5"])

    def test_hotspot_password_is_easy_to_type(self):
        p = bridge.new_password()
        self.assertEqual(len(p), 10)
        self.assertFalse(set(p) & set("01lIoO"))

    def test_hotspot_gives_a_wifi_qr_text(self):
        calls = []

        class R:
            returncode = 0
            stdout = stderr = ""
        r = bridge.hotspot_on("abc23456xy", run=lambda argv, **k: calls.append(argv) or R())
        self.assertEqual(r["wifi"], "WIFI:T:WPA;S:OziOS-Tahta;P:abc23456xy;;")
        self.assertIn("hotspot", calls[0])


if __name__ == "__main__":
    unittest.main()
