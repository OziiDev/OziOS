import QtQuick

// A small label with a coloured outline: severities, verdicts, kinds.
Rectangle {
    id: chip
    property alias text: label.text
    property color tone: Theme.mid

    implicitWidth: label.implicitWidth + 16
    implicitHeight: 22
    radius: 2
    color: "transparent"
    border.width: 1
    border.color: tone

    Text {
        id: label
        anchors.centerIn: parent
        color: chip.tone
        font.family: Theme.family
        font.pixelSize: 12
    }
}
