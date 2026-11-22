import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Three islands floating at the top: Ozi + the window in front on the left,
// the clock in the middle, the system and quick settings on the right.
Window {
    id: bar
    property var shell
    readonly property var c: shell.c
    signal quickPanel()
    signal launcher()

    visible: true
    height: 46
    color: "transparent"
    LS.Window.layer: LS.Window.LayerTop
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: 46
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    readonly property var locale: Qt.locale("tr_TR")
    property date now: new Date()
    Timer { interval: 1000; repeat: true; running: true; onTriggered: bar.now = new Date() }

    // Left: the Ozi button and what has the focus.
    Island {
        id: left
        c: bar.c
        anchors { left: parent.left; leftMargin: 10; top: parent.top; topMargin: 7 }
        height: 34
        width: leftRow.implicitWidth + 20
        lit: ozi.containsMouse

        Row {
            id: leftRow
            anchors.centerIn: parent
            spacing: 10
            Rectangle {
                width: 22; height: 22; radius: 7
                anchors.verticalCenter: parent.verticalCenter
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: bar.c.accent }
                    GradientStop { position: 1; color: bar.c.accent2 }
                }
                rotation: ozi.containsMouse ? 45 : 0
                Behavior on rotation { NumberAnimation { duration: bar.shell.ms(260); easing.type: Easing.OutBack } }
                Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 2; color: bar.c.ink }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: Shell.activeTitle || "OziOS"
                color: bar.c.text
                font.pixelSize: 13; font.weight: Font.DemiBold
                elide: Text.ElideRight
                width: Math.min(implicitWidth, bar.width * 0.28)
            }
        }
        MouseArea { id: ozi; anchors.fill: parent; hoverEnabled: true; onClicked: bar.launcher() }
    }

    // Middle: clock and date.
    Island {
        c: bar.c
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 7 }
        height: 34
        width: clock.implicitWidth + 32
        Row {
            id: clock
            anchors.centerIn: parent
            spacing: 10
            Text {
                text: bar.now.toLocaleTimeString(bar.locale, "HH:mm")
                color: bar.c.text; font.pixelSize: 14; font.weight: Font.Bold
            }
            Rectangle { width: 4; height: 4; radius: 2; color: bar.c.accent; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: bar.now.toLocaleDateString(bar.locale, "d MMM ddd")
                color: bar.c.muted; font.pixelSize: 13
            }
        }
    }

    // Right: network, sound, battery; a click opens the quick panel.
    Island {
        c: bar.c
        anchors { right: parent.right; rightMargin: 10; top: parent.top; topMargin: 7 }
        height: 34
        width: status.implicitWidth + 28
        lit: quick.containsMouse
        Row {
            id: status
            anchors.centerIn: parent
            spacing: 14
            readonly property var s: Shell.status
            Glyph {
                kind: status.s.network.kind === "none" ? "offline" : status.s.network.kind
                color: status.s.network.kind === "none" ? bar.c.muted : bar.c.text
            }
            Glyph {
                kind: status.s.volume.muted ? "muted" : "volume"
                level: status.s.volume.percent / 100
                color: bar.c.text
                visible: status.s.volume.available
            }
            Row {
                visible: status.s.battery.present === true
                spacing: 5
                Glyph { kind: status.s.battery.charging ? "charging" : "battery"; level: (status.s.battery.percent || 0) / 100; color: (status.s.battery.percent || 100) <= 15 ? "#FF556E" : bar.c.text }
                Text { text: (status.s.battery.percent || 0) + "%"; color: bar.c.muted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
            }
            Glyph { kind: "dots"; color: bar.c.accent }
        }
        MouseArea { id: quick; anchors.fill: parent; hoverEnabled: true; onClicked: bar.quickPanel() }
    }
}
