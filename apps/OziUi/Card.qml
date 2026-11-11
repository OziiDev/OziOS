import QtQuick

// A raised surface. `emphasis` adds the short corner ticks of the tesseract
// frame; use it on one large surface per view, never on small controls.
Rectangle {
    id: card
    property bool emphasis: false
    default property alias content: inner.data
    property int padding: 16

    color: Theme.raised
    radius: 8
    border.width: 1
    border.color: emphasis ? Theme.mid : Theme.far

    Item {
        id: inner
        anchors.fill: parent
        anchors.margins: card.padding
    }

    Repeater {
        model: card.emphasis ? 4 : 0
        Rectangle {
            required property int index
            width: 14
            height: 2
            color: Theme.cyan
            x: index % 2 === 0 ? -3 : card.width - width + 3
            y: index < 2 ? -1 : card.height - 1
            rotation: (index === 0 || index === 3) ? -45 : 45
            transformOrigin: index % 2 === 0 ? Item.Left : Item.Right
        }
    }
}
