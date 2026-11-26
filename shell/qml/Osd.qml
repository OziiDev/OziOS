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
    width: 280; height: 52
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
        "volume": Shell.tr("Volume"), "muted": Shell.tr("Muted"), "brightness": Shell.tr("Brightness"), "mic": Shell.tr("Microphone"),
        "airplane-on": Shell.tr("Airplane mode on"), "airplane-off": Shell.tr("Airplane mode off")
    })
    readonly property bool gauge: kind === "volume" || kind === "brightness"

    Rectangle {
        anchors.fill: parent
        radius: 14
        color: osd.c.raised
        border.width: 1
        border.color: Qt.alpha(osd.c.text, 0.08)
        Glyph {
            anchors { left: parent.left; leftMargin: 18; verticalCenter: parent.verticalCenter }
            size: 18
            kind: osd.kind === "brightness" ? "sun" : osd.kind === "muted" ? "muted" : osd.kind === "mic" ? "mic"
                  : osd.kind.startsWith("airplane") ? "airplane" : "volume"
            level: osd.value / 100
            color: osd.c.text
        }
        Text {
            visible: !osd.gauge
            anchors { left: parent.left; leftMargin: 50; verticalCenter: parent.verticalCenter }
            text: osd.labels[osd.kind] || ""
            color: osd.c.text; font.pixelSize: 15; font.weight: Font.DemiBold
        }
        Rectangle {
            visible: osd.gauge
            anchors { left: parent.left; leftMargin: 50; right: parent.right; rightMargin: 56; verticalCenter: parent.verticalCenter }
            height: 4; radius: 2
            color: Qt.alpha(osd.c.text, 0.14)
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, osd.value / 100)); height: parent.height; radius: 2
                color: osd.c.accent
                Behavior on width { NumberAnimation { duration: 120 } }
            }
        }
        Text {
            visible: osd.gauge
            anchors { right: parent.right; rightMargin: 20; verticalCenter: parent.verticalCenter }
            text: osd.value + "%"
            color: osd.c.text; font.pixelSize: 13
            font.features: { "tnum": 1 }
        }
    }
}
