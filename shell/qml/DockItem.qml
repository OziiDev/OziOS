import QtQuick

// One icon of the OziOS dock. It grows toward the pointer, dips when pressed,
// hops while its program starts, pulses while it asks for attention and shows
// a light under it while it runs. Everything that moves is a transform or an
// opacity, drawn by the GPU: the dock never changes size while the pointer moves.
//
// Plain Qt Quick; the icon itself is given as a child. So it can be shown and
// tested without a Plasma session (tools/qml-shot.py, tests/test_desktop.py).
Item {
    id: item

    property real baseSize: 40            // icon size at rest
    property real zoom: 1                 // set by the dock from the pointer's distance
    property bool hovered: false
    property bool pressed: false
    property bool running: false          // has a window
    property bool active: false           // its window has the focus
    property bool attention: false        // a window asks to be looked at
    property bool starting: false         // the program is being started
    property int windows: 0
    property color accent: "#00E5FF"
    property color lightColor: "#F4FCFF"
    property color attentionColor: "#FFBE5A"
    property bool animate: true           // false when the user turned animations off

    default property alias content: holder.data

    // A click on a pinned program: a short squash and stretch.
    function bounce() {
        if (animate)
            popAnimation.restart()
    }

    implicitWidth: Math.round(baseSize * 1.3)
    implicitHeight: Math.round(baseSize * 1.45)

    // Grow with a little spring, as if the icon had weight.
    property real shownZoom: zoom
    Behavior on shownZoom {
        enabled: item.animate
        SpringAnimation { spring: 4.5; damping: 0.32; epsilon: 0.002 }
    }
    property real press: pressed ? 0.88 : 1
    Behavior on press {
        enabled: item.animate
        NumberAnimation { duration: 110; easing.type: Easing.OutQuad }
    }
    property real lift: 0                 // how far the icon hops up
    property real pop: 1                  // squash and stretch after a click
    property real grow: 1                 // arrival of a new icon

    // A soft key behind the icon while the pointer is on it.
    Rectangle {
        width: item.baseSize * 1.2
        height: width
        radius: width * 0.3
        x: holder.x + (holder.width - width) / 2
        y: holder.y + (holder.height - height) / 2
        transformOrigin: Item.Bottom
        scale: holder.scale
        color: item.accent
        opacity: item.hovered ? 0.14 : (item.active ? 0.07 : 0)
        Behavior on opacity {
            enabled: item.animate
            NumberAnimation { duration: 180 }
        }
    }

    // Rings that spread out while a window asks for attention.
    Rectangle {
        id: ring
        width: item.baseSize
        height: width
        radius: width * 0.3
        x: holder.x
        y: holder.y
        color: "transparent"
        border.width: Math.max(1, Math.round(item.baseSize / 22))
        border.color: item.attentionColor
        opacity: 0
    }
    SequentialAnimation {
        running: item.attention && item.animate && item.visible
        loops: Animation.Infinite
        ParallelAnimation {
            NumberAnimation { target: ring; property: "scale"; from: 1; to: 1.5; duration: 900; easing.type: Easing.OutCubic }
            NumberAnimation { target: ring; property: "opacity"; from: 0.85; to: 0; duration: 900; easing.type: Easing.OutCubic }
        }
        PauseAnimation { duration: 250 }
        onRunningChanged: if (!running) ring.opacity = 0
    }

    Item {
        id: holder
        width: item.baseSize
        height: item.baseSize
        x: Math.round((item.width - width) / 2)
        y: Math.round(item.height - height - item.baseSize * 0.24 - item.lift)
        transformOrigin: Item.Bottom
        scale: item.shownZoom * item.press * item.pop * item.grow
        opacity: Math.min(1, item.grow)
    }

    // The light under a running program: a dot, a longer dash for several
    // windows, a bright bar with a glow for the one in front.
    Rectangle {
        id: light
        readonly property real dot: Math.max(4, Math.round(item.baseSize / 9))
        width: !item.running && !item.attention ? dot
             : item.active ? Math.round(item.baseSize * 0.42)
             : item.windows > 1 ? Math.round(item.baseSize * 0.2) : dot
        height: dot
        radius: height / 2
        x: Math.round((item.width - width) / 2)
        y: Math.round(item.height - height - Math.max(2, item.baseSize * 0.05))
        color: item.attention ? item.attentionColor : item.active ? item.accent : item.lightColor
        opacity: item.running || item.attention ? (item.active || item.attention ? 1 : 0.55) : 0
        Behavior on width {
            enabled: item.animate
            NumberAnimation { duration: 260; easing.type: Easing.OutBack }
        }
        Behavior on opacity {
            enabled: item.animate
            NumberAnimation { duration: 200 }
        }
        Behavior on color {
            enabled: item.animate
            ColorAnimation { duration: 200 }
        }
    }
    Rectangle {
        width: light.width + light.height * 3
        height: light.height * 3
        radius: height / 2
        x: light.x + (light.width - width) / 2
        y: light.y + (light.height - height) / 2
        color: light.color
        opacity: item.active ? 0.22 : 0
        z: -1
        Behavior on opacity {
            enabled: item.animate
            NumberAnimation { duration: 220 }
        }
    }

    // Hops while the program starts, like a ball that settles.
    SequentialAnimation {
        running: item.starting && item.animate && item.visible
        loops: Animation.Infinite
        NumberAnimation { target: item; property: "lift"; to: item.baseSize * 0.16; duration: 220; easing.type: Easing.OutQuad }
        NumberAnimation { target: item; property: "lift"; to: 0; duration: 430; easing.type: Easing.OutBounce }
        onRunningChanged: if (!running) settle.restart()
    }
    NumberAnimation { id: settle; target: item; property: "lift"; to: 0; duration: 180; easing.type: Easing.OutQuad }

    SequentialAnimation {
        id: popAnimation
        NumberAnimation { target: item; property: "pop"; to: 1.06; duration: 110; easing.type: Easing.OutQuad }
        NumberAnimation { target: item; property: "pop"; to: 0.95; duration: 110; easing.type: Easing.InOutQuad }
        NumberAnimation { target: item; property: "pop"; to: 1; duration: 200; easing.type: Easing.OutBack }
    }

    // A new icon arrives from small, with a little overshoot.
    NumberAnimation {
        id: arrive
        target: item
        property: "grow"
        from: 0.3
        to: 1
        duration: 380
        easing.type: Easing.OutBack
    }
    Component.onCompleted: if (animate) arrive.start()
}
