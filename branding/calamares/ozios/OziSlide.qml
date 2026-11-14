import QtQuick 2.0

// One page of the installer's slideshow: a heading and a few words, centred.
Rectangle {
    id: page
    property string heading: ""
    property string words: ""

    anchors.fill: parent
    color: "#080B10"

    Column {
        anchors.centerIn: parent
        width: parent.width * 0.7
        spacing: 18
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: page.heading
            color: "#00E5FF"
            font.pixelSize: 34
        }
        Text {
            width: parent.width
            text: page.words
            color: "#F4FCFF"
            font.pixelSize: 18
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
