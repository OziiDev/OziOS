import QtQuick
import QtQuick.Window

// Stand-in for PlasmaCore.Dialog: a window of its own around its main item, with
// room for the Plasma style's frame the preview draws behind it.
Window {
    id: dialog
    property Item mainItem
    property int location: 0
    property int type: 0
    property bool hideOnWindowDeactivate: false
    property Item visualParent
    readonly property int margin: 12
    color: "transparent"
    width: mainItem ? mainItem.width + margin * 2 : 100
    height: mainItem ? mainItem.height + margin * 2 : 100
    onMainItemChanged: {
        if (mainItem) {
            mainItem.parent = dialog.contentItem
            mainItem.x = margin
            mainItem.y = margin
        }
    }
}
