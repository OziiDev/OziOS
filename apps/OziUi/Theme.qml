pragma Singleton
import QtQuick

// The OziOS palette and type. Depth is shown by light: near things are bright
// in the accent, available things mid, inactive things far.
//
// The values here are the cyan theme. When an app starts, ozi_qt.py sets them
// from the OziOS theme in use (ozipkg/themes.py, app_palette), so the apps follow
// `ozi theme` like the rest of the desktop. `cyan` is the accent, whatever its hue.
QtObject {
    property color ink: "#080B10"
    property color raised: "#0E131B"
    property color control: "#141B26"
    property color cyan: "#00E5FF"
    property color mid: "#0098B0"
    property color far: "#00465C"
    property color ice: "#F4FCFF"
    property color muted: "#8096A0"
    property color onAccent: "#080B10"        // text on a filled accent button
    property bool light: false                // the light theme: dark text on a light ink
    readonly property color good: light ? "#128C54" : "#3CE6A0"
    readonly property color caution: light ? "#B06E00" : "#FFBE5A"
    readonly property color danger: light ? "#C42242" : "#FF556E"

    readonly property string family: "Overpass"
    readonly property string mono: "Overpass Mono"

    function severityColor(severity) {
        if (severity === "danger") return danger
        if (severity === "warning") return caution
        if (severity === "notice") return mid
        return muted
    }

    function verdictColor(verdict) {
        if (verdict === "danger") return danger
        if (verdict === "look") return caution
        return good
    }
}
