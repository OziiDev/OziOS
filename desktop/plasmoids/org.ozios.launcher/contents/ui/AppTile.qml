import QtQuick

// One program in the launcher grid. When the grid fills, the tiles flow in one
// after the other; under the pointer a tile rises a little, and it dips when
// pressed. Plain Qt Quick, the icon is given as a child, so it can be shown and
// tested without a Plasma session.
Item {
    id: tile

    property string label: ""
    property bool hovered: false
    property bool pressed: false
    property bool current: false
    property int order: 0                 // place in the grid: later tiles arrive a little later
    property bool animate: true
    property real iconSize: 48
    property color textColor: "#F4FCFF"
    property color accent: "#00E5FF"
    property font font

    default property alias content: iconHolder.data

    property real arrival: animate ? 0 : 1
    property real focusScale: (hovered ? 1.07 : 1) * (pressed ? 0.93 : 1)
    Behavior on focusScale {
        enabled: tile.animate
        SpringAnimation { spring: 5; damping: 0.35; epsilon: 0.002 }
    }

    Item {
        id: body
        anchors.fill: parent
        opacity: tile.arrival
        scale: (0.86 + 0.14 * tile.arrival) * tile.focusScale
        transform: Translate { y: (1 - tile.arrival) * tile.iconSize * 0.35 }

        Item {
            id: iconHolder
            width: tile.iconSize
            height: tile.iconSize
            x: Math.round((parent.width - width) / 2)
            y: Math.round(parent.height * 0.12)
        }

        Text {
            anchors.top: iconHolder.bottom
            anchors.topMargin: Math.round(tile.iconSize * 0.18)
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 4
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            text: tile.label
            font: tile.font
            color: tile.textColor
            opacity: tile.current || tile.hovered ? 1 : 0.86
        }
    }

    SequentialAnimation {
        id: arrive
        PauseAnimation { duration: Math.min(tile.order, 28) * 14 }
        NumberAnimation { target: tile; property: "arrival"; to: 1; duration: 320; easing.type: Easing.OutCubic }
    }
    Component.onCompleted: if (animate) arrive.start()
}
