import QtQuick

// One icon of the OziOS dock: a soft square behind it under the pointer, a
// small dip when pressed, a hop while its program starts, and a mark under
// it while it runs (a dot; a short bar for the one in front). Its name shows
// above it on hover.
//
// Plain Qt Quick; the icon itself is given as a child, so it can be shown and
// tested without a Plasma session (tools/qml-shot.py, tests/test_desktop.py).
Item {
    id: item

    property var c: ({ text: "#F4FCFF", accent: "#00E5FF", ink: "#080B10", raised: "#0E131B", muted: "#8096A0" })
    property real baseSize: 40
    property bool hovered: false
    property bool pressed: false
    property bool running: false          // has a window
    property bool active: false           // its window has the focus
    property bool attention: false        // a window asks to be looked at
    property bool starting: false         // the program is being started
    property int windows: 0
    property string name: ""
    property color attentionColor: "#F5A524"
    property bool animate: true           // false when the user turned animations off

    default property alias content: holder.data

    // A click on a pinned program: a short dip and back.
    function bounce() {
        if (animate)
            popAnimation.restart()
    }

    implicitWidth: Math.round(baseSize * 1.25)
    implicitHeight: Math.round(baseSize * 1.25)

    property real press: pressed ? 0.92 : 1
    Behavior on press {
        enabled: item.animate
        NumberAnimation { duration: 90; easing.type: Easing.OutQuad }
    }
    property real lift: 0
    property real pop: 1

    Rectangle {
        anchors.centerIn: parent
        width: item.baseSize * 1.2
        height: width
        radius: 11
        color: item.c.text
        opacity: item.hovered ? 0.09 : 0
        Behavior on opacity {
            enabled: item.animate
            NumberAnimation { duration: 120 }
        }
    }

    Item {
        id: holder
        width: item.baseSize
        height: item.baseSize
        x: Math.round((item.width - width) / 2)
        y: Math.round((item.height - height) / 2 - item.lift)
        scale: item.press * item.pop
    }

    // Under a running program: a dot; the one in front gets a short bar.
    Rectangle {
        id: light
        width: item.active ? 14 : 5
        height: 3
        radius: 1.5
        x: Math.round((item.width - width) / 2)
        y: item.height - 1
        color: item.attention ? item.attentionColor : item.active ? item.c.accent : item.c.text
        opacity: item.running || item.attention ? (item.active || item.attention ? 1 : 0.5) : 0
        Behavior on width {
            enabled: item.animate
            NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
        }
        Behavior on opacity {
            enabled: item.animate
            NumberAnimation { duration: 160 }
        }
    }

    // Its name, above it while the pointer is on it.
    Rectangle {
        visible: item.hovered && item.name !== ""
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.top; bottomMargin: 12 }
        z: 10
        width: tip.implicitWidth + 16; height: 26; radius: 7
        color: item.c.raised
        border.width: 1; border.color: Qt.alpha(item.c.text, 0.10)
        Text { id: tip; anchors.centerIn: parent; text: item.name; color: item.c.text; font.pixelSize: 12 }
    }

    // Hops while the program starts.
    SequentialAnimation {
        running: item.starting && item.animate && item.visible
        loops: Animation.Infinite
        NumberAnimation { target: item; property: "lift"; to: item.baseSize * 0.12; duration: 220; easing.type: Easing.OutQuad }
        NumberAnimation { target: item; property: "lift"; to: 0; duration: 380; easing.type: Easing.OutBounce }
        onRunningChanged: if (!running) settle.restart()
    }
    NumberAnimation { id: settle; target: item; property: "lift"; to: 0; duration: 160; easing.type: Easing.OutQuad }

    SequentialAnimation {
        id: popAnimation
        NumberAnimation { target: item; property: "pop"; to: 0.9; duration: 90; easing.type: Easing.OutQuad }
        NumberAnimation { target: item; property: "pop"; to: 1; duration: 180; easing.type: Easing.OutCubic }
    }
}
