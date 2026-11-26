#!/usr/bin/env python3
"""Make OziOS promo videos and pictures for Instagram from real screenshots.

    tools/promo-video.py SCENES.json OUT_DIR

SCENES.json:
    {"scenes": [
        {"title": "OziOS", "text": "...", "image": "a.png" | "frames": "dir/", "seconds": 4},
        ...],
     "outro": {"title": "...", "text": "..."}}

Writes OUT_DIR/ozios-reel.mp4 (1080x1920, 30 fps, H.264, no sound: pick music
in the app) and OUT_DIR/kare-NN.png (1080x1350 carousel pictures, one per scene).
Every picture on screen is a real OziOS screenshot; nothing is drawn over the
desktop itself, the captions sit above and below it.
"""
import json
import math
import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient,  # noqa: E402
                         QPainter, QPainterPath, QPen, QRadialGradient)

W, H, FPS = 1080, 1920, 30
INK = QColor("#080B10")
TEXT = QColor("#F4FCFF")
MUTED = QColor("#9FB3BC")
ACCENT = QColor("#00E5FF")
ACCENT2 = QColor("#7C5CFF")
PINK = QColor("#FF5EAF")
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "..", "site", "logo.svg")


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def font(size, weight=QFont.Weight.Bold):
    f = QFont("Overpass", 10)
    f.setPixelSize(int(size))
    f.setWeight(weight)
    return f


def background(p, w, h, phase):
    p.fillRect(0, 0, w, h, INK)
    for color, cx, cy, r in ((ACCENT, 0.15 + 0.08 * math.sin(phase), 0.12, 0.9),
                             (ACCENT2, 0.9, 0.55 + 0.06 * math.cos(phase * 0.8), 0.85),
                             (PINK, 0.3, 0.98, 0.6)):
        g = QRadialGradient(QPointF(cx * w, cy * h), r * w)
        c = QColor(color)
        c.setAlphaF(0.20)
        g.setColorAt(0, c)
        c2 = QColor(color)
        c2.setAlphaF(0)
        g.setColorAt(1, c2)
        p.fillRect(0, 0, w, h, g)


def framed(p, img, rect, glow_phase):
    """The screenshot in a rounded frame with OziOS's flowing two-colour border."""
    path = QPainterPath()
    path.addRoundedRect(rect, 28, 28)
    for i in range(10, 0, -2):   # soft shadow
        shadow = QPainterPath()
        shadow.addRoundedRect(rect.adjusted(-i * 2, -i * 2 + 18, i * 2, i * 2 + 18), 28 + i, 28 + i)
        c = QColor(0, 0, 0, 10)
        p.fillPath(shadow, c)
    p.save()
    p.setClipPath(path)
    p.drawImage(rect, img)
    p.restore()
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    shift = (math.sin(glow_phase) + 1) / 2
    g.setColorAt(0, ACCENT)
    g.setColorAt(0.5 * shift + 0.25, ACCENT2)
    g.setColorAt(1, PINK)
    p.setPen(QPen(g, 5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def text_block(p, title, text, top, w, alpha, rise):
    """The title and the line under it; the title may take two lines, the
    text starts below wherever the title ends."""
    p.save()
    p.setOpacity(alpha)
    p.translate(0, rise)
    flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
    size = 84
    while True:
        p.setFont(font(size))
        used = p.boundingRect(QRectF(70, top, w - 140, 1000), flags, title)
        if used.height() <= size * 2.6 or size <= 56:
            break
        size -= 6
    p.setPen(TEXT)
    p.drawText(QRectF(70, top, w - 140, used.height() + 10), flags, title)
    p.setPen(MUTED)
    p.setFont(font(44, QFont.Weight.Normal))
    p.drawText(QRectF(90, top + used.height() + 28, w - 180, 300), flags, text)
    p.restore()


def brand(p, w, y, size=52, alpha=1.0):
    p.save()
    p.setOpacity(alpha)
    logo = QImage(LOGO)
    if not logo.isNull():
        s = int(size * 1.3)
        p.drawImage(QRectF(w / 2 - 110 - s / 2, y - s / 2, s, s * 260 / 280), logo)
    p.setPen(TEXT)
    p.setFont(font(size))
    p.drawText(QRectF(w / 2 - 60, y - size, 400, size * 2), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "OziOS")
    p.restore()


class Scene:
    def __init__(self, spec, base):
        self.title = spec.get("title", "")
        self.text = spec.get("text", "")
        self.seconds = float(spec.get("seconds", 4))
        # [x, y, w] in the screenshot: the reel zooms from the whole screen to
        # this part (the panel, the keyboard...), so a phone shows it big.
        self.focus = spec.get("focus")
        self.ratio = float(spec.get("ratio", 1.08))   # the frame's height / width while zoomed
        self.frames = []
        if spec.get("frames"):
            d = os.path.join(base, spec["frames"])
            self.frames = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".png")]
        elif spec.get("image"):
            self.frames = [os.path.join(base, spec["image"])]
        self.cache = {}

    def image(self, t):
        if not self.frames:
            return None
        if len(self.frames) == 1:
            i = 0
        else:   # play the recorded frames once, hold the last one
            i = min(len(self.frames) - 1, int(t * self.seconds * FPS * len(self.frames) / max(1, self.seconds * FPS)))
            i = min(len(self.frames) - 1, int(t * len(self.frames) * 1.15))
        path = self.frames[i]
        if path not in self.cache:
            self.cache = {path: QImage(path)}
        return self.cache[path]


def draw_scene(p, scene, t, global_t, w=W, h=H, still=False):
    """t: 0..1 through the scene."""
    background(p, w, h, global_t * 0.7)
    brand(p, w, 120 if h > 1500 else 90, 44, 0.9)
    img = scene.image(t)
    appear = 1.0 if still else ease(t * 5)
    if img is not None and not img.isNull() and scene.focus and not still:
        # A tall frame on the phone, zooming from the whole screen into the focus.
        box_w = w - 2 * 60
        box_h = round(box_w * scene.ratio)
        aspect = box_w / box_h
        fx, fy, fw = scene.focus
        fh = fw / aspect
        if fh > img.height():                 # never ask for more than the picture has
            fh = img.height()
            fw = fh * aspect
        full_h = img.height()
        full_w = full_h * aspect
        cx0, cy0 = img.width() / 2, img.height() / 2
        k = ease((t - 0.12) / 0.6)
        sw = full_w + (fw - full_w) * k
        sh = full_h + (fh - full_h) * k
        cx = cx0 + (fx + fw / 2 - cx0) * k
        cy = cy0 + (fy + fh / 2 - cy0) * k
        sx = max(0.0, min(img.width() - sw, cx - sw / 2))
        sy = max(0.0, min(img.height() - sh, cy - sh / 2))
        y = 250
        rect = QRectF(w / 2 - box_w / 2, y + 40 * (1 - appear), box_w, box_h)
        part = img.copy(int(sx), int(sy), int(sw), int(sh))
        p.save()
        p.setOpacity(appear)
        framed(p, part, rect, global_t * 2)
        p.restore()
        text_top = rect.bottom() + 60
    elif img is not None and not img.isNull():
        box_w = w - 2 * 60
        box_h = box_w * img.height() / img.width()
        y = (h * 0.30) if h > 1500 else 200
        # A slow push in (Ken Burns) on stills: the eye keeps moving.
        zoom = 1.0 if (still or len(scene.frames) > 1) else 1.0 + 0.05 * t
        rect = QRectF(w / 2 - box_w * zoom / 2, y - (box_h * (zoom - 1)) / 2 + 40 * (1 - appear), box_w * zoom, box_h * zoom)
        p.save()
        p.setOpacity(appear)
        framed(p, img, rect, global_t * 2)
        p.restore()
        text_top = rect.bottom() + (70 if h > 1500 else 40)
    else:
        text_top = h * 0.40
    text_block(p, scene.title, scene.text, text_top, w, ease(t * 4 - 0.3) if not still else 1.0,
               0 if still else 30 * (1 - ease(t * 4 - 0.3)))


def draw_outro(p, outro, t, global_t, w=W, h=H):
    background(p, w, h, global_t * 0.7)
    a = ease(t * 3)
    logo = QImage(LOGO)
    s = 380 * (0.85 + 0.15 * a)
    p.save()
    p.setOpacity(a)
    p.translate(w / 2, h * 0.36)
    p.rotate(8 * math.sin(global_t * 2))
    p.drawImage(QRectF(-s / 2, -s / 2 * 260 / 280, s, s * 260 / 280), logo)
    p.restore()
    text_block(p, outro.get("title", "OziOS"), outro.get("text", ""), h * 0.50, w, ease(t * 3 - 0.3), 0)


def render(spec_path, out):
    base = os.path.dirname(os.path.abspath(spec_path))
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    scenes = [Scene(s, base) for s in spec["scenes"]]
    outro = spec.get("outro", {})
    os.makedirs(out, exist_ok=True)
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))

    n = 0
    total = sum(s.seconds for s in scenes) + float(outro.get("seconds", 3.5))
    fade = int(0.35 * FPS)
    previous = None
    for scene in scenes + [None]:
        seconds = scene.seconds if scene else float(outro.get("seconds", 3.5))
        count = int(seconds * FPS)
        for i in range(count):
            t = i / max(1, count - 1)
            img = QImage(W, H, QImage.Format.Format_RGB32)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            if scene:
                draw_scene(p, scene, t, n / FPS)
            else:
                draw_outro(p, outro, t, n / FPS)
            if previous is not None and i < fade:   # cross-fade from the last scene's end
                p.setOpacity(1 - i / fade)
                p.drawImage(0, 0, previous)
            p.end()
            img.save(os.path.join(frames_dir, "f%05d.png" % n))
            n += 1
            last = img
        previous = last
    video = os.path.join(out, "ozios-reel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%05d.png"),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    video], check=True)

    # Carousel pictures, 4:5, one per scene plus the closing card.
    for k, scene in enumerate(scenes, 1):
        img = QImage(1080, 1350, QImage.Format.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        draw_scene(p, scene, 1.0, k, 1080, 1350, still=True)
        p.end()
        img.save(os.path.join(out, "kare-%02d.png" % k))
    img = QImage(1080, 1350, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    draw_outro(p, outro, 1.0, 0, 1080, 1350)
    p.end()
    img.save(os.path.join(out, "kare-%02d.png" % (len(scenes) + 1)))
    print(video, "%.1f s" % total)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    app = QGuiApplication(sys.argv[:1])
    QFontDatabase.addApplicationFont("/usr/share/fonts/TTF/overpass-bold.ttf")
    render(sys.argv[1], sys.argv[2])
