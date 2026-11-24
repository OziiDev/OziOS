import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The launcher: Super, Super+Space or the apps button. Type to search, arrows
// and Enter to start, Esc or a click outside to close. Right click on an app
// pins it to the dock. Lock, sleep, log out, restart and shut down at the
// bottom; the last three ask once more before they act.
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
    property string armed: ""   // a power action waiting for its second click

    function toggle() { open ? close() : show() }
    function show() {
        query.text = ""
        results = Shell.apps
        current = 0
        armed = ""
        visible = true
        open = true
        grid.positionViewAtBeginning()
        query.forceActiveFocus()
    }
    function close() { open = false; hideTimer.restart() }
    function start(app) { if (app) { Shell.launch(app.id); close() } }
    function move(by) {
        if (results.length === 0) return
        current = Math.max(0, Math.min(results.length - 1, current + by))
        grid.positionViewAtIndex(current, GridView.Contain)
    }

    Timer { id: hideTimer; interval: launcher.shell.ms(160); onTriggered: if (!launcher.open) launcher.visible = false }
    Timer { id: disarm; interval: 3000; onTriggered: launcher.armed = "" }

    // Dim everything behind; a click there closes.
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: launcher.open ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: launcher.shell.ms(160) } }
        MouseArea { anchors.fill: parent; onClicked: launcher.close() }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 760)
        height: Math.min(parent.height - 96, 600)
        radius: 16
        color: launcher.c.raised
        border.width: 1
        border.color: Qt.alpha(launcher.c.text, 0.08)
        opacity: launcher.open ? 1 : 0
        scale: launcher.open ? 1 : 0.97
        Behavior on opacity { NumberAnimation { duration: launcher.shell.ms(160) } }
        Behavior on scale { NumberAnimation { duration: launcher.shell.ms(200); easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }  // clicks on the card stay on the card

        // Search field.
        Rectangle {
            id: field
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            height: 42; radius: 10
            color: Qt.alpha(launcher.c.text, 0.06)
            border.width: query.activeFocus ? 1 : 0
            border.color: Qt.alpha(launcher.c.accent, 0.8)
            Glyph { kind: "search"; color: launcher.c.muted; anchors { left: parent.left; leftMargin: 14 } size: 16 }
            TextInput {
                id: query
                anchors { fill: parent; leftMargin: 40; rightMargin: 14 }
                verticalAlignment: TextInput.AlignVCenter
                color: launcher.c.text
                selectionColor: launcher.c.accent
                selectedTextColor: launcher.c.onAccent
                font.pixelSize: 15
                onTextChanged: { launcher.results = Shell.search(text); launcher.current = 0; grid.positionViewAtBeginning() }
                Keys.onEscapePressed: launcher.close()
                Keys.onReturnPressed: launcher.start(launcher.results[launcher.current])
                Keys.onEnterPressed: launcher.start(launcher.results[launcher.current])
                Keys.onDownPressed: launcher.move(grid.columns)
                Keys.onUpPressed: launcher.move(-grid.columns)
                Keys.onRightPressed: (ev) => { if (query.cursorPosition === query.text.length) launcher.move(1); else ev.accepted = false }
                Keys.onLeftPressed: (ev) => { if (query.cursorPosition === 0) launcher.move(-1); else ev.accepted = false }
                Keys.onTabPressed: launcher.move(1)
                Text {
                    visible: !query.text
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Uygulama ara"
                    color: launcher.c.muted; font.pixelSize: 15
                }
            }
        }

        GridView {
            id: grid
            anchors { left: parent.left; right: parent.right; top: field.bottom; bottom: footer.top; leftMargin: 12; rightMargin: 12; topMargin: 10; bottomMargin: 6 }
            clip: true
            readonly property int columns: Math.max(1, Math.floor(width / cellWidth))
            cellWidth: Math.floor(width / Math.max(1, Math.floor(width / 112)))
            cellHeight: 104
            model: launcher.results
            currentIndex: launcher.current
            boundsBehavior: Flickable.StopAtBounds
            delegate: Item {
                id: cell
                required property var modelData
                required property int index
                width: grid.cellWidth; height: grid.cellHeight
                readonly property bool chosen: index === launcher.current

                Rectangle {
                    anchors { fill: parent; margins: 3 }
                    radius: 10
                    color: cell.chosen ? Qt.alpha(launcher.c.accent, 0.16)
                         : cellMouse.containsMouse ? Qt.alpha(launcher.c.text, 0.06) : "transparent"
                }
                Image {
                    id: icon
                    anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 14 }
                    width: 44; height: 44
                    source: Shell.iconSource(cell.modelData.icon)
                    sourceSize: Qt.size(96, 96)
                    smooth: true; mipmap: true
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
                text: "“" + query.text + "” için uygulama yok"
                color: launcher.c.muted; font.pixelSize: 14
            }
        }

        // Footer: how many apps, and the power actions.
        Item {
            id: footer
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 12 }
            height: 40
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top; topMargin: -6 }
                height: 1; color: Qt.alpha(launcher.c.text, 0.07)
            }
            Text {
                anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
                text: launcher.armed ? "Emin misin? Onaylamak için bir daha tıkla."
                     : launcher.results.length + " uygulama · sağ tık: Dock'a sabitle"
                color: launcher.armed ? launcher.c.danger : launcher.c.muted
                font.pixelSize: 12
            }
            Row {
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                spacing: 4
                Repeater {
                    model: [
                        { kind: "lock", label: "Kilitle", action: "lock", ask: false },
                        { kind: "suspend", label: "Uyku", action: "suspend", ask: false },
                        { kind: "logout", label: "Oturumu kapat", action: "logout", ask: true },
                        { kind: "reboot", label: "Yeniden başlat", action: "reboot", ask: true },
                        { kind: "power", label: "Kapat", action: "poweroff", ask: true },
                    ]
                    Rectangle {
                        id: powerButton
                        required property var modelData
                        readonly property bool isArmed: launcher.armed === modelData.action
                        width: isArmed || powerMouse.containsMouse ? label.implicitWidth + 44 : 36
                        height: 36; radius: 9
                        clip: true
                        color: isArmed ? launcher.c.danger : powerMouse.containsMouse ? Qt.alpha(launcher.c.text, 0.08) : "transparent"
                        Behavior on width { NumberAnimation { duration: launcher.shell.ms(140); easing.type: Easing.OutCubic } }
                        Glyph {
                            id: glyph
                            anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                            kind: powerButton.modelData.kind
                            color: powerButton.isArmed ? "white" : launcher.c.text
                        }
                        Text {
                            id: label
                            anchors { left: glyph.right; leftMargin: 8; verticalCenter: parent.verticalCenter }
                            text: powerButton.modelData.label
                            color: powerButton.isArmed ? "white" : launcher.c.text
                            font.pixelSize: 13
                            opacity: powerButton.width > 40 ? 1 : 0
                        }
                        MouseArea {
                            id: powerMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                const m = powerButton.modelData
                                if (m.ask && launcher.armed !== m.action) { launcher.armed = m.action; disarm.restart(); return }
                                launcher.armed = ""
                                launcher.close()
                                Shell.power(m.action)
                            }
                        }
                    }
                }
            }
        }
    }
}
