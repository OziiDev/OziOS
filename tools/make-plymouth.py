"""Write the OziOS boot splash: a Plymouth "two-step" theme with the turning tesseract.

    python3 tools/make-plymouth.py          (needs PyQt6)

Plymouth's two-step plugin loops throbber-NNNN.png while the computer starts,
shows animation-NNNN.png at the end when a mode asks for it, and draws the disk
password prompt with entry.png, bullet.png and lock.png. All of them are drawn
here, so the splash comes from the same geometry as the wallpaper and the logo.

The loop is seamless: a tesseract turned a quarter turn in a coordinate plane is
the same figure again, so turning two planes by a quarter over the loop ends
where it began.
"""
import math
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QRadialGradient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
OUT = os.path.join(ROOT, "branding", "plymouth", "ozios")

FRAMES = 48               # throbber frames; Plymouth shows them at about 30 a second
END_FRAMES = 12
SIZE = 168
CYAN = QColor(0, 229, 255)
ICE = QColor(244, 252, 255)
INK = QColor(8, 11, 16)

CORNERS = [[1 if i & bit else -1 for bit in (8, 4, 2, 1)] for i in range(16)]
EDGES = [(a, b) for a in range(16) for b in range(a + 1, 16) if bin(a ^ b).count("1") == 1]


def project(phase):
    """Corners on the picture, with a depth from 0 (far) to 1 (near), for a phase from 0 to 1."""
    xw = phase * math.pi / 2              # a quarter turn in x-w over the loop
    yz = phase * math.pi / 2              # and in y-z
    out = []
    for x, y, z, w in CORNERS:
        c, s = math.cos(xw), math.sin(xw)
        x, w = x * c - w * s, x * s + w * c
        c, s = math.cos(yz), math.sin(yz)
        y, z = y * c - z * s, y * s + z * c
        # A fixed tilt, so the figure is seen at an angle and never flat.
        c, s = math.cos(0.42), math.sin(0.42)
        x, z = x * c - z * s, x * s + z * c
        c, s = math.cos(0.3), math.sin(0.3)
        y, z = y * c - z * s, y * s + z * c
        k = 2.6 / (3.4 - w)
        x, y, z = x * k, y * k, z * k
        k = 3.2 / (4.6 - z)
        depth = max(0.0, min(1.0, (w + 1.5) / 3 * 0.6 + (z + 2) / 4 * 0.4))
        out.append((x * k, y * k, depth))
    return out


def tesseract(phase, size=SIZE, fade=1.0, scale=1.0):
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    glow = QRadialGradient(QPointF(size / 2, size / 2), size / 2)
    glow.setColorAt(0, QColor(0, 229, 255, int(46 * fade)))
    glow.setColorAt(1, QColor(0, 229, 255, 0))
    painter.fillRect(QRectF(0, 0, size, size), glow)
    unit = size / 3.3 * scale
    points = [(size / 2 + x * unit, size / 2 + y * unit, d) for x, y, d in project(phase)]
    for a, b in sorted(EDGES, key=lambda e: points[e[0]][2] + points[e[1]][2]):     # far edges first
        depth = (points[a][2] + points[b][2]) / 2
        halo = QColor(CYAN)
        halo.setAlphaF(min(1.0, (0.06 + depth * 0.12) * fade))
        painter.setPen(QPen(halo, (5 + depth * 6) * size / 400, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(points[a][0], points[a][1]), QPointF(points[b][0], points[b][1]))
        line = QColor(CYAN)
        line.setAlphaF(min(1.0, (0.3 + depth * 0.7) * fade))
        painter.setPen(QPen(line, max(1.0, (1 + depth * 1.6) * size / 300), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(points[a][0], points[a][1]), QPointF(points[b][0], points[b][1]))
    painter.setPen(Qt.PenStyle.NoPen)
    for x, y, depth in points:
        dot = QColor(ICE)
        dot.setAlphaF(min(1.0, (0.45 + depth * 0.55) * fade))
        painter.setBrush(dot)
        radius = (1.4 + depth * 2.2) * size / 300
        painter.drawEllipse(QPointF(x, y), radius, radius)
    painter.end()
    return image


def rounded(width, height, radius, fill, rim=None):
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), radius, radius)
    painter.fillPath(path, fill)
    if rim is not None:
        painter.setPen(QPen(rim, 1))
        painter.drawPath(path)
    painter.end()
    return image


def lock_icon(size=24):
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(CYAN, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(QRectF(size * 0.28, size * 0.1, size * 0.44, size * 0.5), 0, 180 * 16)
    painter.drawLine(QPointF(size * 0.28, size * 0.35), QPointF(size * 0.28, size * 0.45))
    painter.drawLine(QPointF(size * 0.72, size * 0.35), QPointF(size * 0.72, size * 0.45))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(CYAN)
    painter.drawRoundedRect(QRectF(size * 0.18, size * 0.44, size * 0.64, size * 0.46), 3, 3)
    painter.setBrush(INK)
    painter.drawEllipse(QPointF(size / 2, size * 0.64), size * 0.07, size * 0.07)
    painter.end()
    return image


THEME_FILE = """\
[Plymouth Theme]
Name=OziOS
Description=The OziOS tesseract, turning while the computer starts
ModuleName=two-step

[two-step]
Font=Overpass 12
TitleFont=Overpass Light 30
ImageDir=/usr/share/plymouth/themes/ozios
DialogHorizontalAlignment=.5
DialogVerticalAlignment=.66
TitleHorizontalAlignment=.5
TitleVerticalAlignment=.3
HorizontalAlignment=.5
VerticalAlignment=.46
Transition=none
TransitionDuration=0.0
BackgroundStartColor=0x080b10
BackgroundEndColor=0x080b10
ProgressBarBackgroundColor=0x141b26
ProgressBarForegroundColor=0x00e5ff
MessageBelowAnimation=true

[boot-up]
UseEndAnimation=false

[shutdown]
UseEndAnimation=false

[reboot]
UseEndAnimation=false

[updates]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Installing updates
SubTitle=Do not turn off the computer

[system-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
Title=Upgrading the system
SubTitle=Do not turn off the computer
"""


def files():
    """{file name: QImage or text} of the whole theme."""
    out = {"ozios.plymouth": THEME_FILE}
    for frame in range(FRAMES):
        out["throbber-%04d.png" % (frame + 1)] = tesseract(frame / FRAMES)
    for frame in range(END_FRAMES):
        step = (frame + 1) / END_FRAMES
        out["animation-%04d.png" % (frame + 1)] = tesseract(step * 0.25, fade=1 - step, scale=1 + step * 0.25)
    out["entry.png"] = rounded(280, 34, 6, QColor(20, 27, 38), QColor(0, 229, 255, 110))
    out["bullet.png"] = rounded(8, 8, 4, ICE)
    out["lock.png"] = lock_icon()
    return out


def main():
    app = QGuiApplication(sys.argv[:1])  # noqa: F841  QImage text and painting need one
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):                 # frames of an earlier, longer loop must not stay behind
        if name.endswith(".png"):
            os.remove(os.path.join(OUT, name))
    for name, content in files().items():
        path = os.path.join(OUT, name)
        if isinstance(content, str):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
        elif not content.save(path):
            sys.exit("could not write " + path)
    print("wrote", len(files()), "files to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
