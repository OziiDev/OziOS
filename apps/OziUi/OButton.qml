import QtQuick
import QtQuick.Controls.Basic

// A filled cyan button appears at most once per view, for the main action.
Button {
    id: control
    property bool primary: false

    implicitHeight: 36
    leftPadding: 16
    rightPadding: 16
    font.family: Theme.family
    font.pixelSize: 14

    contentItem: Text {
        text: control.text
        font: control.font
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: !control.enabled ? Theme.far : (control.primary ? Theme.ink : Theme.ice)
    }

    background: Rectangle {
        radius: 4
        opacity: control.enabled ? 1 : 0.5
        color: control.primary ? (control.down ? Theme.mid : Theme.cyan) : (control.down ? Theme.raised : Theme.control)
        border.width: control.primary ? 0 : 1
        border.color: control.hovered || control.visualFocus ? Theme.cyan : Theme.far
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }
}
