import QtQuick

// Stand-in for TaskManager.VirtualDesktopInfo.
QtObject {
    property var currentDesktop: "desktop-1"
    property int numberOfDesktops: 2
    property var desktopIds: ["desktop-1", "desktop-2"]
    property var desktopNames: ["1", "2"]
}
