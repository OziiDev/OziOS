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

    height: 58; radius: 16
    color: on ? Qt.alpha(c.accent, 0.2) : c.control
    border.width: 1
    border.color: on ? Qt.alpha(c.accent, 0.6) : Qt.alpha(c.muted, 0.15)
    Behavior on color { ColorAnimation { duration: 160 } }
    scale: mouse.pressed ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 90 } }

    MouseArea { id: mouse; anchors.fill: parent; onClicked: tile.toggled() }

    Rectangle {
        id: badge
        anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
        width: 34; height: 34; radius: 17
        color: tile.on ? tile.c.accent : Qt.alpha(tile.c.muted, 0.2)
        Glyph { anchors.centerIn: parent; kind: tile.glyph; level: tile.level; color: tile.on ? tile.c.ink : tile.c.text; size: 17 }
    }
    Column {
        anchors { left: badge.right; leftMargin: 9; right: arrow.left; rightMargin: 4; verticalCenter: parent.verticalCenter }
        Text { width: parent.width; text: tile.title; color: tile.c.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
        Text { width: parent.width; text: tile.subtitle; color: tile.c.muted; font.pixelSize: 11; elide: Text.ElideRight; visible: text !== "" }
    }
    Item {
        id: arrow
        visible: tile.more
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: tile.more ? 30 : 0
        Text { anchors.centerIn: parent; text: "›"; color: tile.c.muted; font.pixelSize: 20 }
        MouseArea { anchors.fill: parent; onClicked: tile.opened() }
    }
}
