import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The little gauge that shows what a sound, brightness or radio key did.
Window {
    id: osd
    property var shell
    readonly property var c: shell.c
    property string kind: "volume"
    property int value: 0

    visible: false
    color: "transparent"
    width: 300; height: 64
    LS.Window.scope: "ozi-osd"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorBottom
    LS.Window.margins.bottom: 110
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    function popup(kind, value) {
        osd.kind = kind
        osd.value = value
        visible = true
        hide.restart()
    }
    Timer { id: hide; interval: 1500; onTriggered: osd.visible = false }

    readonly property var labels: ({
        "volume": "Ses", "muted": "Ses kapalı", "brightness": "Parlaklık", "mic": "Mikrofon",
        "airplane-on": "Uçak modu açık", "airplane-off": "Uçak modu kapalı"
    })
    readonly property bool gauge: kind === "volume" || kind === "brightness"

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Qt.alpha(osd.c.raised, 0.96)
        border.width: 1
        border.color: Qt.alpha(osd.c.accent, 0.45)
        Glyph {
            anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
            size: 22
            kind: osd.kind === "brightness" ? "sun" : osd.kind === "muted" ? "muted" : osd.kind === "mic" ? "mic"
                  : osd.kind.startsWith("airplane") ? "airplane" : "volume"
            level: osd.value / 100
            color: osd.c.text
        }
        Text {
            visible: !osd.gauge
            anchors { left: parent.left; leftMargin: 60; verticalCenter: parent.verticalCenter }
            text: osd.labels[osd.kind] || ""
            color: osd.c.text; font.pixelSize: 15; font.weight: Font.DemiBold
        }
        Rectangle {
            visible: osd.gauge
            anchors { left: parent.left; leftMargin: 60; right: parent.right; rightMargin: 62; verticalCenter: parent.verticalCenter }
            height: 8; radius: 4
            color: Qt.alpha(osd.c.muted, 0.25)
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, osd.value / 100)); height: parent.height; radius: 4
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: osd.c.accent }
                    GradientStop { position: 1; color: osd.c.accent2 }
                }
                Behavior on width { NumberAnimation { duration: 120 } }
            }
        }
        Text {
            visible: osd.gauge
            anchors { right: parent.right; rightMargin: 20; verticalCenter: parent.verticalCenter }
            text: osd.value + "%"
            color: osd.c.muted; font.pixelSize: 13
        }
    }
}
