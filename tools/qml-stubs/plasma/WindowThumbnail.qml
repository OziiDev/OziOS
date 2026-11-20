import QtQuick

// Stand-in for KWin.WindowThumbnail: a made-up window, coloured after its id.
Rectangle {
    property var wId
    property var client
    readonly property real hue: (Number(wId) * 0.137) % 1
    color: Qt.hsla(hue, 0.18, 0.16, 1)
    Rectangle {
        width: parent.width
        height: Math.round(parent.height * 0.12)
        color: Qt.hsla(parent.hue, 0.3, 0.24, 1)
    }
    Column {
        x: parent.width * 0.08
        y: parent.height * 0.22
        spacing: parent.height * 0.07
        Repeater {
            model: 5
            Rectangle {
                required property int index
                width: (0.35 + ((index * 37) % 50) / 100) * parent.parent.width * 0.8
                height: Math.max(2, parent.parent.height * 0.045)
                radius: height / 2
                color: Qt.hsla(parent.parent.hue, 0.5, 0.62, 0.55)
            }
        }
    }
}
