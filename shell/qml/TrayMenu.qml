import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The menu of a tray icon (what the program offers: open, mute, quit...),
// under the icon. A click outside or Esc closes it.
Window {
    id: tm
    property var shell
    readonly property var c: shell.c
    property real anchorX: width - 120
    property string service: ""
    property var entries: []
    property bool open: false
    // With any tick in the menu, every label leaves room for one, so they line up.
    readonly property bool ticks: entries.some(e => e.toggle !== "")

    visible: false
    color: "transparent"
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-tray-menu"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityOnDemand

    function openWith(svc, list) {
        if (!list || list.length === 0) return
        service = svc
        entries = list
        visible = true
        open = true
        card.forceActiveFocus()
    }
    function close() { open = false; hideTimer.restart() }
    Timer { id: hideTimer; interval: tm.shell.ms(120); onTriggered: if (!tm.open) tm.visible = false }

    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onClicked: tm.close() }

    Rectangle {
        id: card
        width: 260
        height: column.height + 12
        x: Math.max(8, Math.min(tm.width - width - 8, tm.anchorX - width / 2))
        y: 40
        radius: 12
        color: tm.c.raised
        border.width: 1
        border.color: Qt.alpha(tm.c.text, 0.10)
        opacity: tm.open ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: tm.shell.ms(120) } }
        focus: true
        Keys.onEscapePressed: tm.close()
        MouseArea { anchors.fill: parent }

        Column {
            id: column
            anchors { top: parent.top; topMargin: 6; horizontalCenter: parent.horizontalCenter }
            width: parent.width - 12
            Repeater {
                model: tm.entries
                Item {
                    id: row
                    required property var modelData
                    width: column.width
                    height: modelData.separator ? 9 : 32
                    Rectangle {
                        visible: row.modelData.separator
                        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
                        height: 1
                        color: Qt.alpha(tm.c.text, 0.10)
                    }
                    Rectangle {
                        visible: !row.modelData.separator
                        anchors.fill: parent
                        radius: 7
                        color: entryMouse.containsMouse && row.modelData.enabled && !row.modelData.submenu
                               ? Qt.alpha(tm.c.text, 0.08) : "transparent"
                        Text {
                            id: check
                            visible: tm.ticks
                            anchors { left: parent.left; leftMargin: 10 + row.modelData.depth * 14; verticalCenter: parent.verticalCenter }
                            text: row.modelData.checked ? (row.modelData.toggle === "radio" ? "●" : "✓") : ""
                            width: 14
                            color: tm.c.accent; font.pixelSize: 12
                        }
                        Text {
                            anchors {
                                left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter
                                leftMargin: 10 + row.modelData.depth * 14 + (check.visible ? 18 : 0); rightMargin: 10
                            }
                            text: row.modelData.label
                            elide: Text.ElideRight
                            color: !row.modelData.enabled ? Qt.alpha(tm.c.text, 0.35)
                                 : row.modelData.submenu ? tm.c.muted : tm.c.text
                            font.pixelSize: 13
                            font.weight: row.modelData.submenu ? Font.DemiBold : Font.Normal
                        }
                        MouseArea {
                            id: entryMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: row.modelData.enabled && !row.modelData.submenu
                            onClicked: { Tray.menuClick(tm.service, row.modelData.id); tm.close() }
                        }
                    }
                }
            }
        }
    }
}
