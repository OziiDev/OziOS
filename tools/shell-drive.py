"""Drive the OziOS applets with real pointer and key events and report what they did.

    python3 tools/shell-drive.py        prints one JSON object

It loads the dock, the launcher, the control widget, the islands at the top
(desktops and clock) and the wallpaper the same
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
from PyQt6.QtGui import QGuiApplication, QWheelEvent  # noqa: E402
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


def drive_switcher(engine, folder):
    view = preview.open_scene(engine, "switcher", "cyan", folder)
    QTest.qWait(500)
    switcher = view.rootObject().findChild(QObject, "applet").property("item")
    popups = [w for w in QGuiApplication.allWindows() if w is not view and w.isVisible() and hasattr(w, "contentItem")]
    out = {"popup": bool(popups), "current": switcher.property("currentIndex")}
    if not popups:
        view.close()
        return out
    popup = popups[-1]
    popup.requestActivate()
    QTest.qWait(100)
    QTest.keyClick(popup, Qt.Key.Key_Right)
    QTest.qWait(100)
    out["after_right"] = switcher.property("currentIndex")
    QTest.keyClick(popup, Qt.Key.Key_Left)
    QTest.keyClick(popup, Qt.Key.Key_Left)
    QTest.qWait(100)
    out["after_two_lefts"] = switcher.property("currentIndex")
    cards = [c for c in visual_tree(popup.contentItem()) if c.metaObject().className().startswith("QQuickMouseArea")
             and c.property("index") is not None]
    cards.sort(key=lambda c: c.property("index"))
    out["cards"] = len(cards)
    plasma_stubs.CALLS.clear()
    if len(cards) > 3:
        point = cards[3].mapToScene(QPointF(cards[3].width() / 2, cards[3].height() / 3))
        QTest.mouseClick(popup, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(int(point.x()), int(point.y())))
        QTest.qWait(100)
    out["click"] = calls()
    for window in popups:
        window.close()
    view.close()
    return out


def wheel(view, item, steps):
    """Turn the mouse wheel over `item`: positive steps scroll down."""
    point = QPointF(centre(view, item))
    for _ in range(abs(steps)):
        event = QWheelEvent(point, QPointF(view.mapToGlobal(point)), QPoint(0, 0), QPoint(0, -120 if steps > 0 else 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QGuiApplication.sendEvent(view, event)
        QTest.qWait(80)


def drive_bar(engine, folder):
    view = preview.open_scene(engine, "bar", "cyan", folder)
    QTest.qWait(600)
    lights = [o for o in visual_tree(view.rootObject()) if o.property("occupied") is not None]
    lights.sort(key=lambda o: o.mapToScene(QPointF(0, 0)).x())

    def state():
        return {"current": [bool(o.property("current")) for o in lights],
                "widths": [round(o.width()) for o in lights]}

    out = {"lights": len(lights), "occupied": [bool(o.property("occupied")) for o in lights], "start": state()}
    if len(lights) > 2:
        click(view, lights[2])
        QTest.qWait(1200)                         # the pill springs over and settles
        out["after_click"] = state()
        wheel(view, lights[2], 1)
        QTest.qWait(300)
        out["after_wheel_down"] = state()["current"]
        wheel(view, lights[2], -3)
        QTest.qWait(300)
        out["after_three_up"] = state()["current"]

    # The clock in the middle: time, dot and date; a click opens the calendar.
    labels = [o for o in visual_tree(view.rootObject()) if "Label" in o.metaObject().className()
              or o.metaObject().className().startswith("QQuickText")]
    out["clock"] = [o.property("text") for o in labels if o.property("text")]
    view.close()
    return out


def drive_calendar(engine, folder):
    view = preview.open_scene(engine, "calendar", "cyan", folder)
    QTest.qWait(500)
    tree = visual_tree(view.rootObject())
    cells = [o for o in tree if o.property("inMonth") is not None]
    out = {"cells": len(cells),
           "today": [o.property("index") for o in cells if o.property("today")],
           "in_month": sum(1 for o in cells if o.property("inMonth"))}
    popup = [o for o in tree if o.property("shown") is not None]
    if popup:
        out["month"] = popup[0].property("shown").toString("yyyy-MM") if hasattr(popup[0].property("shown"), "toString") else str(popup[0].property("shown"))
    buttons = [o for o in tree if "ToolButton" in o.metaObject().className()]
    buttons.sort(key=lambda o: o.mapToScene(QPointF(0, 0)).x())
    if len(buttons) >= 2 and popup:
        click(view, buttons[1])                  # next month
        click(view, buttons[1])
        shown = popup[0].property("shown")
        out["two_months_on"] = shown.toString("yyyy-MM") if hasattr(shown, "toString") else str(shown)
        tree = visual_tree(view.rootObject())
        out["today_after"] = [o.property("index") for o in tree if o.property("today")]
    view.close()
    return out


def turning(figure, wait=300):
    """Whether the figure moved on during the wait."""
    before = figure.property("t")
    QTest.qWait(wait)
    return figure.property("t") != before


def drive_wallpaper(engine, folder):
    view = preview.open_scene(engine, "wallpaper", "cyan", folder)
    QTest.qWait(300)
    items = [view.rootObject()] + view.rootObject().findChildren(QQuickItem)
    figure = [o for o in items if o.property("speed") is not None]
    wallpaper = [o for o in items if o.property("clock") is not None]
    out = {"turning": bool(figure) and turning(figure[0])}
    # The light effects profile: the wallpaper holds still.
    if wallpaper:
        wallpaper[0].setProperty("configuration", {"Animated": False})
        out["turning_in_light_profile"] = bool(figure) and turning(figure[0])
        wallpaper[0].setProperty("configuration", {})
    # A maximized window: the wallpaper stops.
    if plasma_stubs.INSTANCES:
        plasma_stubs.INSTANCES[-1].change(0, IsMaximized=True)
        QTest.qWait(200)
    out["turning_when_covered"] = bool(figure) and turning(figure[0])
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
                        ("bar", drive_bar), ("calendar", drive_calendar),
                        ("switcher", drive_switcher), ("wallpaper", drive_wallpaper)):
        try:
            result[name] = drive(engine, folder)
        except Exception as err:                 # report it with the rest instead of stopping
            result[name] = {"error": "%s: %s" % (type(err).__name__, err)}
    result["warnings"] = list(preview.messages)
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
