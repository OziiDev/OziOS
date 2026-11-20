import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as K

// Stand-in for PlasmaComponents.Switch.
QQC2.Switch {
    id: control
    font: K.Theme.defaultFont
    indicator: Rectangle {
        implicitWidth: 40
        implicitHeight: 20
        x: control.leftPadding
        y: (control.height - height) / 2
        radius: height / 2
        color: control.checked ? K.Theme.highlightColor : Qt.rgba(K.Theme.textColor.r, K.Theme.textColor.g, K.Theme.textColor.b, 0.15)
        Rectangle {
            width: 16
            height: 16
            radius: 8
            y: 2
            x: control.checked ? parent.width - width - 2 : 2
            color: control.checked ? K.Theme.backgroundColor : K.Theme.textColor
            Behavior on x { NumberAnimation { duration: 120 } }
        }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: K.Theme.textColor
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + 8
    }
}
