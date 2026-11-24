import QtQuick

// A slider in the OziOS look: a thin track that fills with the accent.
Item {
    id: slider
    property var c
    property real from: 0
    property real to: 1
    property real value: 0
    property real stepSize: 0
    signal moved(real value)

    implicitHeight: 28
    readonly property real ratio: (value - from) / Math.max(0.0001, to - from)

    Rectangle {
        id: track
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
        height: 4; radius: 2
        color: Qt.alpha(slider.c.text, 0.14)
        Rectangle {
            width: Math.max(height, parent.width * slider.ratio)
            height: parent.height; radius: 2
            color: slider.c.accent
        }
    }
    Rectangle {
        x: track.width * slider.ratio - width / 2
        anchors.verticalCenter: parent.verticalCenter
        width: area.pressed ? 18 : 16; height: width; radius: width / 2
        color: "white"
        border.width: 1; border.color: Qt.rgba(0, 0, 0, 0.18)
        Behavior on width { NumberAnimation { duration: 120 } }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        preventStealing: true
        function set(x) {
            let v = slider.from + Math.max(0, Math.min(1, x / track.width)) * (slider.to - slider.from)
            if (slider.stepSize > 0) v = Math.round(v / slider.stepSize) * slider.stepSize
            if (v !== slider.value) slider.moved(v)
        }
        onPressed: (ev) => set(ev.x)
        onPositionChanged: (ev) => { if (pressed) set(ev.x) }
    }
}
