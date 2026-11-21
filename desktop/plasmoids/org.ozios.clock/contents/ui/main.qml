import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

// The time and the date in the middle of the bar, with an accent dot between them;
// clicked, a calendar with today in the accent colours. It wakes once a minute, on
// the minute, and draws nothing in between. While music plays, the island grows to
// show the track: a click on it pauses, and the calendar has the player's buttons.
PlasmoidItem {
    id: root

    property date now: new Date()
    readonly property color accent: Kirigami.Theme.highlightColor
    // The accent's partner, as in the window frames' glow and the desktop lights.
    readonly property color accent2: {
        const hue = Math.max(0, accent.hsvHue) * 360
        const d = ((270 - hue + 540) % 360) - 180
        const shift = Math.abs(d) < 20 ? 40 : Math.sign(d) * Math.min(Math.abs(d), 70)
        return Qt.hsva((((hue + shift) % 360) + 360) % 360 / 360, accent.hsvSaturation, accent.hsvValue, 1)
    }

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

    // Plasma's media players, loaded apart (NowPlaying.qml): if that fails, the clock stays.
    Loader {
        id: mediaLoader
        source: "NowPlaying.qml"
    }
    readonly property var media: mediaLoader.status === Loader.Ready ? mediaLoader.item : null
    readonly property bool hasMedia: !!media && media.active

    toolTipMainText: now.toLocaleDateString(Qt.locale(), Locale.LongFormat)
    toolTipSubText: hasMedia ? media.title + (media.artist ? " — " + media.artist : "") : ""

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
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                visible: root.hasMedia
                width: 4
                height: 4
                radius: 2
                color: root.accent2
            }
            // The track, after three bars in the accent colours. The bars dance for a few
            // seconds when a track starts or changes, then rest: a panel redraws whole
            // for every frame, and music can play for hours.
            Item {
                id: music
                objectName: "music"
                visible: root.hasMedia
                anchors.verticalCenter: parent.verticalCenter
                width: musicRow.implicitWidth
                height: musicRow.implicitHeight

                Row {
                    id: musicRow
                    spacing: Kirigami.Units.smallSpacing + 2

                    Row {
                        id: bars
                        objectName: "bars"
                        property bool dancing: false
                        // On while a track has just started, never with animations off.
                        function wake() {
                            dancing = Kirigami.Units.longDuration > 0 && !!root.media && root.media.playing
                            if (dancing) {
                                rest.restart()
                            }
                        }
                        anchors.verticalCenter: parent.verticalCenter
                        height: Math.round(trackLabel.implicitHeight * 0.7)
                        spacing: 2

                        Timer {
                            id: rest
                            interval: 6000
                            onTriggered: bars.dancing = false
                        }
                        Repeater {
                            model: [0.5, 1, 0.7]
                            delegate: Rectangle {
                                id: bar
                                required property real modelData
                                required property int index
                                property real level: modelData
                                anchors.bottom: parent.bottom
                                width: 3
                                radius: 1.5
                                height: Math.max(3, Math.round(bars.height * (bars.dancing ? level : modelData)))
                                opacity: root.media && root.media.playing ? 1 : 0.45
                                gradient: Gradient {
                                    GradientStop { position: 0; color: root.accent2 }
                                    GradientStop { position: 1; color: root.accent }
                                }
                                Behavior on height {
                                    NumberAnimation { duration: 170; easing.type: Easing.OutQuad }
                                }
                                Timer {
                                    running: bars.dancing
                                    repeat: true
                                    interval: 190 + bar.index * 40
                                    onTriggered: bar.level = 0.25 + Math.random() * 0.75
                                }
                            }
                        }
                    }
                    PlasmaComponents.Label {
                        id: trackLabel
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(implicitWidth, Kirigami.Units.gridUnit * 9)
                        text: root.media ? root.media.title : ""
                        elide: Text.ElideRight
                        opacity: root.media && root.media.playing ? 0.9 : 0.5
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -Kirigami.Units.smallSpacing
                    onClicked: root.media.toggle()
                }
                Connections {
                    target: root.media
                    function onTitleChanged() { bars.wake() }
                    function onPlayingChanged() { bars.wake() }
                }
                Component.onCompleted: bars.wake()
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
                objectName: "previousMonth"
                icon.name: "go-previous"
                text: "‹"
                display: PlasmaComponents.ToolButton.IconOnly
                onClicked: popup.shown = new Date(popup.shown.getFullYear(), popup.shown.getMonth() - 1, 1)
            }
            PlasmaComponents.ToolButton {
                objectName: "nextMonth"
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
                    objectName: "dayName"
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    // The narrow names (M T W, P S Ç); the C locale, which the live session
                    // runs in, has numbers there, so it gets two letters of the short ones.
                    text: {
                        const day = (grid.firstDay + index) % 7
                        const narrow = Qt.locale().dayName(day, Locale.NarrowFormat)
                        return /^[0-9]+$/.test(narrow) ? Qt.locale().dayName(day, Locale.ShortFormat).slice(0, 2) : narrow
                    }
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

        // What is playing: the cover (or a note on the accent colours) and the buttons to
        // go back, pause and skip.
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            visible: root.hasMedia
            color: Kirigami.Theme.textColor
            opacity: 0.1
        }
        RowLayout {
            objectName: "nowPlaying"
            Layout.fillWidth: true
            visible: root.hasMedia
            spacing: Kirigami.Units.largeSpacing

            Item {
                Layout.preferredWidth: Math.round(Kirigami.Units.gridUnit * 2.6)
                Layout.preferredHeight: Layout.preferredWidth

                Rectangle {
                    anchors.fill: parent
                    visible: cover.status !== Image.Ready
                    radius: Kirigami.Units.smallSpacing * 2
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: root.accent }
                        GradientStop { position: 1; color: root.accent2 }
                    }
                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: Math.round(parent.width * 0.55)
                        height: width
                        source: "music-note-16th"
                        isMask: true
                        color: Qt.rgba(0, 0, 0, 0.72)
                    }
                }
                Kirigami.ShadowedImage {
                    id: cover
                    anchors.fill: parent
                    visible: status === Image.Ready
                    radius: Kirigami.Units.smallSpacing * 2
                    source: root.media ? root.media.art : ""
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: root.media ? root.media.title : ""
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: root.media ? (root.media.artist || root.media.identity) : ""
                    opacity: 0.7
                    elide: Text.ElideRight
                }
            }
            PlasmaComponents.ToolButton {
                objectName: "mediaPrevious"
                icon.name: "media-skip-backward"
                text: "⏮"
                display: PlasmaComponents.ToolButton.IconOnly
                enabled: !!root.media && root.media.canPrevious
                onClicked: root.media.previous()
            }
            PlasmaComponents.ToolButton {
                objectName: "mediaToggle"
                icon.name: root.media && root.media.playing ? "media-playback-pause" : "media-playback-start"
                text: root.media && root.media.playing ? "⏸" : "⏵"
                display: PlasmaComponents.ToolButton.IconOnly
                enabled: !!root.media && root.media.canControl
                onClicked: root.media.toggle()
            }
            PlasmaComponents.ToolButton {
                objectName: "mediaNext"
                icon.name: "media-skip-forward"
                text: "⏭"
                display: PlasmaComponents.ToolButton.IconOnly
                enabled: !!root.media && root.media.canNext
                onClicked: root.media.next()
            }
        }
    }
}
