import QtQuick
import org.kde.kirigami as K

// Stand-in for Kirigami.Avatar: a circle with the person's initials.
Rectangle {
    property var source
    property string name: ""
    implicitWidth: 32
    implicitHeight: 32
    radius: width / 2
    color: Qt.darker(K.Theme.highlightColor, 1.6)
    Text {
        anchors.centerIn: parent
        text: parent.name.split(" ").map(part => part.charAt(0)).join("").slice(0, 2).toUpperCase()
        color: "white"
        font.pixelSize: parent.height * 0.4
        font.bold: true
    }
}
