import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The dock: the apps button, pinned programs and the ones running, on a quiet
// shelf at the bottom. A dot under each running program, a short bar under the
// one in front. Right click: pin, new window, close.
Window {
    id: dock
    property var shell
    readonly property var c: shell.c
    signal launcher()

    readonly property int iconSize: 40
    visible: true
    color: "transparent"
    // The window never changes size: a dock that grew under the pointer would
    // move its own edge past it and flicker. It is tall enough for a name or
    // the menu above the icons; only the shelf (and the open menu) take the
    // pointer, the clear part above lets clicks through to the windows below.
    width: Screen.width > 0 ? Screen.width : 1366
    height: 250
    LS.Window.scope: "ozi-dock"
    LS.Window.layer: LS.Window.LayerTop
    LS.Window.anchors: LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: 70
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    // Dragging an icon along the dock moves it; where it will land shows as a line.
    property string dragId: ""
    property real dragX: 0
    readonly property var drop: {
        if (!dragId) return { index: -1, x: 0 }
        let n = 0, x = -1
        for (let i = 0; i < icons.count; i++) {
            const it = icons.itemAt(i)
            if (!it || it.modelData.id === dragId || !it.modelData.pinned) continue
            const left = it.x
            if (x < 0) x = left - row.spacing / 2
            if (left + it.width / 2 < dragX) { n++; x = left + it.width + row.spacing / 2 }
        }
        return { index: n, x: x }
    }

    function updateInput() {
        if (menu.visible)
            Shell.setInputRegion(dock, [0, 0, dock.width, dock.height])
        else
            Shell.setInputRegion(dock, [shelf.x, shelf.y, shelf.width, shelf.height + 8])
    }
    Component.onCompleted: Qt.callLater(updateInput)
    onWidthChanged: Qt.callLater(updateInput)
    onHeightChanged: Qt.callLater(updateInput)

    // With the menu open the whole window listens, so a click beside it
    // closes it; leaving the window upwards closes it too.
    HoverHandler {
        id: inside
        onHoveredChanged: if (!hovered && menu.visible) leaveTimer.restart()
    }
    Timer { id: leaveTimer; interval: 500; onTriggered: if (!inside.hovered) menu.close() }

    Rectangle {
        id: shelf
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 8 }
        height: 58
        width: row.width + 16
        radius: 16
        color: Qt.alpha(dock.c.raised, 0.92)
        border.width: 1
        border.color: Qt.alpha(dock.c.text, 0.08)
        Behavior on width { NumberAnimation { duration: dock.shell.ms(200); easing.type: Easing.OutCubic } }
        onXChanged: Qt.callLater(dock.updateInput)
        onWidthChanged: Qt.callLater(dock.updateInput)
    }

    Row {
        id: row
        anchors { horizontalCenter: shelf.horizontalCenter; verticalCenter: shelf.verticalCenter }
        spacing: 4

        DockItem {
            id: launcherButton
            baseSize: dock.iconSize
            c: dock.c
            animate: dock.shell.speed > 0
            hovered: launcherMouse.containsMouse
            pressed: launcherMouse.pressed
            name: "Uygulamalar"
            Rectangle {
                anchors.fill: parent
                radius: 10
                color: Qt.alpha(dock.c.text, 0.10)
                Glyph { anchors.centerIn: parent; kind: "apps"; color: dock.c.text; size: 20 }
            }
            MouseArea { id: launcherMouse; anchors.fill: parent; hoverEnabled: true; onClicked: dock.launcher() }
        }

        Rectangle { width: 1; height: dock.iconSize * 0.6; color: Qt.alpha(dock.c.text, 0.12); anchors.verticalCenter: parent.verticalCenter }

        Repeater {
            id: icons
            model: Shell.dock
            DockItem {
                id: item
                required property var modelData
                readonly property bool dragged: dock.dragId === modelData.id
                z: dragged ? 10 : 0
                opacity: dragged ? 0.85 : 1
                // Follows the pointer while dragged; its place in the row (x) stays.
                transform: Translate { x: item.dragged ? dock.dragX - item.x - item.width / 2 : 0 }
                baseSize: dock.iconSize
                c: dock.c
                animate: dock.shell.speed > 0
                running: modelData.windows.length > 0
                active: modelData.active
                windows: modelData.windows.length
                hovered: mouse.containsMouse && !menu.visible && !dock.dragId
                pressed: mouse.pressed
                name: modelData.name
                Image {
                    anchors.fill: parent
                    source: Shell.iconSource(item.modelData.icon)
                    sourceSize: Qt.size(96, 96)
                    smooth: true; mipmap: true
                }
                MouseArea {
                    id: mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                    property real startX: 0
                    property bool dragging: false
                    onPressed: (ev) => { startX = ev.x; dragging = false }
                    onPositionChanged: (ev) => {
                        if (!(pressedButtons & Qt.LeftButton)) return
                        if (!dragging && Math.abs(ev.x - startX) > 10) {
                            dragging = true
                            menu.close()
                            dock.dragId = item.modelData.id
                        }
                        // Local coordinates move with the icon; mapping undoes that.
                        if (dragging) dock.dragX = mouse.mapToItem(row, ev.x, 0).x
                    }
                    onReleased: {
                        if (!dragging) return
                        const to = dock.drop.index
                        dock.dragId = ""
                        if (to >= 0) Shell.movePin(item.modelData.id, to)
                    }
                    onCanceled: { dragging = false; dock.dragId = "" }
                    onClicked: (ev) => {
                        if (dragging) return
                        if (ev.button === Qt.RightButton) { menu.openFor(item); return }
                        menu.close()
                        if (ev.button === Qt.MiddleButton) { Shell.launch(item.modelData.id); return }
                        if (!item.running) item.bounce()
                        Shell.activateDockItem(item.modelData.id)
                    }
                }
            }
        }
    }

    Rectangle {
        visible: dock.dragId !== "" && dock.drop.x >= 0
        x: row.x + dock.drop.x - 1
        anchors.verticalCenter: shelf.verticalCenter
        width: 3; height: dock.iconSize; radius: 1.5
        color: dock.c.accent
    }

    // Right-click menu of a dock icon.
    Rectangle {
        id: menu
        property var target: null
        readonly property var app: target ? target.modelData : null
        visible: target !== null
        onVisibleChanged: Qt.callLater(dock.updateInput)
        width: 220
        height: menuColumn.height + 12
        radius: 12
        color: dock.c.raised
        border.width: 1
        border.color: Qt.alpha(dock.c.text, 0.10)
        x: target ? Math.max(8, Math.min(dock.width - width - 8, target.mapToItem(dock.contentItem, target.width / 2, 0).x - width / 2)) : 0
        anchors { bottom: shelf.top; bottomMargin: 8 }

        function openFor(item) { target = item }
        function close() { target = null }

        component MenuEntry: Rectangle {
            id: entry
            property string label
            property bool danger: false
            signal picked()
            width: menuColumn.width; height: 32; radius: 7
            color: entryMouse.containsMouse ? Qt.alpha(dock.c.text, 0.08) : "transparent"
            Text {
                anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                text: entry.label
                color: entry.danger ? dock.c.danger : dock.c.text
                font.pixelSize: 13
            }
            MouseArea { id: entryMouse; anchors.fill: parent; hoverEnabled: true; onClicked: { entry.picked(); menu.close() } }
        }

        Column {
            id: menuColumn
            anchors { top: parent.top; topMargin: 6; horizontalCenter: parent.horizontalCenter }
            width: parent.width - 12
            Text {
                width: parent.width
                leftPadding: 10; topPadding: 4; bottomPadding: 6
                text: menu.app ? menu.app.name : ""
                color: dock.c.muted; font.pixelSize: 12; font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            MenuEntry { label: "Yeni pencere"; onPicked: Shell.launch(menu.app.id) }
            MenuEntry {
                label: menu.app && menu.app.pinned ? "Dock'tan kaldır" : "Dock'a sabitle"
                onPicked: Shell.setPinned(menu.app.id, !menu.app.pinned)
            }
            MenuEntry {
                visible: !!menu.app && menu.app.windows.length > 0
                label: menu.app && menu.app.windows.length > 1 ? "Tüm pencereleri kapat" : "Kapat"
                danger: true
                onPicked: menu.app.windows.forEach(w => Shell.closeWindow(w))
            }
        }
    }

    // Clicking anywhere else closes the menu.
    MouseArea {
        anchors.fill: parent
        z: -1
        enabled: menu.visible
        onClicked: menu.close()
    }
}
