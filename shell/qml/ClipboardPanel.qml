import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Super+V: the last texts copied. Click (or arrows and Enter) puts one back on
// the clipboard, ready for Ctrl+V; the bin forgets it. Kept in memory only.
Window {
    id: cb
    property var shell
    readonly property var c: shell.c
    readonly property var items: Shell.clipboard

    visible: false
    color: "transparent"
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-clipboard"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityExclusive

    property bool open: false
    property int current: 0
    property string copied: ""

    function toggle() { open ? close() : show() }
    function show() { current = 0; copied = ""; visible = true; open = true; list.forceActiveFocus() }
    function close() { open = false; hideTimer.restart() }
    function pick(i) {
        if (i < 0 || i >= items.length) return
        Shell.useClip(i)
        copied = Shell.tr("Copied: paste with Ctrl+V")
        closeSoon.restart()
    }
    Timer { id: hideTimer; interval: cb.shell.ms(140); onTriggered: if (!cb.open) cb.visible = false }
    Timer { id: closeSoon; interval: 450; onTriggered: cb.close() }

    MouseArea { anchors.fill: parent; onClicked: cb.close() }

    Rectangle {
        id: card
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 90 }
        width: 420
        height: Math.min(cb.height - 160, header.height + Math.max(90, list.contentHeight) + 28)
        radius: 16
        color: cb.c.raised
        border.width: 1
        border.color: Qt.alpha(cb.c.text, 0.08)
        opacity: cb.open ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: cb.shell.ms(140) } }
        MouseArea { anchors.fill: parent }

        Item {
            id: header
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
            height: 28
            Glyph { id: hIcon; kind: "clipboard"; color: cb.c.text; size: 16; anchors { left: parent.left; verticalCenter: parent.verticalCenter } }
            Text {
                anchors { left: hIcon.right; leftMargin: 10; verticalCenter: parent.verticalCenter }
                text: cb.copied || Shell.tr("Clipboard history")
                color: cb.copied ? cb.c.accent : cb.c.text
                font.pixelSize: 14; font.weight: Font.DemiBold
            }
            Rectangle {
                visible: cb.items.length > 0
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: clearText.implicitWidth + 20; height: 26; radius: 7
                color: clearMouse.containsMouse ? Qt.alpha(cb.c.text, 0.10) : "transparent"
                Text { id: clearText; anchors.centerIn: parent; text: Shell.tr("Clear all"); color: cb.c.muted; font.pixelSize: 12 }
                MouseArea { id: clearMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Shell.forgetClip(-1) }
            }
        }

        ListView {
            id: list
            anchors { left: parent.left; right: parent.right; top: header.bottom; bottom: parent.bottom; margins: 10; topMargin: 8 }
            clip: true
            spacing: 4
            model: cb.items
            currentIndex: cb.current
            focus: true
            boundsBehavior: Flickable.StopAtBounds
            Keys.onEscapePressed: cb.close()
            Keys.onUpPressed: cb.current = Math.max(0, cb.current - 1)
            Keys.onDownPressed: cb.current = Math.min(cb.items.length - 1, cb.current + 1)
            Keys.onReturnPressed: cb.pick(cb.current)
            Keys.onEnterPressed: cb.pick(cb.current)
            Keys.onDeletePressed: Shell.forgetClip(cb.current)
            delegate: Rectangle {
                id: entry
                required property var modelData
                required property int index
                width: list.width
                height: Math.min(76, text.implicitHeight + 20)
                radius: 10
                color: index === cb.current ? Qt.alpha(cb.c.accent, 0.16)
                     : entryMouse.containsMouse ? Qt.alpha(cb.c.text, 0.06) : Qt.alpha(cb.c.text, 0.03)
                Text {
                    id: text
                    anchors { left: parent.left; right: bin.left; verticalCenter: parent.verticalCenter; leftMargin: 12; rightMargin: 6 }
                    text: entry.modelData.length > 400 ? entry.modelData.slice(0, 400) + "…" : entry.modelData
                    textFormat: Text.PlainText
                    color: cb.c.text
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
                MouseArea { id: entryMouse; anchors.fill: parent; hoverEnabled: true; onClicked: cb.pick(entry.index) }
                Rectangle {
                    id: bin
                    anchors { right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                    width: 28; height: 28; radius: 7
                    opacity: entryMouse.containsMouse || binMouse.containsMouse ? 1 : 0
                    color: binMouse.containsMouse ? Qt.alpha(cb.c.danger, 0.18) : "transparent"
                    Glyph { anchors.centerIn: parent; kind: "trash"; color: binMouse.containsMouse ? cb.c.danger : cb.c.muted; size: 14 }
                    MouseArea { id: binMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Shell.forgetClip(entry.index) }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: cb.items.length === 0
                width: parent.width - 40
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: Shell.tr("Nothing copied yet. Text you copy collects here.")
                color: cb.c.muted; font.pixelSize: 13
            }
        }
    }
}
