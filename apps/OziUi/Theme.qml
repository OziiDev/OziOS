pragma Singleton
import QtQuick

// The OziOS palette and type. Depth is shown by light: near things are bright
// cyan, available things mid, inactive things far.
QtObject {
    readonly property color ink: "#080B10"
    readonly property color raised: "#0E131B"
    readonly property color control: "#141B26"
    readonly property color cyan: "#00E5FF"
    readonly property color mid: "#0098B0"
    readonly property color far: "#00465C"
    readonly property color ice: "#F4FCFF"
    readonly property color muted: "#8096A0"
    readonly property color good: "#3CE6A0"
    readonly property color caution: "#FFBE5A"
    readonly property color danger: "#FF556E"

    readonly property string family: "Overpass"
    readonly property string mono: "JetBrains Mono"

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
