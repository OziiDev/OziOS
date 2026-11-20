import QtQuick

// Stand-in for PlasmaCore.ToolTipArea: knows whether the pointer is on it.
Item {
    property string mainText
    property string subText
    property int textFormat: Text.AutoText
    property int location: 0
    property bool active: true
    property bool interactive: false
    property Item mainItem
    readonly property bool containsMouse: hover.hovered

    HoverHandler { id: hover }
}
