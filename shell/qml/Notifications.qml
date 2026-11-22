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
                height: Math.max(72, body.y + body.height + 14)
                radius: 18
                color: Qt.alpha(win.c.raised, 0.97)
                border.width: 1
                border.color: modelData.critical ? "#FF556E" : Qt.alpha(win.c.accent, 0.4)

                // Arrive from the right.
                property real enter: 0
                Component.onCompleted: enter = 1
                Behavior on enter { NumberAnimation { duration: win.shell.ms(320); easing.type: Easing.OutBack } }
                transform: Translate { x: (1 - card.enter) * 60 }
                opacity: enter

                // Time left, as a thin line of the theme colours along the bottom.
                Rectangle {
                    id: lifeLine
                    visible: card.modelData.timeout > 0
                    anchors { left: parent.left; bottom: parent.bottom; leftMargin: 18; bottomMargin: 5 }
                    height: 2; radius: 1
                    width: (parent.width - 36) * life
                    property real life: 1
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: win.c.accent }
                        GradientStop { position: 1; color: win.c.accent2 }
                    }
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
                Rectangle {
                    id: closeButton
                    anchors { right: parent.right; top: parent.top; margins: 10 }
                    width: 22; height: 22; radius: 11
                    color: closeMouse.containsMouse ? Qt.alpha("#FF556E", 0.3) : "transparent"
                    Text { anchors.centerIn: parent; text: "×"; color: win.c.muted; font.pixelSize: 16 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Notes.close(card.modelData.id) }
                }
            }
        }
    }
}
