import QtQuick

// A floating pill of the top bar: dark glass with a hairline of the accent.
Rectangle {
    id: island
    property var c
    property bool lit: false
    radius: height / 2
    color: Qt.alpha(c.raised, 0.92)
    border.width: 1
    border.color: Qt.alpha(lit ? c.accent : c.muted, lit ? 0.7 : 0.25)
    Behavior on border.color { ColorAnimation { duration: 200 } }
    Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
}
