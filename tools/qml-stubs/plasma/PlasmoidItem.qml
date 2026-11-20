import QtQuick

// Stand-in for PlasmoidItem. In Plasma the full representation opens in a popup;
// here it is shown in place of the compact one while `expanded` is true, or always
// when it is the preferred one. Children of the item itself are always shown, as
// in Plasma when no full representation is given.
Item {
    id: plasmoidItem

    property bool expanded: false
    property Component compactRepresentation
    property Component fullRepresentation
    property var preferredRepresentation: null
    property real switchWidth: 0
    property real switchHeight: 0
    property string toolTipMainText
    property string toolTipSubText
    property bool hideOnWindowDeactivate: true
    property bool activationTogglesExpanded: true
    readonly property Item compactRepresentationItem: compact.item
    readonly property Item fullRepresentationItem: full.item

    readonly property bool showFull: fullRepresentation !== null && (expanded || preferredRepresentation === fullRepresentation)

    Loader {
        id: compact
        anchors.fill: parent
        active: plasmoidItem.compactRepresentation !== null && !plasmoidItem.showFull
        sourceComponent: plasmoidItem.compactRepresentation
    }
    Loader {
        id: full
        anchors.fill: parent
        active: plasmoidItem.showFull
        sourceComponent: plasmoidItem.fullRepresentation
        focus: true
    }
}
