import QtQuick
import org.kde.kirigami as Kirigami

// One choice on the logout screen: a rounded tile with a line drawing and a name.
// The one under the pointer or the keyboard fills with the accent colours, grows a
// little and glows. It rises in after the tiles before it.
MouseArea {
    id: tile
    property string glyph
    property string title
    property bool badge: false          // updates are installed first
    property bool current: false
    property color accent
    property color accent2
    property real progress: -1          // what is left of a countdown on this tile, 1 to 0; -1 without one
    property int order: 0               // place in the row, for the entrance
    readonly property bool lit: current || containsMouse

    signal chosen()

    width: Kirigami.Units.gridUnit * 6.5
    height: Kirigami.Units.gridUnit * 7.2
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: chosen()
    Accessible.role: Accessible.Button
    Accessible.name: title
    Accessible.onPressAction: chosen()

    opacity: 0
    transform: Translate { id: rise; y: Kirigami.Units.gridUnit * 1.6 }
    Component.onCompleted: {
        if (Kirigami.Units.longDuration > 1) {
            entrance.start()
        } else {
            tile.opacity = 1
            rise.y = 0
        }
    }
    SequentialAnimation {
        id: entrance
        PauseAnimation { duration: 110 + tile.order * 55 }
        ParallelAnimation {
            NumberAnimation { target: tile; property: "opacity"; to: 1; duration: 260; easing.type: Easing.OutCubic }
            NumberAnimation { target: rise; property: "y"; to: 0; duration: 560; easing.type: Easing.OutBack; easing.overshoot: 1.3 }
        }
    }

    Item {
        anchors.fill: parent
        scale: tile.pressed ? 0.95 : (tile.lit ? 1.07 : 1)
        Behavior on scale { NumberAnimation { duration: 240; easing.type: Easing.OutBack; easing.overshoot: 2 } }

        // The glow: rings of the two accent colours, fainter outwards.
        Repeater {
            model: 3
            Rectangle {
                anchors.centerIn: face
                width: face.width + (index + 1) * 12
                height: face.height + (index + 1) * 12
                radius: face.radius + (index + 1) * 6
                color: index === 1 ? tile.accent2 : tile.accent
                opacity: tile.lit ? 0.085 : 0
                Behavior on opacity { NumberAnimation { duration: 220 } }
            }
        }

        Rectangle {
            id: face
            anchors.fill: parent
            radius: Kirigami.Units.gridUnit * 1.4
            color: Qt.rgba(1, 1, 1, 0.07)
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, tile.lit ? 0 : 0.13)

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                opacity: tile.lit ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: tile.accent }
                    GradientStop { position: 1; color: tile.accent2 }
                }
            }
            // light from above
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.rgba(1, 1, 1, tile.lit ? 0.18 : 0.06) }
                    GradientStop { position: 0.6; color: "transparent" }
                }
            }

            Glyph {
                id: drawing
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: parent.height * 0.19
                width: Math.round(parent.width * 0.4)
                height: width
                name: tile.glyph
                color: tile.lit ? "#FFFFFF" : "#D5E6EE"
            }
            Text {
                anchors.top: drawing.bottom
                anchors.topMargin: Kirigami.Units.gridUnit * 0.55
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - Kirigami.Units.gridUnit
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                text: tile.title
                color: "#F4FCFF"
                font.pixelSize: Math.round(Kirigami.Units.gridUnit * 0.78)
                font.weight: tile.lit ? Font.DemiBold : Font.Medium
            }
            // updates go in first
            Rectangle {
                visible: tile.badge
                anchors { top: parent.top; right: parent.right; margins: Kirigami.Units.gridUnit * 0.6 }
                width: Kirigami.Units.gridUnit * 0.55
                height: width
                radius: width / 2
                color: "#FFD166"
            }
            // what is left of the countdown
            Rectangle {
                visible: tile.progress >= 0
                anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: Kirigami.Units.gridUnit * 0.5 }
                width: (parent.width - Kirigami.Units.gridUnit * 1.6) * Math.max(0, tile.progress)
                height: 4
                radius: 2
                color: "#FFFFFF"
                opacity: 0.9
                Behavior on width { NumberAnimation { duration: 950 } }
            }
        }
    }
}
