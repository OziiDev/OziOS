"""Tahta Köprüsü (board bridge): phones in the classroom talk to the board
through a small web server on it, nothing to install.

- The teacher scans one QR code and the phone becomes the board's remote:
  next and previous slide, start and end the show, a touchpad, a live view of
  the board, and "share this board" which saves what is on it for the class.
- Students scan the other QR code and get the lesson's notes: drawings saved
  by the screen pen, boards the teacher shared, and all of them as one PDF.

The teacher's pages carry a random key that only the QR code on the board
shows, so a student who guesses the address gets nothing but the notes. The
server only listens while the Tahta Köprüsü window is open.

The keys and clicks go to the desktop through oziwm's IPC socket; everything
that needs Qt (the PDF, shrinking screenshots) is passed in by the app, so
this module has no Qt in it and is tested without a screen.
"""
import html
import json
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
NOTE_EXT = (".png", ".jpg", ".jpeg", ".pdf")

# evdev key codes for the remote's buttons.
KEYS = {
    "next": [109],        # Page Down: next slide in LibreOffice, PDF viewers, Xournal++
    "prev": [104],        # Page Up
    "start": [63],        # F5: start the show
    "end": [1],           # Esc
    "black": [48],        # B: a black screen in the show
}
BTN_LEFT, BTN_RIGHT = 272, 273


# ---- the desktop ---------------------------------------------------------

def oziwm(request, socket_path=None, timeout=5.0):
    """One request to oziwm; its answer, or None when oziwm is not there."""
    path = socket_path or os.environ.get("OZIWM_SOCKET", "")
    if not path:
        return None
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.settimeout(timeout)
            s.connect(path)
            s.sendall((json.dumps(request) + "\n").encode())
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
        return json.loads(data or b"null")
    except (OSError, ValueError):
        return None


def local_addresses(run=subprocess.run):
    """The board's IPv4 addresses on the local network, the likeliest first."""
    try:
        out = run(["ip", "-j", "-4", "addr"], capture_output=True, text=True, timeout=5).stdout
        links = json.loads(out or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    found = []
    for link in links:
        name = link.get("ifname", "")
        if name == "lo" or name.startswith(("docker", "virbr", "veth", "podman")):
            continue
        for addr in link.get("addr_info", []):
            ip = addr.get("local", "")
            if ip and not ip.startswith("127."):
                found.append((0 if name.startswith("wl") else 1, ip))
    return [ip for _, ip in sorted(found)]


def qr_svg(text, run=subprocess.run):
    """A QR code for `text` as SVG (qrencode), or "" when qrencode is missing."""
    if not shutil.which("qrencode"):
        return ""
    try:
        out = run(["qrencode", "-t", "SVG", "-m", "1", "-l", "M", "-o", "-", text],
                  capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


# ---- the board's own Wi-Fi ------------------------------------------------

HOTSPOT_NAME = "OziOS-Tahta"


def hotspot_on(password, run=subprocess.run):
    """Turn the board's Wi-Fi into an access point for the class. The Wi-Fi it was
    on is left while the hotspot runs (one radio does one or the other)."""
    out = run(["nmcli", "device", "wifi", "hotspot", "con-name", HOTSPOT_NAME, "ssid", HOTSPOT_NAME,
               "password", password], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise ValueError((out.stderr or out.stdout).strip() or "nmcli failed")
    return {"ssid": HOTSPOT_NAME, "password": password,
            "wifi": "WIFI:T:WPA;S:%s;P:%s;;" % (HOTSPOT_NAME, password)}


def hotspot_off(run=subprocess.run):
    run(["nmcli", "connection", "down", HOTSPOT_NAME], capture_output=True, text=True, timeout=30)
    return {}


def new_password():
    # Easy to type from the board: no look-alike letters.
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


# ---- notes -----------------------------------------------------------------

def notes_dirs(environ=os.environ):
    """Where notes come from: the shared folder, then the screen pen's drawings."""
    home = environ.get("HOME", os.path.expanduser("~"))

    def user_dir(kind, fallback):
        try:
            out = subprocess.run(["xdg-user-dir", kind], capture_output=True, text=True, timeout=3).stdout.strip()
            if out and out != home:
                return out
        except (OSError, subprocess.SubprocessError):
            pass
        return os.path.join(home, fallback)

    return [os.path.join(user_dir("DOCUMENTS", "Belgeler"), "Ders Notları"),
            os.path.join(user_dir("PICTURES", "Resimler"), "ozi-pen")]


def list_notes(dirs, since=None):
    """Notes newest first: {name, path, size, time}. `since` (epoch) keeps only newer ones."""
    found = []
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            path = os.path.join(d, name)
            if not name.lower().endswith(NOTE_EXT) or not os.path.isfile(path):
                continue
            st = os.stat(path)
            if since and st.st_mtime < since:
                continue
            found.append({"name": name, "path": path, "size": st.st_size, "time": st.st_mtime})
    found.sort(key=lambda n: n["time"], reverse=True)
    return found


def start_of_today(now=None):
    t = time.localtime(now)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


# ---- the pages ---------------------------------------------------------------

STYLE = """
:root{--ink:#0B1310;--raised:#13201A;--control:#1C2C24;--text:#F2FCF6;--muted:#8DA897;--accent:#45F582;--on:#08140C}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 system-ui,sans-serif;background:var(--ink);color:var(--text)}
main{max-width:640px;margin:0 auto;padding:20px 16px 40px}h1{font-size:24px;margin:8px 0 4px}
p.sub{color:var(--muted);margin:0 0 18px}.card{background:var(--raised);border-radius:18px;padding:14px;margin:12px 0}
a.note{display:flex;gap:12px;align-items:center;padding:10px;border-radius:12px;color:var(--text);text-decoration:none}
a.note:active{background:var(--control)}a.note img{width:64px;height:48px;object-fit:cover;border-radius:8px;background:#fff}
.pdf{width:64px;height:48px;border-radius:8px;background:var(--control);display:grid;place-items:center;color:var(--accent);font-weight:700}
.btn{display:block;width:100%;border:0;border-radius:14px;padding:16px;font:600 17px system-ui;background:var(--control);color:var(--text);text-align:center;text-decoration:none}
.btn.main{background:var(--accent);color:var(--on)}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:10px 0}.small{color:var(--muted);font-size:14px}
#pad{height:240px;border-radius:18px;background:var(--control);touch-action:none;display:grid;place-items:center;text-align:center;padding:16px;color:var(--muted);user-select:none;-webkit-user-select:none}
#board{width:100%;border-radius:12px;display:none;background:#000}#board.on{display:block}
#msg{min-height:22px;color:var(--accent);text-align:center;margin-top:8px}
"""


def page(title, body, script=""):
    return ("<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>%s</style></head><body><main>%s</main>%s</body></html>"
            % (html.escape(title), STYLE, body, "<script>%s</script>" % script if script else ""))


def size_text(n):
    return "%.1f MB" % (n / 1e6) if n >= 1e6 else "%d KB" % max(1, n // 1000)


def students_page(notes, has_pdf):
    items = []
    for n in notes:
        url = "/n/" + urllib.parse.quote(n["name"])
        thumb = "<span class='pdf'>PDF</span>" if n["name"].lower().endswith(".pdf") else "<img src='%s' alt=''>" % url
        when = time.strftime("%H:%M", time.localtime(n["time"]))
        items.append("<a class='note' href='%s' download>%s<span>%s<br><span class='small'>%s · %s</span></span></a>"
                     % (url, thumb, html.escape(n["name"]), when, size_text(n["size"])))
    body = "<h1>Ders notları</h1><p class='sub'>Tahtadan bugün paylaşılanlar. Dokun, telefonuna insin.</p>"
    if notes and has_pdf:
        body += "<a class='btn main' href='/notlar.pdf' download>Hepsini tek PDF olarak indir</a>"
    body += "<div class='card'>%s</div>" % ("".join(items) or "<p class='small'>Henüz paylaşılan not yok.</p>")
    body += "<a class='btn' href='/'>Yenile</a>"
    return page("Ders notları", body)


def teacher_page(token):
    base = "/k/" + token
    body = """
<h1>Tahta kumandası</h1><p class='sub'>Bu sayfa yalnız senin; adresi kimseyle paylaşma.</p>
<div class='row'><button class='btn main' data-do='prev'>◀ Önceki</button><button class='btn main' data-do='next'>Sonraki ▶</button></div>
<div class='row3'><button class='btn' data-do='start'>Sunumu başlat</button><button class='btn' data-do='black'>Kararta</button><button class='btn' data-do='end'>Bitir</button></div>
<div id='pad'>Fare: kaydır · dokun = tıkla · iki parmak = sağ tık</div>
<div class='row'><button class='btn' data-do='click'>Tıkla</button><button class='btn' data-do='right'>Sağ tık</button></div>
<div class='card'><img id='board' alt='Tahta'><div class='row'><button class='btn' id='live'>Canlı görüntü: kapalı</button><button class='btn main' data-do='share'>Bu tahtayı paylaş</button></div></div>
<div id='msg'></div>"""
    script = """
const base=%s;const msg=document.getElementById('msg');
function send(a,extra){return fetch(base+'/do',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({action:a},extra||{}))}).then(r=>r.json()).then(r=>{if(r.say){msg.textContent=r.say;setTimeout(()=>msg.textContent='',2500)}}).catch(()=>{msg.textContent='Tahtaya ulaşılamadı'})}
document.querySelectorAll('[data-do]').forEach(b=>b.addEventListener('click',()=>send(b.dataset.do)));
const pad=document.getElementById('pad');let last=null,moved=0,pend=[0,0],timer=null,fingers=0,downAt=0;
function flush(){timer=null;if(pend[0]||pend[1]){send('move',{dx:pend[0],dy:pend[1]});pend=[0,0]}}
pad.addEventListener('pointerdown',e=>{pad.setPointerCapture(e.pointerId);last=[e.clientX,e.clientY];moved=0;downAt=Date.now()});
pad.addEventListener('touchstart',e=>{fingers=Math.max(fingers,e.touches.length)},{passive:true});
pad.addEventListener('pointermove',e=>{if(!last)return;const dx=e.clientX-last[0],dy=e.clientY-last[1];last=[e.clientX,e.clientY];moved+=Math.abs(dx)+Math.abs(dy);pend[0]+=dx*2.2;pend[1]+=dy*2.2;if(!timer)timer=setTimeout(flush,40)});
pad.addEventListener('pointerup',()=>{if(last&&moved<8&&Date.now()-downAt<350){send(fingers>1?'right':'click')}last=null;setTimeout(()=>fingers=0,50)});
const img=document.getElementById('board'),live=document.getElementById('live');let on=false,busy=false;
function frame(){if(!on||busy)return;busy=true;const n=new Image();n.onload=()=>{img.src=n.src;img.classList.add('on');busy=false;setTimeout(frame,800)};n.onerror=()=>{busy=false;setTimeout(frame,2000)};n.src=base+'/tahta.jpg?'+Date.now()}
live.addEventListener('click',()=>{on=!on;live.textContent='Canlı görüntü: '+(on?'açık':'kapalı');if(on)frame();else img.classList.remove('on')});
""" % json.dumps(base)
    return page("Tahta kumandası", body, script)


# ---- the server --------------------------------------------------------------

class Bridge:
    """The web server and what it does; `ipc`, `snapshot` and `make_pdf` are
    passed in so tests run without a desktop."""

    def __init__(self, dirs=None, ipc=oziwm, snapshot=None, make_pdf=None, port=PORT, host="0.0.0.0"):
        self.dirs = dirs or notes_dirs()
        self.ipc = ipc
        self.snapshot = snapshot          # () -> JPEG bytes of the board, or None
        self.make_pdf = make_pdf          # ([png paths], out path) -> bool
        self.token = secrets.token_urlsafe(9)
        self.since = start_of_today()
        self.pointer = None
        self.lock = threading.Lock()
        self.server = None
        self.thread = None
        self.host = host
        self.port = port
        self.on_event = None              # (text) -> None, for the window's log

    # -- actions --

    def screen(self):
        outs = (self.ipc({"get": "outputs"}) or {}).get("ok") or []
        if not outs:
            return (0, 0, 1920, 1080)
        o = outs[0]
        return (o.get("x", 0), o.get("y", 0), o.get("width", 1920), o.get("height", 1080))

    def act(self, action, data=None):
        data = data or {}
        if action in KEYS:
            self.ipc({"do": "press", "keys": KEYS[action]})
            return {"ok": True}
        if action in ("move", "click", "right"):
            with self.lock:
                x0, y0, w, h = self.screen()
                if self.pointer is None:
                    self.pointer = [x0 + w / 2, y0 + h / 2]
                if action == "move":
                    self.pointer[0] = min(max(self.pointer[0] + float(data.get("dx", 0)), x0), x0 + w - 1)
                    self.pointer[1] = min(max(self.pointer[1] + float(data.get("dy", 0)), y0), y0 + h - 1)
                request = {"do": "pointer", "x": int(self.pointer[0]), "y": int(self.pointer[1])}
                if action != "move":
                    request["button"] = BTN_LEFT if action == "click" else BTN_RIGHT
                self.ipc(request)
            return {"ok": True}
        if action == "share":
            path = self.share_board()
            return {"ok": bool(path), "say": "Paylaşıldı: öğrenciler indirebilir" if path else "Paylaşılamadı"}
        raise ValueError("unknown action")

    def share_board(self):
        """Save what is on the board now in the shared folder."""
        folder = self.dirs[0]
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            return ""
        path = os.path.join(folder, time.strftime("Tahta %H.%M.%S.png"))
        answer = self.ipc({"do": "screenshot", "path": path}) or {}
        if "ok" not in answer:
            return ""
        for _ in range(50):          # the compositor writes it on its next frame
            if os.path.exists(path) and os.path.getsize(path) > 0:
                break
            time.sleep(0.1)
        if self.on_event:
            self.on_event("Tahta paylaşıldı")
        return path if os.path.exists(path) else ""

    def notes(self):
        return list_notes(self.dirs, self.since)

    def pdf(self):
        if not self.make_pdf:
            return None
        images = [n["path"] for n in reversed(self.notes()) if n["name"].lower().endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            return None
        out = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ozi-bridge-notes.pdf")
        return out if self.make_pdf(images, out) else None

    # -- serving --

    def handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "OziOS"

            def log_message(self, *args):
                pass

            def send(self, code, body, kind="text/html; charset=utf-8", extra=None):
                if isinstance(body, str):
                    body = body.encode()
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def file(self, path, name):
                kind = "application/pdf" if name.lower().endswith(".pdf") else (
                    "image/png" if name.lower().endswith(".png") else "image/jpeg")
                with open(path, "rb") as f:
                    data = f.read()
                self.send(200, data, kind, {"Content-Disposition": "inline; filename*=UTF-8''" + urllib.parse.quote(name)})

            def teacher(self, rest):
                """The path after /k/, when its key is right; None otherwise."""
                key, _, tail = rest.partition("/")
                return tail if secrets.compare_digest(key, bridge.token) else None

            def do_GET(self):
                path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
                if path == "/":
                    return self.send(200, students_page(bridge.notes(), bridge.make_pdf is not None))
                if path.startswith("/n/"):
                    name = path[3:]
                    for n in bridge.notes():
                        if n["name"] == name:      # only what the list shows, never a path
                            return self.file(n["path"], name)
                    return self.send(404, "Yok")
                if path == "/notlar.pdf":
                    out = bridge.pdf()
                    return self.file(out, "Ders notları.pdf") if out else self.send(404, "Yok")
                if path.startswith("/k/"):
                    tail = self.teacher(path[3:])
                    if tail is None:
                        return self.send(404, "Yok")
                    if tail == "":
                        return self.send(200, teacher_page(bridge.token))
                    if tail == "tahta.jpg" and bridge.snapshot:
                        data = bridge.snapshot()
                        return self.send(200, data, "image/jpeg") if data else self.send(503, "")
                return self.send(404, "Yok")

            do_HEAD = do_GET

            def do_POST(self):
                path = urllib.parse.urlsplit(self.path).path
                tail = self.teacher(path[3:]) if path.startswith("/k/") else None
                if tail != "do":
                    return self.send(404, "Yok")
                try:
                    length = min(int(self.headers.get("Content-Length", 0)), 4096)
                    data = json.loads(self.rfile.read(length) or b"{}")
                    result = bridge.act(str(data.get("action", "")), data)
                except (ValueError, TypeError) as err:
                    return self.send(400, json.dumps({"error": str(err)}), "application/json")
                self.send(200, json.dumps(result), "application/json")

        return Handler

    def start(self):
        last_error = None
        for port in range(self.port, self.port + 20):
            try:
                self.server = ThreadingHTTPServer((self.host, port), self.handler())
                self.port = port
                break
            except OSError as err:
                last_error = err
        if self.server is None:
            raise ValueError("no free port: %s" % last_error)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.port

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def urls(self, address):
        base = "http://%s:%d" % (address, self.port)
        return {"students": base + "/", "teacher": "%s/k/%s" % (base, self.token)}

