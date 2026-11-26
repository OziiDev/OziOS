import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Super+Shift+S: drag over part of the screen to save it (to Pictures and the
// clipboard). Esc or a right click cancels.
Window {
    id: shot
    property var shell
    readonly property var c: shell.c

    visible: false
    color: "transparent"
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-areashot"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityExclusive

    property point from: Qt.point(-1, -1)
    property point to: Qt.point(-1, -1)
    readonly property rect area: Qt.rect(Math.min(from.x, to.x), Math.min(from.y, to.y), Math.abs(to.x - from.x), Math.abs(to.y - from.y))
    readonly property bool dragging: from.x >= 0

    function start() { from = Qt.point(-1, -1); to = Qt.point(-1, -1); visible = true; keys.forceActiveFocus() }
    function cancel() { visible = false }

    // Dim the screen outside the chosen part.
    Rectangle { x: 0; y: 0; width: parent.width; height: shot.dragging ? shot.area.y : parent.height; color: Qt.rgba(0, 0, 0, 0.35) }
    Rectangle { visible: shot.dragging; x: 0; y: shot.area.y + shot.area.height; width: parent.width; height: parent.height - y; color: Qt.rgba(0, 0, 0, 0.35) }
    Rectangle { visible: shot.dragging; x: 0; y: shot.area.y; width: shot.area.x; height: shot.area.height; color: Qt.rgba(0, 0, 0, 0.35) }
    Rectangle { visible: shot.dragging; x: shot.area.x + shot.area.width; y: shot.area.y; width: parent.width - x; height: shot.area.height; color: Qt.rgba(0, 0, 0, 0.35) }
    Rectangle {
        visible: shot.dragging
        x: shot.area.x; y: shot.area.y; width: shot.area.width; height: shot.area.height
        color: "transparent"
        border.width: 1; border.color: "white"
    }
    Rectangle {
        visible: shot.dragging && shot.area.width > 0
        x: shot.area.x; y: Math.max(4, shot.area.y - height - 6)
        width: sizeText.implicitWidth + 14; height: 22; radius: 6
        color: Qt.rgba(0, 0, 0, 0.7)
        Text { id: sizeText; anchors.centerIn: parent; text: Math.round(shot.area.width) + " × " + Math.round(shot.area.height); color: "white"; font.pixelSize: 11 }
    }
    Rectangle {
        visible: !shot.dragging
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 60 }
        width: hint.implicitWidth + 28; height: 36; radius: 10
        color: shot.c.raised
        border.width: 1; border.color: Qt.alpha(shot.c.text, 0.10)
        Text { id: hint; anchors.centerIn: parent; text: Shell.tr("Drag over the part to save · Esc: cancel"); color: shot.c.text; font.pixelSize: 13 }
    }

    Item { id: keys; focus: true; Keys.onEscapePressed: shot.cancel() }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.CrossCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPressed: (ev) => {
            if (ev.button === Qt.RightButton) { shot.cancel(); return }
            shot.from = Qt.point(ev.x, ev.y); shot.to = shot.from
        }
        onPositionChanged: (ev) => { if (pressed && shot.dragging) shot.to = Qt.point(ev.x, ev.y) }
        onReleased: (ev) => {
            if (ev.button !== Qt.LeftButton || !shot.dragging) return
            const r = shot.area
            shot.visible = false
            // Let the overlay leave the screen before the picture is taken.
            saveLater.r = r
            saveLater.restart()
        }
    }
    Timer {
        id: saveLater
        property rect r
        interval: 180
        onTriggered: Shell.saveArea(r.x, r.y, r.width, r.height)
    }
}
