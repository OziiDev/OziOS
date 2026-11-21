"""Pictures of the OziOS shell, made without a Plasma session.

    python3 tools/shell-preview.py OUTDIR [--theme NAME | --all-themes] [--check] [--still]

Each scene loads the real QML from desktop/ on top of the stand-ins in
tools/plasma_stubs.py and drives it the way a person would:

    dock        the dock on a floating panel, the pointer on its second icon
    launcher    the launcher's popup after its tiles have flowed in
    search      the launcher with "o" typed into the search field
    control     the control widget's popup, theme swatches included
    wallpaper   the wallpaper, a few seconds in so the motes are out

and saves OUTDIR/<scene>-<theme>.png plus OUTDIR/showcase-<theme>.png, all
of them together. Program icons are drawn as coloured tiles (icon themes are
not available outside Plasma), and the panel behind the dock is a plain
approximation of the OziOS Plasma style.

Every warning Qt prints is listed at the end. With --check nothing is saved and
the exit status is 1 when there was any warning or a scene did not load:
tests/test_desktop.py runs it that way. --still turns animations off, as
`ozi effects off` does.
"""
import argparse
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtCore import QLocale, QPoint, QPointF, QRectF, QUrl, Qt, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPalette  # noqa: E402
from PyQt6.QtQml import QQmlEngine  # noqa: E402
from PyQt6.QtQuick import QQuickItem, QQuickView, QQuickWindow  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

import plasma_stubs  # noqa: E402
import plasma_style  # noqa: E402
from ozipkg import themes  # noqa: E402

DESKTOP = os.path.join(ROOT, "desktop")
SCENES = ("dock", "launcher", "search", "control", "bar", "calendar", "switcher", "wallpaper")

messages = []


def remember(mode, context, message):
    where = "/".join((context.file or "?").replace("\\", "/").split("/")[-3:])
    messages.append("%s:%s: %s" % (where, context.line, message))


def url(*parts):
    return QUrl.fromLocalFile(os.path.join(DESKTOP, *parts)).toString()


HARNESS = {
    # The dock sits on a floating panel near the bottom of a desktop.
    "dock": ("""
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as K
Item {
    width: 760; height: 128
    Item {
        id: panel
        objectName: "panel"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        height: 65
        width: (dock.item ? dock.item.Layout.preferredWidth : 300) + 8
        Loader {
            id: dock
            objectName: "applet"
            anchors.fill: parent
            anchors.margins: 4
            source: "%(dock)s"
        }
    }
}
""", (760, 128)),
    "launcher": ("""
import QtQuick
import org.kde.kirigami as K
Item {
    width: 880; height: 620
    Loader {
        id: launcher
        objectName: "applet"
        anchors.fill: parent
        anchors.margins: 10
        source: "%(launcher)s"
        focus: true
        onLoaded: item.expanded = true
    }
}
""", (880, 620)),
    "control": ("""
import QtQuick
import org.kde.kirigami as K
Item {
    width: 380; height: 330
    Loader {
        objectName: "applet"
        anchors.fill: parent
        anchors.margins: 12
        source: "%(control)s"
        onLoaded: item.expanded = true
    }
}
""", (380, 330)),
    # The islands at the top: desktops on the left, the clock in the middle.
    "bar": ("""
import QtQuick
import QtQuick.Layouts
Item {
    width: 900; height: 56
    Item {
        objectName: "island"
        x: 12; y: 8; height: 40
        width: (desktops.item && desktops.item.fullRepresentationItem ? desktops.item.fullRepresentationItem.Layout.preferredWidth : 80) + 16
        Loader {
            id: desktops
            objectName: "applet"
            anchors.fill: parent
            anchors.margins: 4
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            source: "%(workspaces)s"
        }
    }
    Item {
        objectName: "island"
        anchors.horizontalCenter: parent.horizontalCenter
        y: 8; height: 40
        width: (clock.item && clock.item.compactRepresentationItem ? clock.item.compactRepresentationItem.Layout.preferredWidth : 120) + 8
        Loader {
            id: clock
            objectName: "applet"
            anchors.fill: parent
            anchors.margins: 4
            source: "%(clock)s"
        }
    }
}
""", (900, 56)),
    "calendar": ("""
import QtQuick
Item {
    width: 330; height: 420
    Loader {
        objectName: "applet"
        anchors.fill: parent
        anchors.margins: 12
        source: "%(clock)s"
        onLoaded: item.expanded = true
    }
}
""", (330, 420)),
    "wallpaper": ("""
import QtQuick
Item {
    width: 1280; height: 720
    Loader {
        objectName: "applet"
        anchors.fill: parent
        source: "%(wallpaper)s"
    }
}
""", (1280, 720)),
}
# The switcher opens its own popup window; this item only holds it.
HARNESS["switcher"] = ("""
import QtQuick
Item {
    width: 40; height: 40
    Loader {
        objectName: "applet"
        source: "%(switcher)s"
        onLoaded: {
            item.screenGeometry = Qt.rect(0, 0, 1600, 900)
            item.model = stubWindows
            item.currentIndex = 1
        }
    }
}
""", (40, 40))
HARNESS["search"] = HARNESS["launcher"]
PACKAGES = {
    "dock": ("plasmoids", "org.ozios.dock"),
    "launcher": ("plasmoids", "org.ozios.launcher"),
    "control": ("plasmoids", "org.ozios.control"),
    "workspaces": ("plasmoids", "org.ozios.workspaces"),
    "clock": ("plasmoids", "org.ozios.clock"),
    "wallpaper": ("wallpaper", "org.ozios.tesseract"),
    "switcher": ("kwin/tabbox", "org.ozios.switcher"),
}


def sources(folder):
    """The main.qml of each package, from a copy that loads with the stand-ins."""
    out = {}
    for name, (kind, package) in PACKAGES.items():
        copy = plasma_stubs.prepared(os.path.join(DESKTOP, *kind.split("/"), package, "contents", "ui"), folder)
        out[name] = QUrl.fromLocalFile(os.path.join(copy, "main.qml")).toString()
    return out
# How long each scene runs before its picture is taken, in milliseconds.
SETTLE = {"dock": 1400, "launcher": 1500, "search": 1200, "control": 700, "bar": 900, "calendar": 600,
          "switcher": 900, "wallpaper": 5200}
CONFIG = {"launchers": ["applications:org.kde.konsole.desktop", "applications:ozi-store.desktop",
                        "applications:systemsettings.desktop"], "magnify": True, "icon": "ozios",
          "favoritesPortedToKAstats": True}


def palette(theme_id):
    theme = themes.BY_ID[theme_id]
    colors = {
        QPalette.ColorRole.Window: theme.ink, QPalette.ColorRole.WindowText: theme.text,
        QPalette.ColorRole.Base: theme.view, QPalette.ColorRole.Text: theme.text,
        QPalette.ColorRole.Button: theme.control, QPalette.ColorRole.ButtonText: theme.text,
        QPalette.ColorRole.Highlight: theme.accent, QPalette.ColorRole.HighlightedText: theme.on_accent or theme.ink,
        QPalette.ColorRole.Mid: theme.raised, QPalette.ColorRole.Dark: theme.raised, QPalette.ColorRole.Light: theme.control,
        QPalette.ColorRole.PlaceholderText: theme.muted,
    }
    out = QPalette()
    for role, rgb in colors.items():
        out.setColor(role, QColor(*rgb))
    return out


def flatten(image, rgb):
    """A picture with see-through parts laid on a solid colour."""
    flat = QImage(image.size(), QImage.Format.Format_RGB32)
    flat.fill(QColor(*rgb))
    painter = QPainter(flat)
    painter.drawImage(0, 0, image)
    painter.end()
    return flat


def open_scene(engine, scene, theme_id, folder, still=False):
    """Load a scene's harness with the real package in it; returns the shown view, or None."""
    # One engine for every scene: the `Plasmoid` stand-in is a singleton object, and Qt
    # lets such an object belong to one engine only.
    session = plasma_stubs.Session(theme_id, config=CONFIG, animations=not still)
    QGuiApplication.setPalette(palette(theme_id))      # the stand-in controls draw with it
    engine.clearComponentCache()
    view = QQuickView(engine, None)
    view.setColor(QColor("transparent"))
    session.prepare(engine)
    text, size = HARNESS[scene]
    harness = os.path.join(folder, "%s.qml" % scene)
    with open(harness, "w", encoding="utf-8") as fh:
        fh.write(text % sources(folder))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(harness))
    if view.status() != QQuickView.Status.Ready or not view.rootObject():
        messages.append("%s: did not load" % scene)
        return None
    view.show()
    view.requestActivate()
    view.session = session          # the fake shell must live as long as the scene
    return view


def run_scene(engine, scene, theme_id, folder, still, quick=False):
    view = open_scene(engine, scene, theme_id, folder, still)
    if view is None:
        return None
    size = HARNESS[scene][1]

    def step(ms):
        QTest.qWait(ms)

    step(150)
    if scene == "dock":
        # The pointer on the second icon: it and its neighbours grow.
        QTest.mouseMove(view, QPoint(size[0] // 2 - 120, size[1] - 40))
        step(120)
        QTest.mouseMove(view, QPoint(size[0] // 2 - 110, size[1] - 40))
    elif scene == "search":
        step(300)
        QTest.keyClick(view, Qt.Key.Key_O)
    step(min(SETTLE[scene], 400) if quick else SETTLE[scene])
    image = view.grabWindow()
    frames = []
    if scene == "switcher":
        popups = [w for w in QGuiApplication.allWindows() if w is not view and isinstance(w, QQuickWindow) and w.isVisible()]
        if not popups:
            messages.append("switcher: no popup opened")
            view.close()
            return None
        image = popups[-1].grabWindow()
        frames.append(("dialogs/background", QRectF(0, 0, image.width(), image.height())))
        for popup in popups:
            popup.close()
    if scene == "dock":
        panel = view.rootObject().findChild(QQuickItem, "panel")
        corner = panel.mapToScene(QPointF(0, 0))
        frames.append(("widgets/panel-background", QRectF(corner.x(), corner.y(), panel.width(), panel.height())))
    elif scene in ("launcher", "search", "control", "calendar"):
        frames.append(("dialogs/background", QRectF(0, 0, image.width(), image.height())))
    elif scene == "bar":
        for island in view.rootObject().findChildren(QQuickItem, "island"):
            corner = island.mapToScene(QPointF(0, 0))
            frames.append(("widgets/panel-background", QRectF(corner.x(), corner.y(), island.width(), island.height())))
    view.close()
    view.deleteLater()
    return image, frames


def compose(image, frames, theme_id, background=None):
    """The scene laid over its Plasma style frames, on a solid colour or see-through."""
    out = QImage(image.size(), QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(QColor(*background) if background else QColor(0, 0, 0, 0))
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for name, rect in frames:
        plasma_style.frame(painter, name, rect, theme_id)
    painter.drawImage(0, 0, image)
    painter.end()
    return out


def showcase(images, theme_id, path):
    """Wallpaper with the dock at the bottom, the launcher in the middle and the control popup at the top right."""
    base = images.get("wallpaper")
    if base is None or base.isNull():
        return False
    canvas = QImage(base.size(), QImage.Format.Format_ARGB32)
    painter = QPainter(canvas)
    painter.drawImage(0, 0, base)
    theme = themes.BY_ID[theme_id]
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    plasma_style.frame(painter, "widgets/panel-background", QRectF(0, 0, canvas.width(), 32), theme_id, borders=("bottom",))
    painter.setPen(QColor(*theme.text))
    font = QFont("Segoe UI", 10)
    painter.setFont(font)
    painter.drawText(canvas.rect().adjusted(0, 0, 0, -canvas.height() + 32), int(Qt.AlignmentFlag.AlignCenter), "Per 20 Kas  21:40")
    launcher = images.get("launcher")
    if launcher is not None and not launcher.isNull():
        scaled = launcher.scaledToWidth(int(canvas.width() * 0.56), Qt.TransformationMode.SmoothTransformation)
        painter.drawImage(int(canvas.width() * 0.06), 48, scaled)
    control = images.get("control")
    if control is not None and not control.isNull():
        painter.drawImage(canvas.width() - control.width() - 16, 40, control)
    dock = images.get("dock")
    if dock is not None and not dock.isNull():
        painter.drawImage((canvas.width() - dock.width()) // 2, canvas.height() - dock.height(), dock)
    painter.end()
    return canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("outdir", nargs="?", default="")
    parser.add_argument("--theme", default="cyan", choices=[t.id for t in themes.THEMES])
    parser.add_argument("--all-themes", action="store_true")
    parser.add_argument("--scenes", default=",".join(SCENES))
    parser.add_argument("--check", action="store_true", help="save nothing; exit 1 on any warning")
    parser.add_argument("--still", action="store_true", help="animations off")
    parser.add_argument("--lang", default="tr_TR", help="the session language the applets see (default tr_TR)")
    args = parser.parse_args()
    if not args.check and not args.outdir:
        parser.error("give a folder for the pictures, or --check")

    QLocale.setDefault(QLocale(args.lang))
    qInstallMessageHandler(remember)
    app = QGuiApplication(sys.argv[:1])
    app.setFont(QFont("Segoe UI", 10))
    folder = tempfile.mkdtemp(prefix="shell-preview-")
    plasma_stubs.register()
    engine = QQmlEngine()
    scenes = [s for s in args.scenes.split(",") if s]
    theme_ids = [t.id for t in themes.THEMES] if args.all_themes else [args.theme]
    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
    for theme_id in theme_ids:
        images = {}
        for scene in scenes:
            before = len(messages)
            result = run_scene(engine, scene, theme_id, folder, args.still, quick=args.check)
            for line in messages[before:]:
                print("[%s/%s] %s" % (theme_id, scene, line), file=sys.stderr)
            if result is None:
                continue
            image, frames = result
            images[scene] = compose(image, frames, theme_id)
            if not args.check:
                path = os.path.join(args.outdir, "%s-%s.png" % (scene, theme_id))
                compose(image, frames, theme_id, background=themes.BY_ID[theme_id].raised).save(path)
                print("saved", path)
        if not args.check and {"wallpaper", "dock", "launcher"} <= set(images):
            path = os.path.join(args.outdir, "showcase-%s.png" % theme_id)
            if showcase(images, theme_id, path):
                print("saved", path)
    print("warnings:", len(messages))
    print("calls:", len(plasma_stubs.CALLS))
    return 1 if messages else 0


if __name__ == "__main__":
    sys.exit(main())
