import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Notifications slide in under the bar on the right, stay a few seconds and
// leave on their own; a click runs the program's main action, × closes.
Window {
    id: win
    property var shell
    readonly property var c: shell.c

    visible: Notes.items.length > 0
    color: "transparent"
    width: 380
    height: Math.max(1, list.height + 12)
    LS.Window.scope: "ozi-notifications"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorRight
    LS.Window.margins.top: 50
    LS.Window.margins.right: 10
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    Column {
        id: list
        width: parent.width
        spacing: 8
        move: Transition { NumberAnimation { properties: "y"; duration: win.shell.ms(220); easing.type: Easing.OutCubic } }

        Repeater {
            model: Notes.items
            Rectangle {
                id: card
                required property var modelData
                width: list.width
                readonly property var buttons: modelData.actions.filter(a => a.key !== "default")
                height: Math.max(68, (buttons.length > 0 ? actionRow.y + actionRow.height : body.y + body.height) + 14)
                radius: 14
                color: win.c.raised
                border.width: 1
                border.color: modelData.critical ? win.c.danger : Qt.alpha(win.c.text, 0.08)

                // Arrive from the right.
                property real enter: 0
                Component.onCompleted: enter = 1
                Behavior on enter { NumberAnimation { duration: win.shell.ms(220); easing.type: Easing.OutCubic } }
                transform: Translate { x: (1 - card.enter) * 40 }
                opacity: enter

                // Time left; it waits while the pointer is on the card.
                QtObject {
                    id: lifeLine
                    property real life: 1
                    NumberAnimation on life {
                        from: 1; to: 0
                        duration: Math.max(1, card.modelData.timeout)
                        running: card.modelData.timeout > 0 && !hover.containsMouse
                        onFinished: Notes.expire(card.modelData.id)
                    }
                }

                Image {
                    id: icon
                    anchors { left: parent.left; top: parent.top; margins: 14 }
                    width: 36; height: 36
                    source: card.modelData.icon.startsWith("file://") || card.modelData.icon.startsWith("/")
                            ? (card.modelData.icon.startsWith("/") ? "file://" + card.modelData.icon : card.modelData.icon)
                            : Shell.iconSource(card.modelData.icon)
                    sourceSize: Qt.size(72, 72)
                    smooth: true; mipmap: true
                }
                Text {
                    id: summary
                    anchors { left: icon.right; right: closeButton.left; top: parent.top; leftMargin: 12; topMargin: 14; rightMargin: 6 }
                    text: card.modelData.summary || card.modelData.app
                    color: win.c.text
                    font.pixelSize: 14; font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    id: body
                    anchors { left: summary.left; right: parent.right; top: summary.bottom; topMargin: 3; rightMargin: 16 }
                    text: card.modelData.body
                    textFormat: Text.StyledText
                    color: win.c.muted
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    maximumLineCount: 4
                    elide: Text.ElideRight
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        const main = card.modelData.actions.find(a => a.key === "default")
                        if (main) Notes.invoke(card.modelData.id, "default")
                        else Notes.close(card.modelData.id)
                    }
                }
                // The program's own buttons ("Reply", "Open", ...).
                Row {
                    id: actionRow
                    visible: card.buttons.length > 0
                    anchors { left: summary.left; top: body.bottom; topMargin: 10 }
                    spacing: 6
                    Repeater {
                        model: card.buttons
                        Rectangle {
                            required property var modelData
                            width: actionText.implicitWidth + 24; height: 28; radius: 7
                            color: actionMouse.containsMouse ? Qt.alpha(win.c.text, 0.14) : Qt.alpha(win.c.text, 0.08)
                            Text { id: actionText; anchors.centerIn: parent; text: parent.modelData.label; color: win.c.text; font.pixelSize: 12 }
                            MouseArea { id: actionMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Notes.invoke(card.modelData.id, parent.modelData.key) }
                        }
                    }
                }
                Rectangle {
                    id: closeButton
                    anchors { right: parent.right; top: parent.top; margins: 10 }
                    width: 22; height: 22; radius: 6
                    color: closeMouse.containsMouse ? Qt.alpha(win.c.text, 0.10) : "transparent"
                    Glyph { anchors.centerIn: parent; kind: "close"; color: win.c.muted; size: 10 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Notes.close(card.modelData.id) }
                }
            }
        }
    }
}
