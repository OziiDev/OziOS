import QtQuick
import QtQuick.Controls.Basic

Switch {
    id: control
    font.family: Theme.family
    font.pixelSize: 14
    implicitHeight: 32
    spacing: 12

    indicator: Rectangle {
        implicitWidth: 40
        implicitHeight: 20
        x: control.leftPadding
        y: (control.height - height) / 2
        radius: 10
        color: control.checked ? Theme.far : Theme.control
        border.width: 1
        border.color: control.checked ? Theme.cyan : Theme.far

        Rectangle {
            width: 14
            height: 14
            radius: 7
            y: 3
            x: control.checked ? parent.width - width - 3 : 3
            color: control.checked ? Theme.cyan : Theme.muted
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? Theme.ice : Theme.muted
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}
