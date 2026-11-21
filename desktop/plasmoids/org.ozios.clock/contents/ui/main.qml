import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

// The time and the date in the middle of the bar, with an accent dot between them;
// clicked, a calendar with today in the accent colours. It wakes once a minute, on
// the minute, and draws nothing in between.
PlasmoidItem {
    id: root

    property date now: new Date()
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color accent2: Qt.hsva((accent.hsvHue + 0.194) % 1, accent.hsvSaturation, accent.hsvValue, 1)

    function untilNextMinute() {
        const d = new Date()
        return 60000 - (d.getSeconds() * 1000 + d.getMilliseconds()) + 40
    }

    Timer {
        id: tick
        running: true
        interval: root.untilNextMinute()
        onTriggered: {
            root.now = new Date()
            interval = root.untilNextMinute()
            start()
        }
    }

    toolTipMainText: now.toLocaleDateString(Qt.locale(), Locale.LongFormat)

    compactRepresentation: MouseArea {
        Layout.minimumWidth: line.implicitWidth + Kirigami.Units.largeSpacing * 2
        Layout.preferredWidth: Layout.minimumWidth
        Layout.fillHeight: true
        hoverEnabled: true
        // After the computer slept the next tick may still be far off.
        onEntered: root.now = new Date()
        onClicked: root.expanded = !root.expanded

        Row {
            id: line
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing * 2

            PlasmaComponents.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: root.now.toLocaleTimeString(Qt.locale(), Locale.ShortFormat)
                font.weight: Font.DemiBold
                font.pixelSize: Math.round(Kirigami.Theme.defaultFont.pixelSize * 1.08)
            }
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 4
                height: 4
                radius: 2
                color: root.accent
            }
            PlasmaComponents.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: root.now.toLocaleDateString(Qt.locale(), "ddd d MMM")
                opacity: 0.72
            }
        }
    }

    fullRepresentation: ColumnLayout {
        id: popup

        property date shown: new Date(root.now.getFullYear(), root.now.getMonth(), 1)

        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        Layout.minimumWidth: Layout.preferredWidth
        Layout.minimumHeight: implicitHeight
        spacing: Kirigami.Units.smallSpacing * 2

        // Each time the calendar opens it is today again.
        Connections {
            target: root
            function onExpandedChanged() {
                if (root.expanded) {
                    root.now = new Date()
                    popup.shown = new Date(root.now.getFullYear(), root.now.getMonth(), 1)
                }
            }
        }

        PlasmaComponents.Label {
            text: root.now.toLocaleTimeString(Qt.locale(), Locale.ShortFormat)
            font.pixelSize: Math.round(Kirigami.Theme.defaultFont.pixelSize * 2.6)
            font.weight: Font.Light
        }
        PlasmaComponents.Label {
            Layout.fillWidth: true
            text: root.now.toLocaleDateString(Qt.locale(), Locale.LongFormat)
            opacity: 0.75
            elide: Text.ElideRight
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: Kirigami.Theme.textColor
            opacity: 0.1
        }
        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: popup.shown.toLocaleDateString(Qt.locale(), "MMMM yyyy")
                font.weight: Font.DemiBold
            }
            PlasmaComponents.ToolButton {
                icon.name: "go-previous"
                text: "‹"
                display: PlasmaComponents.ToolButton.IconOnly
                onClicked: popup.shown = new Date(popup.shown.getFullYear(), popup.shown.getMonth() - 1, 1)
            }
            PlasmaComponents.ToolButton {
                icon.name: "go-next"
                text: "›"
                display: PlasmaComponents.ToolButton.IconOnly
                onClicked: popup.shown = new Date(popup.shown.getFullYear(), popup.shown.getMonth() + 1, 1)
            }
        }

        GridLayout {
            id: grid
            Layout.fillWidth: true
            columns: 7
            rowSpacing: 2
            columnSpacing: 2

            // In JavaScript's count, where Sunday is 0.
            readonly property int firstDay: Qt.locale().firstDayOfWeek % 7
            readonly property date start: {
                const first = popup.shown
                const back = (first.getDay() - firstDay + 7) % 7
                return new Date(first.getFullYear(), first.getMonth(), 1 - back)
            }

            Repeater {
                model: 7
                delegate: PlasmaComponents.Label {
                    required property int index
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: Qt.locale().dayName((grid.firstDay + index) % 7, Locale.NarrowFormat)
                    opacity: 0.55
                }
            }
            Repeater {
                model: 42
                delegate: Item {
                    id: cell
                    required property int index
                    readonly property date day: new Date(grid.start.getFullYear(), grid.start.getMonth(), grid.start.getDate() + index)
                    readonly property bool inMonth: day.getMonth() === popup.shown.getMonth()
                    readonly property bool today: day.toDateString() === root.now.toDateString()

                    Layout.fillWidth: true
                    implicitHeight: Math.round(Kirigami.Units.gridUnit * 1.55)

                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width, parent.height)
                        height: width
                        radius: width / 2
                        visible: cell.today
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: root.accent }
                            GradientStop { position: 1; color: root.accent2 }
                        }
                    }
                    PlasmaComponents.Label {
                        anchors.centerIn: parent
                        text: cell.day.getDate()
                        color: cell.today ? Qt.rgba(0, 0, 0, 0.8) : Kirigami.Theme.textColor
                        opacity: cell.inMonth ? 1 : 0.35
                        font.weight: cell.today ? Font.Bold : Font.Normal
                    }
                }
            }
        }
    }
}
