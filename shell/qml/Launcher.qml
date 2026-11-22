import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The launcher: Super or the dock's grid button. Type to search, arrows and
// Enter to start, Esc or a click outside to close. Power actions at the bottom.
Window {
    id: launcher
    property var shell
    readonly property var c: shell.c

    visible: false
    color: "transparent"
    // Always a real size: when Qt shows the window again it sends the size before
    // the anchors, and a 0 size without anchors is a protocol error that ends the shell.
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-launcher"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityExclusive

    property bool open: false
    property var results: Shell.apps
    property int current: 0

    function toggle() { open ? close() : show() }
    function show() {
        query.text = ""
        results = Shell.apps
        current = 0
        visible = true
        open = true
        query.forceActiveFocus()
    }
    function close() { open = false; hideTimer.restart() }
    function start(app) { if (app) { Shell.launch(app.id); close() } }

    Timer { id: hideTimer; interval: launcher.shell.ms(180); onTriggered: if (!launcher.open) launcher.visible = false }

    // Dim everything behind; a click there closes.
    Rectangle {
        anchors.fill: parent
        color: Qt.alpha(launcher.c.ink, 0.72)
        opacity: launcher.open ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: launcher.shell.ms(180) } }
        MouseArea { anchors.fill: parent; onClicked: launcher.close() }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 860)
        height: Math.min(parent.height - 80, 620)
        radius: 26
        color: Qt.alpha(launcher.c.raised, 0.97)
        border.width: 1
        border.color: Qt.alpha(launcher.c.accent, 0.35)
        opacity: launcher.open ? 1 : 0
        scale: launcher.open ? 1 : 0.94
        Behavior on opacity { NumberAnimation { duration: launcher.shell.ms(200) } }
        Behavior on scale { NumberAnimation { duration: launcher.shell.ms(320); easing.type: Easing.OutBack; easing.overshoot: 1.6 } }
        MouseArea { anchors.fill: parent }  // clicks on the card stay on the card

        readonly property var greeting: {
            const h = new Date().getHours()
            return h < 6 ? "İyi geceler" : h < 12 ? "Günaydın" : h < 18 ? "İyi günler" : "İyi akşamlar"
        }

        Column {
            anchors { fill: parent; margins: 28 }
            spacing: 18

            Text {
                text: card.greeting
                color: launcher.c.text
                font.pixelSize: 26; font.weight: Font.Bold
            }

            // Search field.
            Rectangle {
                width: parent.width; height: 48; radius: 24
                color: launcher.c.control
                border.width: query.activeFocus ? 2 : 1
                border.color: query.activeFocus ? launcher.c.accent : Qt.alpha(launcher.c.muted, 0.3)
                Glyph { kind: "search"; color: launcher.c.muted; anchors { left: parent.left; leftMargin: 18 } size: 18 }
                TextInput {
                    id: query
                    anchors { fill: parent; leftMargin: 48; rightMargin: 18 }
                    verticalAlignment: TextInput.AlignVCenter
                    color: launcher.c.text
                    selectionColor: launcher.c.accent
                    font.pixelSize: 16
                    onTextChanged: { launcher.results = Shell.search(text); launcher.current = 0 }
                    Keys.onEscapePressed: launcher.close()
                    Keys.onReturnPressed: launcher.start(launcher.results[launcher.current])
                    Keys.onEnterPressed: launcher.start(launcher.results[launcher.current])
                    Keys.onDownPressed: launcher.current = Math.min(launcher.results.length - 1, launcher.current + grid.columns)
                    Keys.onUpPressed: launcher.current = Math.max(0, launcher.current - grid.columns)
                    Keys.onRightPressed: launcher.current = Math.min(launcher.results.length - 1, launcher.current + 1)
                    Keys.onLeftPressed: launcher.current = Math.max(0, launcher.current - 1)
                    Text {
                        visible: !query.text
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Uygulama ara…"
                        color: launcher.c.muted; font.pixelSize: 16
                    }
                }
            }

            GridView {
                id: grid
                width: parent.width
                height: parent.height - 48 - 26 - 64 - 3 * 18
                clip: true
                readonly property int columns: Math.max(1, Math.floor(width / cellWidth))
                cellWidth: 118; cellHeight: 112
                model: launcher.results
                currentIndex: launcher.current
                boundsBehavior: Flickable.StopAtBounds
                delegate: Item {
                    id: cell
                    required property var modelData
                    required property int index
                    width: grid.cellWidth; height: grid.cellHeight
                    readonly property bool chosen: index === launcher.current
                    // Arrive one after another when the launcher opens.
                    opacity: launcher.open ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: launcher.shell.ms(160 + Math.min(cell.index, 24) * 14) } }

                    Rectangle {
                        anchors { fill: parent; margins: 4 }
                        radius: 16
                        color: cell.chosen || cellMouse.containsMouse ? Qt.alpha(launcher.c.accent, 0.14) : "transparent"
                        border.width: cell.chosen ? 1 : 0
                        border.color: Qt.alpha(launcher.c.accent, 0.6)
                    }
                    Image {
                        id: icon
                        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 14 }
                        width: 48; height: 48
                        source: Shell.iconSource(cell.modelData.icon)
                        sourceSize: Qt.size(96, 96)
                        smooth: true; mipmap: true
                        scale: cellMouse.containsMouse ? 1.12 : 1
                        Behavior on scale { NumberAnimation { duration: launcher.shell.ms(160); easing.type: Easing.OutBack } }
                    }
                    Text {
                        anchors { top: icon.bottom; topMargin: 8; left: parent.left; right: parent.right; leftMargin: 6; rightMargin: 6 }
                        text: cell.modelData.name
                        color: launcher.c.text
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                        maximumLineCount: 2; wrapMode: Text.Wrap
                    }
                    MouseArea {
                        id: cellMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        onClicked: (ev) => {
                            if (ev.button === Qt.RightButton) Shell.setPinned(cell.modelData.id, true)
                            else launcher.start(cell.modelData)
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: launcher.results.length === 0
                    text: "Bulunamadı"
                    color: launcher.c.muted; font.pixelSize: 15
                }
            }

            // Power.
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 14
                Repeater {
                    model: [
                        { kind: "lock", label: "Kilitle", action: "lock" },
                        { kind: "suspend", label: "Uyku", action: "suspend" },
                        { kind: "logout", label: "Oturumu kapat", action: "logout" },
                        { kind: "reboot", label: "Yeniden başlat", action: "reboot" },
                        { kind: "power", label: "Kapat", action: "poweroff" },
                    ]
                    Rectangle {
                        required property var modelData
                        width: 128; height: 46; radius: 23
                        color: powerMouse.containsMouse ? Qt.alpha(modelData.action === "poweroff" ? "#FF556E" : launcher.c.accent, 0.18) : launcher.c.control
                        border.width: 1
                        border.color: powerMouse.containsMouse ? (modelData.action === "poweroff" ? "#FF556E" : launcher.c.accent) : Qt.alpha(launcher.c.muted, 0.25)
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Glyph { kind: parent.parent.modelData.kind; color: launcher.c.text }
                            Text { text: parent.parent.modelData.label; color: launcher.c.text; font.pixelSize: 13 }
                        }
                        MouseArea { id: powerMouse; anchors.fill: parent; hoverEnabled: true; onClicked: { launcher.close(); Shell.power(parent.modelData.action) } }
                    }
                }
            }
        }
    }
}
