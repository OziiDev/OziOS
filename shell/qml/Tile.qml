import QtQuick

// A quick settings tile: tap to switch on/off; the arrow opens its list.
Rectangle {
    id: tile
    property var c
    property string glyph: "dots"
    property real level: 1
    property string title
    property string subtitle
    property bool on: false
    property bool more: false
    signal toggled()
    signal opened()

    height: 56; radius: 12
    color: on ? c.accent : mouse.containsMouse ? Qt.alpha(c.text, 0.10) : Qt.alpha(c.text, 0.06)
    Behavior on color { ColorAnimation { duration: 160 } }
    scale: mouse.pressed ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 90 } }

    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: tile.toggled() }

    Item {
        id: badge
        anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
        width: 22; height: 22
        Glyph { anchors.centerIn: parent; kind: tile.glyph; level: tile.level; color: tile.on ? tile.c.onAccent : tile.c.text; size: 17 }
    }
    Column {
        anchors { left: badge.right; leftMargin: 9; right: arrow.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
        Text { width: parent.width; text: tile.title; color: tile.on ? tile.c.onAccent : tile.c.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
        Text { width: parent.width; text: tile.subtitle; color: tile.on ? Qt.alpha(tile.c.onAccent, 0.75) : tile.c.muted; font.pixelSize: 11; elide: Text.ElideRight; visible: text !== "" }
    }
    Item {
        id: arrow
        visible: tile.more
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: tile.more ? 30 : 0
        Text { anchors.centerIn: parent; text: "›"; color: tile.on ? tile.c.onAccent : tile.c.muted; font.pixelSize: 20 }
        MouseArea { anchors.fill: parent; onClicked: tile.opened() }
    }
}
