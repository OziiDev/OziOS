import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as K

// Stand-in for PlasmaComponents.Button, drawn roughly the way the OziOS Plasma style draws it.
QQC2.Button {
    id: control
    font: K.Theme.defaultFont
    contentItem: Text {
        text: control.text
        font: control.font
        color: K.Theme.textColor
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        implicitWidth: 80
        implicitHeight: 32
        radius: 6
        color: Qt.rgba(K.Theme.textColor.r, K.Theme.textColor.g, K.Theme.textColor.b, control.down ? 0.16 : control.hovered ? 0.11 : 0.07)
        border.width: 1
        border.color: Qt.rgba(K.Theme.highlightColor.r, K.Theme.highlightColor.g, K.Theme.highlightColor.b, control.hovered ? 0.6 : 0.3)
    }
}
