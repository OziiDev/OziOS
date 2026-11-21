"""Drive the OziOS logout screen and report what it did.

    python3 tools/logout-drive.py [--shot DIR]     prints one JSON object

Plasma's logout greeter (ksmserver-logout-greeter) loads
desktop/look-and-feel/org.ozios.desktop/contents/logout/Logout.qml with a
context of its own (what was asked for, whether this user may shut down, the
ways to sleep) and acts on the signals the screen sends. This loads the real
file the same way, on top of the stand-ins in tools/plasma_stubs.py, in a few
of those situations, presses keys and clicks, and records the signals.
tests/test_desktop.py checks the answers. With --shot, pictures of the screen
go to DIR, in English and in Turkish.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PyQt6.QtCore import QLocale, QObject, QPoint, QPointF, QRect, Qt, QUrl, pyqtSlot, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication  # noqa: E402
from PyQt6.QtQuick import QQuickItem, QQuickView  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

import plasma_stubs  # noqa: E402

LOGOUT = os.path.join(ROOT, "desktop", "look-and-feel", "org.ozios.desktop", "contents", "logout", "Logout.qml")
SIGNALS = ("logoutRequested", "haltRequested", "haltUpdateRequested", "suspendRequested", "rebootRequested",
           "rebootRequested2", "rebootUpdateRequested", "cancelRequested", "lockScreenRequested")
DEFAULT, NONE, REBOOT, HALT = -1, 0, 1, 2

# Loads the screen with the given first values and passes every signal it sends to the recorder.
HARNESS = """
import QtQuick
Loader {
    id: loader
    focus: true
    Component.onCompleted: setSource(screenUrl, firstValues)
    onLoaded: {
        for (const name of signalNames)
            item[name].connect(function (value) { recorder.heard(name, value === undefined ? -1 : value) })
        item.forceActiveFocus()
    }
}
"""

warnings = []


def visual_tree(item):
    """Every item under `item`. Delegates made by a Repeater have no QObject parent."""
    out = []
    for child in item.childItems():
        out.append(child)
        out.extend(visual_tree(child))
    return out


def remember(mode, context, message):
    warnings.append("%s:%s: %s" % (os.path.basename(context.file or "?"), context.line, message))


class Recorder(QObject):
    def __init__(self):
        super().__init__()
        self.signals = []

    @pyqtSlot(str, int)
    def heard(self, name, value):
        self.signals.append([name] if value == -1 else [name, value])


class Screen:
    """One logout screen, as the greeter would show it."""

    def __init__(self, folder, sdtype=DEFAULT, update=False, maysd=True, can_logout=True, suspend=True,
                 hibernate=False, others=0, locale="en_US", size=(1280, 800), first=None, entry=""):
        QLocale.setDefault(QLocale(locale))
        plasma_stubs.SESSIONS["others"] = others
        self.recorder = Recorder()
        self.view = QQuickView()
        self.view.setColor(QColor("#1B2433"))         # a dark desktop behind, for the pictures
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.resize(*size)
        ctx = self.view.rootContext()
        values = {"screenGeometry": QRect(0, 0, *size), "sdtype": sdtype, "maysd": maysd, "canLogout": can_logout,
                  "spdMethods": {"SuspendState": suspend, "HibernateState": hibernate, "HybridSuspendState": False},
                  "softwareUpdatePending": update, "isUefi": True, "rebootToFirmwareSetup": False,
                  "rebootToBootLoaderMenu": False, "rebootToBootLoaderEntry": entry,
                  "screenUrl": QUrl.fromLocalFile(LOGOUT).toString(), "firstValues": first or {},
                  "signalNames": list(SIGNALS)}
        for name, value in values.items():
            ctx.setContextProperty(name, value)
        ctx.setContextProperty("recorder", self.recorder)
        path = os.path.join(folder, "harness.qml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(HARNESS)
        self.view.setSource(QUrl.fromLocalFile(path))
        self.view.show()
        self.view.requestActivate()
        QTest.qWait(1300)                    # the tiles have risen in
        self.root = self.view.rootObject().property("item")

    @property
    def heard(self):
        return self.recorder.signals

    def tiles(self):
        found = [t for t in visual_tree(self.root) if t.objectName().startswith("tile-")]
        found.sort(key=lambda t: t.mapToScene(QPointF(0, 0)).x())
        return found

    def names(self):
        return [t.objectName()[5:] for t in self.tiles()]

    def titles(self):
        return [t.property("title") for t in self.tiles()]

    def current(self):
        choices = self.root.property("choices")
        if hasattr(choices, "toVariant"):
            choices = choices.toVariant()
        return choices[self.root.property("current")]["key"]

    def click(self, item, x=0.5, y=0.5):
        point = item.mapToScene(QPointF(item.width() * x, item.height() * y))
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(int(point.x()), int(point.y())))
        QTest.qWait(50)

    def tile(self, name):
        return next(t for t in self.tiles() if t.objectName() == "tile-" + name)

    def key(self, key):
        QTest.keyClick(self.view, key)
        QTest.qWait(50)

    def notes(self):
        return [t.property("text") for t in visual_tree(self.root) if t.objectName() == "note"]

    def shot(self, path):
        self.view.grabWindow().save(path)

    def close(self):
        self.view.close()
        self.view.deleteLater()
        QTest.qWait(20)


def main():
    shots = sys.argv[sys.argv.index("--shot") + 1] if "--shot" in sys.argv else None
    qInstallMessageHandler(remember)
    app = QGuiApplication(sys.argv[:1])  # noqa: F841
    plasma_stubs.register()
    import tempfile
    folder = tempfile.mkdtemp(prefix="logout-drive-")
    out = {}

    s = Screen(folder)
    out["all"] = {"tiles": s.names(), "current": s.current(), "titles": s.titles()}
    s.key(Qt.Key.Key_Right)
    out["all"]["after_right"] = s.current()
    s.key(Qt.Key.Key_Return)
    out["all"]["enter"] = s.heard[:]
    for name in ("lock", "sleep", "reboot", "halt"):
        s.click(s.tile(name))
    out["all"]["clicks"] = s.heard[1:]
    del s.heard[:]
    s.key(Qt.Key.Key_Escape)
    s.click(s.root, 0.5, 0.97)                       # beside the tiles
    s.click(next(c for c in visual_tree(s.root) if c.objectName() == "cancel"))
    out["all"]["cancel"] = s.heard[:]
    if shots:
        s.root.setProperty("current", 3)
        QTest.qWait(400)
        s.shot(os.path.join(shots, "logout-en.png"))
    s.close()

    # A restart asked for by a program: that tile alone, counting down, then restarting.
    s = Screen(folder, sdtype=REBOOT, first={"timeout": 2})
    out["reboot"] = {"tiles": s.names(), "notes": s.notes()}
    QTest.qWait(2200)
    out["reboot"]["heard"] = s.heard[:]
    s.close()

    # Any key stops the count.
    s = Screen(folder, sdtype=REBOOT, first={"timeout": 2})
    s.key(Qt.Key.Key_Left)
    QTest.qWait(2200)
    out["reboot_stopped"] = {"heard": s.heard[:]}
    s.close()

    s = Screen(folder, sdtype=NONE, first={"timeout": 30})
    out["logout"] = {"tiles": s.names(), "notes": s.notes()}
    s.close()

    s = Screen(folder, update=True, hibernate=True, others=2)
    out["updates"] = {"tiles": s.names(), "badges": [t.objectName()[5:] for t in s.tiles() if t.property("badge")],
                      "current": s.current(), "notes": s.notes()}
    s.click(s.tile("reboot-update"))
    s.click(s.tile("hibernate"))
    out["updates"]["heard"] = s.heard[:]
    s.close()

    s = Screen(folder, maysd=False, can_logout=False, suspend=False)
    out["guest"] = {"tiles": s.names()}
    s.close()

    s = Screen(folder, locale="tr_TR", size=(1024, 640))
    out["turkish"] = {"titles": s.titles(), "fits": all(0 <= t.mapToScene(QPointF(0, 0)).x() and
                                                         t.mapToScene(QPointF(t.width(), 0)).x() <= 1024
                                                         for t in s.tiles())}
    if shots:
        s.view.resize(1280, 800)
        QTest.qWait(300)
        s.shot(os.path.join(shots, "logout-tr.png"))
    s.close()

    if shots:
        s = Screen(folder, sdtype=REBOOT, locale="tr_TR", first={"timeout": 30})
        QTest.qWait(1200)
        s.shot(os.path.join(shots, "logout-reboot-tr.png"))
        s.close()

    out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
