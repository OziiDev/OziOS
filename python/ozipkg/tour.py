"""OziOS turu: Ozi-chan shows the Education edition by herself, opening the
real programs one after another, for a stand, a classroom or a board that is
waiting for someone. A touch pauses her.

The scenes are here; the app (apps/ozi-tour) draws Ozi-chan and her speech
bubble along the bottom of the screen and calls `enter` and `leave`.
"""
import base64
import os
import subprocess

from . import bridge

TOUR_FLAG = "/usr/share/ozios/tanitim"
SITE = "https://ozios.freedev.app"

# title, what Ozi-chan says, the program to open (None: just her), her colours,
# and how many seconds the scene lasts.
SCENES = [
    {"title": "Merhaba, ben Ozi-chan!",
     "text": "Bu OziOS Eğitim: akıllı tahtalar için yapılmış, kendi masaüstü olan bir Linux. "
             "Birkaç dakikada her şeyi göstereyim. Durdurmak için bana dokun.",
     "open": None, "look": "green", "seconds": 11},
    {"title": "Ekran kalemi",
     "text": "Ekranda ne olursa olsun üstüne parmakla ya da kalemle çizilir. Renkler, kalınlık, silgi, "
             "geri al; çizim tek dokunuşla kaydedilir.",
     "open": ["ozi-pen", "--demo"], "look": "pink", "seconds": 12},
    {"title": "Beyaz tahta",
     "text": "Xournal++ ile sayfa sayfa ders anlat, PDF'in üstüne yaz, resim ekle. Her şey bir dosyada kalır.",
     "open": ["xournalpp"], "look": "blue", "seconds": 11},
    {"title": "Sınıf",
     "text": "Rastgele öğrenci seç, grupları kur, etkinlik için süre tut. Sınıf listeleri tahtada kalır.",
     "open": ["ozi-classroom"], "look": "purple", "seconds": 11},
    {"title": "Tahta Köprüsü",
     "text": "Öğretmen QR kodu okutunca telefonu tahtanın kumandası olur: slayt, fare, canlı görüntü. "
             "Öğrenciler kendi kodunu okutup ders notlarını indirir. Uygulama ya da internet gerekmez.",
     "open": ["ozi-bridge"], "look": "green", "seconds": 14},
    {"title": "Kısıtlı ve yetkili mod",
     "text": "Tahta her sabah kısıtlı açılır: öğrenciler terminali, ayarları, mağazayı açamaz. Öğretmen şifresiyle "
             "her şey açılır. Dondurma açıksa tahta her açılışta tertemiz hâline döner.",
     "open": ["ozi-mode"], "look": "blue", "seconds": 14},
    {"title": "Ekran klavyesi ve dokunma",
     "text": "Yazı yazılacak bir yere dokununca ekran klavyesi kendiliğinden çıkar. Türkçe harfler, büyük tuşlar, "
             "her pencerede çalışır.",
     "open": None, "keyboard": True, "look": "pink", "seconds": 11},
    {"title": "Bozulmayan güncelleme",
     "text": "Her güncellemeden önce sistemin kopyası alınır. Güncellemeden sonra sistem kontrol edilir; "
             "bir şey bozulduysa yeniden başlatmadan önce kendiliğinden eski hâline döner.",
     "open": None, "look": "purple", "seconds": 12},
    {"title": "Hepsi ücretsiz",
     "text": "OziOS açık kaynak ve ücretsiz. USB belleğe yaz, tahtada dene, beğenirsen kur. "
             "İndirmek için kodu okut: ozios.freedev.app",
     "open": None, "look": "green", "qr": SITE, "seconds": 14},
]

LOOKS = {
    "green": "ozi-chan.svg",
    "pink": "ozi-chan-pembe.svg",
    "blue": "ozi-chan-mavi.svg",
    "purple": "ozi-chan-mor.svg",
}


def is_demo_medium(flag=TOUR_FLAG):
    """The tour starts by itself on the presentation USB (the tanıtım ISO)."""
    return os.path.exists(flag)


def scenes():
    out = []
    for i, s in enumerate(SCENES):
        item = dict(s, index=i, mascot=LOOKS.get(s["look"], LOOKS["green"]))
        if s.get("qr"):
            svg = bridge.qr_svg(s["qr"])
            item["qrImage"] = ("data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()) if svg else ""
        out.append(item)
    return out


def window_ids(ipc=bridge.oziwm):
    answer = ipc({"get": "windows"}) or {}
    return [w["id"] for w in (answer.get("ok") or []) if "id" in w]


class Tour:
    """Opens a scene's program and closes it again when the scene ends."""

    def __init__(self, ipc=bridge.oziwm):
        self.ipc = ipc
        self.before = None
        self.keyboard = False

    def enter(self, index):
        scene = SCENES[index]
        self.before = set(window_ids(self.ipc))
        self.keyboard = bool(scene.get("keyboard"))
        if scene.get("open"):
            self.ipc({"do": "spawn", "command": scene["open"]})
        if self.keyboard:
            self.ipc({"do": "key", "key": "keyboard-show"})
        return {"index": index}

    def leave(self):
        """Close what the scene opened, leave everything else alone."""
        if self.before is None:
            return {"closed": 0}
        opened = [i for i in window_ids(self.ipc) if i not in self.before]
        for wid in opened:
            self.ipc({"do": "close", "id": wid})
        self.before = None
        if self.keyboard:
            self.ipc({"do": "key", "key": "keyboard-hide"})
            self.keyboard = False
        # The pen is a layer, not a window: it is ended by name.
        subprocess.run(["pkill", "-x", "ozi-pen"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"closed": len(opened)}
