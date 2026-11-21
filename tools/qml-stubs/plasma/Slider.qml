import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as K

// Stand-in for PlasmaComponents.Slider.
QQC2.Slider {
    id: control
    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 160
        implicitHeight: 4
        width: control.availableWidth
        height: implicitHeight
        radius: 2
        color: Qt.rgba(K.Theme.textColor.r, K.Theme.textColor.g, K.Theme.textColor.b, 0.15)
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: K.Theme.highlightColor
        }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 16
        implicitHeight: 16
        radius: 8
        color: K.Theme.backgroundColor
        border.color: K.Theme.highlightColor
        border.width: 2
    }
}
