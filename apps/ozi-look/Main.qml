import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

// Look: how windows look and move. A small desktop at the top shows every change
// before the real one takes it on; three presets set everything at once. With
// --keys (Meta+K) the window shows only the keys worth knowing.
ApplicationWindow {
    id: window
    readonly property bool keysOnly: backend.page() === "keys"

    width: keysOnly ? 560 : 920
    height: keysOnly ? 620 : 700
    minimumWidth: keysOnly ? 460 : 720
    minimumHeight: keysOnly ? 480 : 520
    visible: true
    title: keysOnly ? backend.tr("Shortcuts") : backend.tr("Look")
    color: Theme.ink

    property var values: ({radius: 10, outline: 2, glow: true, titlebar: true, gaps: 10, tiling: false,
                           blur: true, speed: "normal"})
    property string preset: ""
    property var presets: []
    property var speeds: []
    property string message: ""

    Component.onCompleted: if (!keysOnly) backend.call("state", "state", "[]")

    Connections {
        target: backend
        function onDone(task, json) {
            var result = JSON.parse(json)
            if (task === "state") {
                window.values = result.values
                window.preset = result.preset
                window.presets = result.presets
                window.speeds = result.speeds
            } else {
                backend.call("state", "state", "[]")
            }
        }
        function onFailed(task, text) {
            window.message = text
        }
    }

    // The preview takes the new value at once; the desktop a moment later.
    function change(name, value) {
        var next = Object.assign({}, values)
        next[name] = value
        values = next
        message = ""
        backend.call("set", "set", JSON.stringify([name, value]))
    }

    function pick(id) {
        message = ""
        backend.call("preset", "preset", JSON.stringify([id]))
    }

    Shortcut {
        sequence: "Escape"
        enabled: window.keysOnly
        onActivated: window.close()
    }

    // The keys worth knowing; the same list on the card and at the end of the Look window.
    readonly property var keys: [
        ["Meta", backend.tr("Programs and search")],
        ["Meta+1 … 4", backend.tr("Go to a desktop")],
        ["Meta+Ctrl+1 … 4", backend.tr("Take the window to a desktop")],
        ["Meta+T", backend.tr("Tile the windows of this desktop, or let them go")],
        ["Meta+F", backend.tr("Let a window float above the tiles")],
        ["Meta+Q", backend.tr("Close the window")],
        ["Meta+Enter", backend.tr("Terminal")],
        ["Meta+E", backend.tr("Files")],
        ["Meta+W", backend.tr("All windows and desktops at a glance")],
        ["Alt+Tab", backend.tr("Switch between windows")],
        ["Meta+↑ / ← / →", backend.tr("Maximise, or fill half of the screen")],
        [backend.tr("Meta+drag"), backend.tr("Move a window from anywhere in it")],
        ["Meta+V", backend.tr("Clipboard")],
        ["Meta+L", backend.tr("Lock the screen")],
        ["Meta+K", backend.tr("This card")]
    ]

    component KeyList: ColumnLayout {
        spacing: 6
        Repeater {
            model: window.keys
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 14
                Rectangle {
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 28
                    radius: 6
                    color: Theme.control
                    border.width: 1
                    border.color: Theme.far
                    Text {
                        anchors.centerIn: parent
                        text: modelData[0]
                        color: Theme.cyan
                        font.family: Theme.mono
                        font.pixelSize: 13
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: modelData[1]
                    color: Theme.ice
                    font.family: Theme.family
                    font.pixelSize: 14
                    elide: Text.ElideRight
                }
            }
        }
    }

    component SectionTitle: Text {
        color: Theme.ice
        font.family: Theme.family
        font.pixelSize: 17
        font.weight: Font.DemiBold
    }

    component Hint: Text {
        Layout.fillWidth: true
        color: Theme.muted
        font.family: Theme.family
        font.pixelSize: 13
        wrapMode: Text.WordWrap
    }

    // A labelled slider row whose value goes to the desktop when the slider is let go.
    component ValueRow: RowLayout {
        id: row
        property string name
        property string label
        property int from: 0
        property int to: 10
        Layout.fillWidth: true
        spacing: 14
        Text {
            Layout.preferredWidth: 190
            text: row.label
            color: Theme.ice
            font.family: Theme.family
            font.pixelSize: 14
        }
        OSlider {
            id: slider
            Layout.fillWidth: true
            from: row.from
            to: row.to
            stepSize: 1
            snapMode: Slider.SnapAlways
            value: window.values[row.name] !== undefined ? window.values[row.name] : 0
            onMoved: {
                var next = Object.assign({}, window.values)
                next[row.name] = Math.round(value)
                window.values = next
            }
            onPressedChanged: if (!pressed) window.change(row.name, Math.round(value))
        }
        Text {
            Layout.preferredWidth: 36
            horizontalAlignment: Text.AlignRight
            text: Math.round(slider.value)
            color: Theme.cyan
            font.family: Theme.mono
            font.pixelSize: 14
        }
    }

    // --- the card of keys alone ------------------------------------------------------------
    ColumnLayout {
        visible: window.keysOnly
        anchors.fill: parent
        anchors.margins: 28
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            SectionTitle {
                Layout.fillWidth: true
                text: backend.tr("Shortcuts")
                font.pixelSize: 22
            }
            OButton {
                text: backend.tr("Close")
                onClicked: window.close()
            }
        }
        Hint { text: backend.tr("Meta is the key with the Windows logo.") }
        KeyList { Layout.fillWidth: true }
        Item { Layout.fillHeight: true }
    }

    // --- the Look window -------------------------------------------------------------------
    ScrollView {
        id: scroller
        visible: !window.keysOnly
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: scroller.availableWidth
            spacing: 18

            Item { Layout.preferredHeight: 10 }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                spacing: 4
                SectionTitle {
                    text: backend.tr("Look")
                    font.pixelSize: 26
                }
                Hint { text: backend.tr("How windows look and move. Every change shows at once.") }
            }

            // A small desktop: two floating windows, or three tiles, in the chosen look.
            Rectangle {
                id: screen
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.preferredHeight: Math.round(width * 0.34)
                radius: 10
                clip: true
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.darker(Theme.ink, 1.05) }
                    GradientStop { position: 1; color: Qt.lighter(Theme.ink, 1.35) }
                }
                border.width: 1
                border.color: Theme.far

                readonly property real unit: width / 640
                readonly property bool tiled: window.values.tiling === true
                readonly property real gap: Math.max(2, window.values.gaps * unit)
                readonly property real below: 22 * unit + gap

                // The islands along the top.
                Repeater {
                    model: [[0.012, 0.13], [0.43, 0.14], [0.83, 0.158]]
                    Rectangle {
                        required property var modelData
                        x: screen.width * modelData[0]
                        y: 5 * screen.unit
                        width: screen.width * modelData[1]
                        height: 16 * screen.unit
                        radius: height / 2
                        color: Theme.raised
                        border.width: 1
                        border.color: Theme.far
                    }
                }

                Repeater {
                    model: 3
                    delegate: Item {
                        id: win
                        required property int index
                        readonly property bool active: index === 0
                        readonly property real r: Math.min(window.values.radius * screen.unit, 14)
                        readonly property var frame: {
                            var g = screen.gap, t = screen.below, w = screen.width, h = screen.height
                            if (screen.tiled) {
                                var half = (w - 3 * g) / 2
                                if (index === 0) return [g, t, half, h - t - g]
                                var tall = (h - t - 3 * g) / 2
                                return [2 * g + half, index === 1 ? t : t + tall + g, half, tall]
                            }
                            if (index === 0) return [w * 0.30, h * 0.30, w * 0.44, h * 0.56]
                            if (index === 1) return [w * 0.10, h * 0.22, w * 0.38, h * 0.52]
                            return [w * 0.62, h * 0.40, w * 0.30, h * 0.40]
                        }
                        x: frame[0]
                        y: frame[1]
                        width: frame[2]
                        height: frame[3]
                        z: active ? 3 : 2 - index
                        Behavior on x { NumberAnimation { duration: 380; easing.type: Easing.OutQuint } }
                        Behavior on y { NumberAnimation { duration: 380; easing.type: Easing.OutQuint } }
                        Behavior on width { NumberAnimation { duration: 380; easing.type: Easing.OutQuint } }
                        Behavior on height { NumberAnimation { duration: 380; easing.type: Easing.OutQuint } }

                        // The glow: a few soft rings in the accent around the active window.
                        Repeater {
                            model: win.active && window.values.glow ? 4 : 0
                            Rectangle {
                                required property int index
                                anchors.fill: parent
                                anchors.margins: -(index + 1) * 2.5 * screen.unit
                                radius: win.r + (index + 1) * 2.5 * screen.unit
                                color: "transparent"
                                border.width: 2.5 * screen.unit
                                border.color: Theme.cyan
                                opacity: 0.16 - index * 0.035
                            }
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: win.r
                            color: Theme.raised
                            border.width: Math.max(1, (win.active ? window.values.outline : 1) * screen.unit * 1.2)
                            border.color: win.active && window.values.outline > 0 ? Theme.cyan : Theme.far
                            Behavior on radius { NumberAnimation { duration: 200 } }

                            // The title bar with its three lights, when there are title bars.
                            Item {
                                visible: window.values.titlebar
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 16 * screen.unit
                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 7 * screen.unit
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4 * screen.unit
                                    Repeater {
                                        model: ["#FEBC2E", Theme.cyan, "#FF5F57"]
                                        Rectangle {
                                            required property var modelData
                                            width: 6 * screen.unit
                                            height: width
                                            radius: width / 2
                                            color: win.active ? modelData : Theme.far
                                        }
                                    }
                                }
                            }
                            // Lines standing for the window's contents.
                            Column {
                                x: 10 * screen.unit
                                y: (window.values.titlebar ? 22 : 10) * screen.unit
                                spacing: 6 * screen.unit
                                Repeater {
                                    model: 3
                                    Rectangle {
                                        required property int index
                                        width: (win.width - 20 * screen.unit) * (index === 0 ? 0.7 : index === 1 ? 0.9 : 0.5)
                                        height: 4 * screen.unit
                                        radius: height / 2
                                        color: index === 0 && win.active ? Theme.mid : Theme.far
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // The presets.
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                spacing: 14
                Repeater {
                    model: window.presets
                    delegate: Card {
                        id: card
                        required property var modelData
                        readonly property bool chosen: window.preset === modelData.id
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        emphasis: chosen
                        border.color: chosen ? Theme.cyan : (area.containsMouse ? Theme.mid : Theme.far)
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 4
                            Text {
                                text: card.modelData.name
                                color: card.chosen ? Theme.cyan : Theme.ice
                                font.family: Theme.family
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                text: card.modelData.text
                                color: Theme.muted
                                font.family: Theme.family
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                        MouseArea {
                            id: area
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: window.pick(card.modelData.id)
                        }
                    }
                }
            }

            Text {
                visible: window.message !== ""
                Layout.leftMargin: 32
                text: window.message
                color: Theme.caution
                font.family: Theme.family
                font.pixelSize: 13
            }

            // Windows.
            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.preferredHeight: windowsColumn.implicitHeight + 32
                ColumnLayout {
                    id: windowsColumn
                    anchors.fill: parent
                    spacing: 8
                    SectionTitle { text: backend.tr("Windows") }
                    ValueRow { name: "radius"; label: backend.tr("Corner radius"); from: 0; to: 24 }
                    ValueRow { name: "outline"; label: backend.tr("Outline"); from: 0; to: 4 }
                    OSwitch {
                        text: backend.tr("Glow around the active window")
                        checked: window.values.glow === true
                        onToggled: window.change("glow", checked)
                    }
                    OSwitch {
                        text: backend.tr("Title bars")
                        checked: window.values.titlebar === true
                        onToggled: window.change("titlebar", checked)
                    }
                    Hint {
                        visible: window.values.titlebar === false
                        text: backend.tr("Without title bars, hold Meta and drag a window to move it.")
                    }
                }
            }

            // Tiling.
            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.preferredHeight: tilingColumn.implicitHeight + 32
                ColumnLayout {
                    id: tilingColumn
                    anchors.fill: parent
                    spacing: 8
                    SectionTitle { text: backend.tr("Tiling") }
                    Hint { text: backend.tr("Meta+T tiles the desktop in use, Meta+F lets a window float above the tiles.") }
                    OSwitch {
                        text: backend.tr("Tile every desktop")
                        checked: window.values.tiling === true
                        onToggled: window.change("tiling", checked)
                    }
                    ValueRow { name: "gaps"; label: backend.tr("Gaps between tiles"); from: 0; to: 40 }
                }
            }

            // Motion.
            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.preferredHeight: motionColumn.implicitHeight + 32
                ColumnLayout {
                    id: motionColumn
                    anchors.fill: parent
                    spacing: 10
                    SectionTitle { text: backend.tr("Motion") }
                    RowLayout {
                        spacing: 8
                        Text {
                            Layout.preferredWidth: 190
                            text: backend.tr("Animation speed")
                            color: Theme.ice
                            font.family: Theme.family
                            font.pixelSize: 14
                        }
                        Repeater {
                            model: window.speeds
                            delegate: OButton {
                                required property var modelData
                                text: modelData.name
                                primary: window.values.speed === modelData.id
                                onClicked: window.change("speed", modelData.id)
                            }
                        }
                    }
                    OSwitch {
                        text: backend.tr("Blur behind panels and menus")
                        checked: window.values.blur === true
                        onToggled: window.change("blur", checked)
                    }
                }
            }

            // Keys.
            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 32
                Layout.rightMargin: 32
                Layout.preferredHeight: keysColumn.implicitHeight + 32
                ColumnLayout {
                    id: keysColumn
                    anchors.fill: parent
                    spacing: 10
                    SectionTitle { text: backend.tr("Shortcuts") }
                    KeyList { Layout.fillWidth: true }
                }
            }

            Item { Layout.preferredHeight: 18 }
        }
    }
}
