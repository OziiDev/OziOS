import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The dock: pinned programs and the ones running, on a floating glass shelf.
// Icons grow toward the pointer (DockItem), a light under each running one.
Window {
    id: dock
    property var shell
    readonly property var c: shell.c
    signal launcher()

    readonly property int iconSize: 44
    visible: true
    color: "transparent"
    width: shelf.width + 40
    height: 92
    LS.Window.layer: LS.Window.LayerTop
    LS.Window.anchors: LS.Window.AnchorBottom
    LS.Window.exclusionZone: 78
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    property real pointerX: -1000

    Rectangle {
        id: shelf
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 10 }
        height: 64
        width: row.width + 24
        radius: 22
        color: Qt.alpha(dock.c.raised, 0.9)
        border.width: 1
        border.color: Qt.alpha(dock.c.accent, 0.25)
        Behavior on width { NumberAnimation { duration: dock.shell.ms(240); easing.type: Easing.OutCubic } }

        // A thin line of the two theme colours along the top edge.
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: parent.radius; rightMargin: parent.radius }
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: Qt.alpha(dock.c.accent, 0) }
                GradientStop { position: 0.3; color: dock.c.accent }
                GradientStop { position: 0.7; color: dock.c.accent2 }
                GradientStop { position: 1; color: Qt.alpha(dock.c.accent2, 0) }
            }
            opacity: 0.8
        }
    }

    Row {
        id: row
        anchors { horizontalCenter: shelf.horizontalCenter; bottom: shelf.bottom; bottomMargin: 2 }
        spacing: 2

        DockItem {
            id: launcherButton
            baseSize: dock.iconSize
            accent: dock.c.accent
            lightColor: dock.c.text
            animate: dock.shell.speed > 0
            zoom: dock.zoomFor(launcherButton)
            hovered: launcherMouse.containsMouse
            pressed: launcherMouse.pressed
            Rectangle {
                anchors.fill: parent
                radius: width * 0.28
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: dock.c.accent }
                    GradientStop { position: 1; color: dock.c.accent2 }
                }
                Grid {
                    anchors.centerIn: parent
                    columns: 3; spacing: 4
                    Repeater { model: 9; Rectangle { width: 5; height: 5; radius: 1.5; color: dock.c.ink } }
                }
            }
            MouseArea { id: launcherMouse; anchors.fill: parent; hoverEnabled: true; onClicked: dock.launcher() }
        }

        Rectangle { width: 1; height: dock.iconSize * 0.7; color: Qt.alpha(dock.c.muted, 0.4); anchors.verticalCenter: parent.verticalCenter }

        Repeater {
            model: Shell.dock
            DockItem {
                id: item
                required property var modelData
                baseSize: dock.iconSize
                accent: dock.c.accent
                lightColor: dock.c.text
                animate: dock.shell.speed > 0
                running: modelData.windows.length > 0
                active: modelData.active
                windows: modelData.windows.length
                zoom: dock.zoomFor(item)
                hovered: mouse.containsMouse
                pressed: mouse.pressed
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
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: (ev) => {
                        if (ev.button === Qt.MiddleButton) { Shell.launch(item.modelData.id); return }
                        if (!item.running) item.bounce()
                        Shell.activateDockItem(item.modelData.id)
                    }
                    onPressAndHold: Shell.setPinned(item.modelData.id, !item.modelData.pinned)
                }
                // Name above the icon while the pointer is on it.
                Rectangle {
                    visible: mouse.containsMouse
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.top; bottomMargin: 18 }
                    width: tip.implicitWidth + 16; height: 24; radius: 12
                    color: dock.c.ink; border.color: Qt.alpha(dock.c.accent, 0.4)
                    Text { id: tip; anchors.centerIn: parent; text: item.modelData.name; color: dock.c.text; font.pixelSize: 12 }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onPositionChanged: (ev) => dock.pointerX = ev.x
        onExited: dock.pointerX = -1000
    }

    // Icons near the pointer grow, like a lens passing over the shelf.
    function zoomFor(item) {
        if (pointerX < 0 || !item) return 1
        const centre = item.mapToItem(dock.contentItem, item.width / 2, 0).x
        const d = Math.abs(pointerX - centre) / (iconSize * 2.2)
        return 1 + 0.45 * Math.max(0, Math.cos(Math.min(d, 1) * Math.PI / 2))
    }
}
