import QtQuick
import QtQuick.Controls.Basic

// A slider in the OziOS colours: the filled part in the accent, the handle a ring
// that grows a little under the pointer. `moved` fires as it is dragged, like Slider's.
Slider {
    id: control
    implicitHeight: 28
    implicitWidth: 220

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: Theme.control
        border.width: 1
        border.color: Theme.far

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: control.enabled ? Theme.cyan : Theme.far
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.pressed || control.hovered ? 20 : 16
        height: width
        radius: width / 2
        color: Theme.ink
        border.width: 3
        border.color: control.enabled ? Theme.cyan : Theme.far
        Behavior on width { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    }
}
