import QtQuick

// Stand-in for KWin.TabBoxSwitcher: what KWin hands a window switcher.
Item {
    property rect screenGeometry: Qt.rect(0, 0, 1600, 900)
    property var model
    property int currentIndex: 0
    property bool allDesktops: false
    property bool noModifierGrab: false
    property bool compositing: true
}
