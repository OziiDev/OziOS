pragma Singleton
import QtQuick

// Stand-in for Kirigami.Theme: the colours of the scheme in use. The preview
// tool sets them from an OziOS theme (tools/plasma_stubs.py).
QtObject {
    property color highlightColor: "#00e5ff"
    property color highlightedTextColor: "#080b10"
    property color textColor: "#f4fcff"
    property color disabledTextColor: "#8096a0"
    property color backgroundColor: "#080b10"
    property color alternateBackgroundColor: "#0e131b"
    property color neutralTextColor: "#ffbe5a"
    property color negativeTextColor: "#ff556e"
    property color positiveTextColor: "#3ce6a0"
    property font defaultFont: Qt.font({ family: "Segoe UI", pixelSize: 14 })
    property font smallFont: Qt.font({ family: "Segoe UI", pixelSize: 12 })
}
