import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The top bar: one quiet strip across the screen. Left: the apps button, the
// desktops and the window in front; middle: clock and date; right: the system
// status, which opens the quick settings.
Window {
    id: bar
    property var shell
    readonly property var c: shell.c
    signal quickPanel()
    signal launcher()
    signal calendar()
    signal trayMenuAt(real x)

    visible: true
    height: 34
    color: "transparent"
    LS.Window.scope: "ozi-bar"
    LS.Window.layer: LS.Window.LayerTop
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: 34
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    readonly property var locale: Qt.locale(Shell.locale)
    property date now: new Date()
    Timer { interval: 1000; repeat: true; running: true; onTriggered: bar.now = new Date() }

    Rectangle {
        anchors.fill: parent
        color: Qt.alpha(bar.c.ink, 0.86)
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1
            color: Qt.alpha(bar.c.text, 0.07)
        }
    }

    // A flat button of the bar: shows a soft background under the pointer.
    component BarButton: Rectangle {
        id: button
        property alias hovered: area.containsMouse
        property alias pressed: area.pressed
        signal clicked()
        height: 26; radius: 7
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        color: area.pressed ? Qt.alpha(bar.c.text, 0.16) : area.containsMouse ? Qt.alpha(bar.c.text, 0.09) : "transparent"
        Behavior on color { ColorAnimation { duration: 120 } }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: button.clicked() }
    }

    Row {
        id: leftRow
        anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
        spacing: 4

        // Apps: the OziOS mark, which opens the launcher.
        BarButton {
            width: 34
            onClicked: bar.launcher()
            Glyph { anchors.centerIn: parent; kind: "apps"; color: bar.c.text; size: 15 }
        }

        // Desktops: numbered; the one in use is filled with the accent.
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Repeater {
                model: Shell.workspaces
                BarButton {
                    required property var modelData
                    width: 24; height: 22
                    color: modelData.active ? bar.c.accent : hovered ? Qt.alpha(bar.c.text, 0.09) : "transparent"
                    onClicked: Shell.switchWorkspace(modelData.index)
                    Text {
                        anchors.centerIn: parent
                        text: parent.modelData.index
                        color: parent.modelData.active ? bar.c.onAccent : parent.modelData.windows > 0 ? bar.c.text : bar.c.muted
                        font.pixelSize: 12; font.weight: parent.modelData.active ? Font.Bold : Font.Medium
                    }
                    // Tiled desktop: a small mark under the number.
                    Rectangle {
                        visible: parent.modelData.tiling
                        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 2 }
                        width: 8; height: 2; radius: 1
                        color: parent.modelData.active ? bar.c.onAccent : bar.c.muted
                    }
                }
            }
        }

        Rectangle { width: 1; height: 16; color: Qt.alpha(bar.c.text, 0.12); anchors.verticalCenter: parent.verticalCenter }

        // While a program starts (some take seconds): a small spinner and its name.
        Item {
            visible: !!Shell.starting.name
            width: 22; height: 22
            anchors.verticalCenter: parent.verticalCenter
            Canvas {
                id: spinner
                anchors.centerIn: parent
                width: 14; height: 14
                property real angle: 0
                onAngleChanged: requestPaint()
                onPaint: {
                    const g = getContext("2d")
                    g.reset()
                    g.lineWidth = 2
                    g.lineCap = "round"
                    g.strokeStyle = Qt.alpha(bar.c.text, 0.18)
                    g.beginPath(); g.arc(7, 7, 5.5, 0, Math.PI * 2); g.stroke()
                    g.strokeStyle = bar.c.accent
                    g.beginPath(); g.arc(7, 7, 5.5, angle, angle + Math.PI * 0.6); g.stroke()
                }
                NumberAnimation on angle { from: 0; to: Math.PI * 2; duration: 800; loops: Animation.Infinite; running: !!Shell.starting.name }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            leftPadding: Shell.starting.name ? 0 : 6
            text: Shell.starting.name ? Shell.trf("{app} is starting…", { app: Shell.starting.name }) : (Shell.activeTitle || Shell.tr("Desktop"))
            color: Shell.starting.name ? bar.c.muted : bar.c.text
            font.pixelSize: 13; font.weight: Font.DemiBold
            elide: Text.ElideRight
            width: Math.min(implicitWidth, bar.width * 0.3)
        }
    }

    // Middle: clock and date.
    BarButton {
        anchors.centerIn: parent
        width: clock.implicitWidth + 20
        onClicked: bar.calendar()
        Row {
            id: clock
            anchors.centerIn: parent
            spacing: 8
            Text {
                text: bar.now.toLocaleDateString(bar.locale, "d MMM ddd")
                color: bar.c.muted; font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: bar.now.toLocaleTimeString(bar.locale, "HH:mm")
                color: bar.c.text; font.pixelSize: 13; font.weight: Font.DemiBold
                font.features: { "tnum": 1 }
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // Tray: programs running in the background (Discord, Steam...). Click: open
    // it; right click: its menu.
    Row {
        id: trayRow
        anchors { right: statusButton.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
        spacing: 2
        Repeater {
            model: Tray.items
            BarButton {
                id: trayButton
                required property var modelData
                width: 28
                onClicked: {
                    const p = trayButton.mapToGlobal(width / 2, bar.height)
                    Tray.activate(modelData.service, p.x, p.y)
                }
                Image {
                    anchors.centerIn: parent
                    width: 18; height: 18
                    sourceSize: Qt.size(36, 36)
                    smooth: true; mipmap: true
                    source: trayButton.modelData.icon.startsWith("/") ? "file://" + trayButton.modelData.icon
                                                                      : Shell.iconSource(trayButton.modelData.icon)
                }
                Rectangle {   // asks to be looked at (a new message...)
                    visible: trayButton.modelData.status === "NeedsAttention"
                    width: 6; height: 6; radius: 3
                    color: bar.c.accent
                    anchors { right: parent.right; top: parent.top; margins: 3 }
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.RightButton | Qt.MiddleButton
                    onClicked: (ev) => {
                        if (ev.button === Qt.MiddleButton) {
                            const p = trayButton.mapToGlobal(width / 2, bar.height)
                            Tray.activate(trayButton.modelData.service, p.x, p.y)
                            return
                        }
                        bar.trayMenuAt(trayButton.mapToGlobal(trayButton.width / 2, 0).x)
                        Tray.openMenu(trayButton.modelData.service)
                    }
                }
            }
        }
    }

    // Right: network, sound, battery; a click opens the quick settings.
    BarButton {
        id: statusButton
        anchors { right: parent.right; rightMargin: 6 }
        width: status.implicitWidth + 20
        onClicked: bar.quickPanel()
        Row {
            id: status
            anchors.centerIn: parent
            spacing: 12
            readonly property var s: Shell.status
            Glyph {
                kind: status.s.network.kind === "none" ? "offline" : status.s.network.kind
                color: status.s.network.kind === "none" ? bar.c.muted : bar.c.text
                size: 15
            }
            Glyph {
                kind: status.s.volume.muted ? "muted" : "volume"
                level: status.s.volume.percent / 100
                color: bar.c.text
                size: 15
                visible: status.s.volume.available
            }
            Row {
                visible: status.s.battery.present === true
                spacing: 4
                Glyph {
                    kind: status.s.battery.charging ? "charging" : "battery"
                    level: (status.s.battery.percent || 0) / 100
                    color: (status.s.battery.percent || 100) <= 15 && !status.s.battery.charging ? bar.c.danger : bar.c.text
                    size: 16
                }
                Text {
                    text: (status.s.battery.percent || 0) + "%"
                    color: bar.c.text; font.pixelSize: 12
                    font.features: { "tnum": 1 }
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Glyph { kind: "power"; color: bar.c.muted; size: 14 }
        }
    }
}
