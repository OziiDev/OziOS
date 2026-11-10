import QtQuick

// Login splash. Plasma raises `stage` from 1 to 6 as the session comes up.
Rectangle {
    id: root
    color: "#080B10"

    property int stage

    Item {
        id: content
        anchors.fill: parent
        opacity: 0
        Behavior on opacity { NumberAnimation { duration: 700; easing.type: Easing.OutCubic } }

        Tesseract {
            id: figure
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -height * 0.12
            width: Math.round(Math.min(root.width, root.height) * 0.34)
            height: width
            speed: 0.03
        }

        Text {
            anchors.top: figure.bottom
            anchors.topMargin: figure.height * 0.12
            anchors.horizontalCenter: parent.horizontalCenter
            text: "OziOS"
            color: "#F4FCFF"
            font.pixelSize: Math.round(figure.height * 0.11)
            font.letterSpacing: font.pixelSize * 0.45
            font.weight: Font.Light
        }
    }

    onStageChanged: {
        if (stage >= 1)
            content.opacity = 1
    }
}
