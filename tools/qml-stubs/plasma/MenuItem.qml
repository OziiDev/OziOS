import QtQuick

// Stand-in for PlasmaExtras.MenuItem.
QtObject {
    property string text
    property var icon
    property bool visible: true
    property bool enabled: true
    property bool separator: false
    property bool checkable: false
    property bool checked: false
    signal clicked()
}
