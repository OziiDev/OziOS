import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as K

// Stand-in for PlasmaComponents.ToolButton: flat until it is checked or hovered.
QQC2.ToolButton {
    id: control
    font: K.Theme.defaultFont
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.checked ? K.Theme.highlightColor : K.Theme.textColor
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        implicitWidth: 40
        implicitHeight: 30
        radius: 6
        color: Qt.rgba(K.Theme.highlightColor.r, K.Theme.highlightColor.g, K.Theme.highlightColor.b, control.checked ? 0.18 : control.hovered ? 0.1 : 0)
        border.width: control.checked ? 1 : 0
        border.color: Qt.rgba(K.Theme.highlightColor.r, K.Theme.highlightColor.g, K.Theme.highlightColor.b, 0.5)
    }
}
