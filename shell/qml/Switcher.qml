import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Alt+Tab: the windows in a row, most recent first; the chosen one is marked.
// oziwm owns the keys (Tab, Shift+Tab, letting go of Alt, Esc); this only shows.
Window {
    id: sw
    property var shell
    readonly property var c: shell.c
    readonly property var items: Shell.switcherWindows
    readonly property int index: Shell.switcherIndex

    visible: items.length > 0
    color: "transparent"
    width: Math.min((Screen.width > 0 ? Screen.width : 1366) - 64, row.implicitWidth + 24)
    height: 168
    LS.Window.scope: "ozi-switcher"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorNone
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    Rectangle {
        anchors.fill: parent
        radius: 16
        color: sw.c.raised
        border.width: 1
        border.color: Qt.alpha(sw.c.text, 0.10)

        ListView {
            id: row
            anchors { fill: parent; margins: 12 }
            orientation: ListView.Horizontal
            spacing: 6
            interactive: false
            implicitWidth: count * 132 + Math.max(0, count - 1) * spacing
            model: sw.items
            currentIndex: sw.index
            highlightFollowsCurrentItem: true
            highlightMoveDuration: 0
            preferredHighlightBegin: 0
            preferredHighlightEnd: width
            highlightRangeMode: ListView.ApplyRange
            delegate: Rectangle {
                id: entry
                required property var modelData
                required property int index
                readonly property bool chosen: index === sw.index
                width: 132; height: row.height
                radius: 12
                color: chosen ? Qt.alpha(sw.c.accent, 0.18) : "transparent"
                border.width: chosen ? 1 : 0
                border.color: Qt.alpha(sw.c.accent, 0.8)
                Image {
                    id: icon
                    anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 22 }
                    width: 52; height: 52
                    source: Shell.iconSource(entry.modelData.icon)
                    sourceSize: Qt.size(104, 104)
                    smooth: true; mipmap: true
                }
                Text {
                    anchors { top: icon.bottom; topMargin: 12; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 }
                    text: entry.modelData.name
                    color: sw.c.text
                    font.pixelSize: 12; font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
                Text {
                    anchors { bottom: parent.bottom; bottomMargin: 12; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 }
                    text: entry.modelData.title
                    color: sw.c.muted
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    visible: text !== entry.modelData.name
                }
                MouseArea { anchors.fill: parent; onClicked: Shell.focusWindow(entry.modelData.id) }
            }
        }
    }
}
