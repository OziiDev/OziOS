import QtQuick

// One window in the OziOS switcher: its live picture in a frame, its icon on the
// corner, its title under it. The chosen window comes forward with a rim and a
// glow in the accent colour; the others step back and dim. Plain Qt Quick: the
// picture and the icon are given from outside, so this can be shown and tested
// without KWin.
Item {
    id: card

    property bool current: false
    property bool hovered: false
    property string caption: ""
    property color accent: "#00E5FF"
    property color textColor: "#F4FCFF"
    property bool animate: true
    property font font
    property real screenRatio: 16 / 9

    default property alias thumbnail: picture.data
    property alias badge: badgeHolder.data

    // 1 for the chosen window, a little for the one under the pointer, 0 for the rest.
    property real lift: current ? 1 : (hovered ? 0.45 : 0)
    Behavior on lift {
        enabled: card.animate
        SpringAnimation { spring: 4; damping: 0.38; epsilon: 0.002 }
    }

    Item {
        id: body
        anchors.fill: parent
        transformOrigin: Item.Center
        scale: 0.9 + 0.1 * card.lift
        opacity: 0.55 + 0.45 * card.lift

        Rectangle {
            id: glow
            x: frame.x - 7
            y: frame.y - 7
            width: frame.width + 14
            height: frame.height + 14
            radius: frame.radius + 7
            color: "transparent"
            border.width: 7
            border.color: card.accent
            opacity: 0.2 * card.lift
        }

        Rectangle {
            id: frame
            width: parent.width
            height: Math.round(width / card.screenRatio)
            radius: 10
            color: Qt.rgba(card.textColor.r, card.textColor.g, card.textColor.b, 0.06)
            border.width: card.current ? 2 : 1
            border.color: card.current ? card.accent : Qt.rgba(card.textColor.r, card.textColor.g, card.textColor.b, 0.16)

            Item {
                id: picture
                anchors.fill: parent
                anchors.margins: 5
                clip: true
            }
        }

        Item {
            id: badgeHolder
            width: Math.round(frame.width * 0.2)
            height: width
            x: 10
            y: frame.height - height * 0.62
        }

        Text {
            anchors.top: frame.bottom
            anchors.topMargin: Math.round(badgeHolder.height * 0.42) + 4
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: card.caption
            font: card.font
            color: card.textColor
            opacity: card.current ? 1 : 0.75
        }
    }
}
