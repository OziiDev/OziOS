"""Drive the OziOS applets with real pointer and key events and report what they did.

    python3 tools/shell-drive.py        prints one JSON object

It loads the dock, the launcher, the control widget and the wallpaper the same
way tools/shell-preview.py does (the real QML on top of the stand-ins in
tools/plasma_stubs.py), clicks, hovers and types into them, and records what
each one asked Plasma or the shell to do. tests/test_desktop.py checks the
answers. The session language is English, so the checks do not depend on the
machine's language.
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
spec = importlib.util.spec_from_file_location("shell_preview", os.path.join(HERE, "shell-preview.py"))
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)

from PyQt6.QtCore import QLocale, QMetaObject, QModelIndex, QObject, QPoint, QPointF, Qt, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QGuiApplication  # noqa: E402
from PyQt6.QtQml import QJSValue, QQmlEngine  # noqa: E402
from PyQt6.QtQuick import QQuickItem  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

import plasma_stubs  # noqa: E402


def visual_tree(item):
    """Every item under `item`, following the visual tree. QObject children are not enough:
    delegates made by a Repeater or a view have no QObject parent."""
    out = []
    for child in item.childItems():
        out.append(child)
        out.extend(visual_tree(child))
    return out


def items(view, class_prefix):
    """The Qt Quick items of a scene whose class name starts with `class_prefix`."""
    return [o for o in visual_tree(view.rootObject()) if o.metaObject().className().startswith(class_prefix)]


def centre(view, item):
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return QPoint(int(point.x()), int(point.y()))


def click(view, item, button=Qt.MouseButton.LeftButton):
    QTest.mouseClick(view, button, Qt.KeyboardModifier.NoModifier, centre(view, item))
    QTest.qWait(60)


def value(v):
    return v.toVariant() if isinstance(v, QJSValue) else v


def delegates(view, list_view):
    content = list_view.property("contentItem")
    out = [d for d in content.childItems() if d.property("index") is not None]
    return sorted(out, key=lambda d: d.property("index"))


def calls():
    return [list(c) for c in plasma_stubs.CALLS]


def drive_dock(engine, folder):
    view = preview.open_scene(engine, "dock", "cyan", folder)
    QTest.qWait(400)
    list_view = items(view, "QQuickListView")[0]
    tasks = delegates(view, list_view)
    out = {"count": len(tasks)}

    # The pointer on the second icon: it grows most, the far ones not at all.
    QTest.mouseMove(view, centre(view, tasks[1]))
    QTest.qWait(700)
    faces = [t.findChildren(QQuickItem)[0] for t in tasks]
    out["zoom"] = [round(float(f.property("shownZoom") or 1), 3) for f in faces]
    QTest.mouseMove(view, QPoint(2, 2))
    QTest.qWait(600)
    out["zoom_after"] = [round(float(f.property("shownZoom") or 1), 3) for f in faces]

    plasma_stubs.CALLS.clear()
    click(view, tasks[0])                                   # Firefox: active window
    click(view, tasks[1])                                   # Dolphin: two windows, not active
    click(view, tasks[2])                                   # Konsole: pinned, not running
    click(view, tasks[3], Qt.MouseButton.MiddleButton)      # Steam: a new instance
    out["clicks"] = calls()

    # Right click opens the menu; its "Pin" entry pins the program and saves the list.
    plasma_stubs.CALLS.clear()
    click(view, tasks[0], Qt.MouseButton.RightButton)
    menus = [o for o in tasks[0].findChildren(QObject) if o.metaObject().className().startswith("Menu_QMLTYPE")]
    out["menu_opened"] = bool(menus) and int(menus[0].property("timesOpened") or 0) > 0
    entries = [o for o in menus[0].findChildren(QObject) if o.metaObject().className().startswith("MenuItem_QMLTYPE")] if menus else []
    out["menu"] = [e.property("text") for e in entries if e.property("visible")]
    pin = [e for e in entries if (e.property("text") or "").startswith("Pin")]
    if pin:
        QMetaObject.invokeMethod(pin[0], "clicked")
        QTest.qWait(100)
    out["pin_calls"] = calls()
    out["saved_launchers"] = list(value(plasma_stubs.STATE.configuration.value("launchers")) or [])
    out["status"] = plasma_stubs.STATE.status
    view.close()
    return out


def drive_launcher(engine, folder):
    view = preview.open_scene(engine, "launcher", "cyan", folder)
    QTest.qWait(900)
    applet = view.rootObject().findChild(QObject, "applet").property("item")
    out = {"expanded": applet.property("expanded")}
    grid = items(view, "QQuickGridView")[0]
    out["programs"] = grid.property("count")
    chips = items(view, "QQuickListView")[0]
    out["categories"] = chips.property("count")

    plasma_stubs.CALLS.clear()
    tiles = delegates(view, grid)
    click(view, tiles[0])
    out["click"] = calls()
    out["closed_after_launch"] = not applet.property("expanded")

    # Open again: typing goes to the search field, Return starts the first result.
    applet.setProperty("expanded", True)
    QTest.qWait(500)
    grid = items(view, "QQuickGridView")[0]          # the popup's content is new each time it opens
    plasma_stubs.CALLS.clear()
    for key in (Qt.Key.Key_F, Qt.Key.Key_I, Qt.Key.Key_R, Qt.Key.Key_E):
        QTest.keyClick(view, key)
    QTest.qWait(300)
    out["results"] = grid.property("count")
    QTest.keyClick(view, Qt.Key.Key_Return)
    QTest.qWait(150)
    out["search"] = calls()

    # A category chip narrows the grid.
    applet.setProperty("expanded", True)
    QTest.qWait(500)
    grid = items(view, "QQuickGridView")[0]
    chips = items(view, "QQuickListView")[0]
    chip_items = delegates(view, chips)
    click(view, chip_items[2])
    QTest.qWait(300)
    out["category_programs"] = grid.property("count")

    # The power buttons: the last one shuts down.
    plasma_stubs.CALLS.clear()
    buttons = [m for m in items(view, "QQuickMouseArea") if (m.objectName() or "").startswith("power-") and m.isVisible()]
    buttons.sort(key=lambda m: m.mapToScene(QPointF(0, 0)).x())
    out["power_buttons"] = [m.objectName()[len("power-"):] for m in buttons]
    if buttons:
        click(view, buttons[-1])
    out["power"] = calls()
    view.close()
    return out


def drive_control(engine, folder):
    view = preview.open_scene(engine, "control", "cyan", folder)
    QTest.qWait(600)
    plasma_stubs.CALLS.clear()
    swatches = [m for m in items(view, "QQuickMouseArea") if (m.objectName() or "").startswith("theme-")]
    swatches.sort(key=lambda m: m.mapToScene(QPointF(0, 0)).x())
    out = {"swatches": [m.objectName()[len("theme-"):] for m in swatches]}
    aurora = [m for m in swatches if m.objectName() == "theme-aurora"]
    if aurora:
        click(view, aurora[0])
    controls = visual_tree(view.rootObject())
    buttons = [b for b in controls if "ToolButton" in b.metaObject().className() and b.property("text") == "Off"]
    if buttons:
        click(view, buttons[0])
    switches = [s for s in controls if "Switch" in s.metaObject().className()]
    if switches:
        click(view, switches[0])
    QTest.qWait(200)
    out["commands"] = [c[2] for c in plasma_stubs.CALLS if c[0] == "shell"]
    view.close()
    return out


def drive_wallpaper(engine, folder):
    view = preview.open_scene(engine, "wallpaper", "cyan", folder)
    QTest.qWait(300)
    figure = [o for o in view.rootObject().findChildren(QQuickItem) if o.property("speed") is not None]
    out = {"turning": bool(figure) and bool(figure[0].property("running"))}
    # A maximized window: the wallpaper stops.
    if plasma_stubs.INSTANCES:
        plasma_stubs.INSTANCES[-1].change(0, IsMaximized=True)
        QTest.qWait(200)
    out["turning_when_covered"] = bool(figure) and bool(figure[0].property("running"))
    view.close()
    return out


def main():
    QLocale.setDefault(QLocale("en_US"))
    qInstallMessageHandler(preview.remember)
    app = QGuiApplication(sys.argv[:1])
    folder = tempfile.mkdtemp(prefix="shell-drive-")
    plasma_stubs.register()
    engine = QQmlEngine()
    result = {}
    for name, drive in (("dock", drive_dock), ("launcher", drive_launcher), ("control", drive_control),
                        ("wallpaper", drive_wallpaper)):
        try:
            result[name] = drive(engine, folder)
        except Exception as err:                 # report it with the rest instead of stopping
            result[name] = {"error": "%s: %s" % (type(err).__name__, err)}
    result["warnings"] = list(preview.messages)
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
