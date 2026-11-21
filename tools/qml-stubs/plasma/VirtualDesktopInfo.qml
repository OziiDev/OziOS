import QtQuick

// Stand-in for TaskManager.VirtualDesktopInfo: four desktops, the first in use.
QtObject {
    property var currentDesktop: "desktop-1"
    property int numberOfDesktops: 4
    property var desktopIds: ["desktop-1", "desktop-2", "desktop-3", "desktop-4"]
    property var desktopNames: ["1", "2", "3", "4"]
    property int desktopLayoutRows: 1
    function requestActivate(id) { currentDesktop = id }
    function requestCreateDesktop(position) {}
}
