import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

ApplicationWindow {
    id: window
    width: 880
    height: 720
    minimumWidth: 640
    minimumHeight: 600
    visible: true
    title: backend.tr("Welcome")
    color: Theme.ink

    property string version: ""
    property bool showAtLogin: true
    property bool live: false
    property bool edu: false
    property string message: ""
    property var themeChoices: []
    property var targetPalette: ({})

    Component.onCompleted: {
        backend.call("info", "info", "[]")
        backend.call("themes", "themes", "[]")
    }

    Connections {
        target: backend
        function onDone(task, json) {
            var result = JSON.parse(json)
            if (task === "info") {
                window.version = result.version
                window.showAtLogin = result.show
                window.live = result.live
                window.edu = result.edu
            } else if (task === "themes") {
                window.themeChoices = result
            } else if (task === "setTheme") {
                window.morphTo(result.palette)
                backend.call("themes", "themes", "[]")
            }
        }
        function onFailed(task, text) {
            window.message = text
        }
    }

    function launch(name) {
        message = ""
        backend.call("launch", "launch", JSON.stringify([name]))
    }

    // The window flows into the new theme's colours while the desktop switches with it.
    function morphTo(palette) {
        targetPalette = palette
        Theme.light = palette.light
        morph.restart()
    }

    ParallelAnimation {
        id: morph
        ColorAnimation { target: Theme; property: "ink"; to: window.targetPalette.ink || Theme.ink; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "raised"; to: window.targetPalette.raised || Theme.raised; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "control"; to: window.targetPalette.control || Theme.control; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "cyan"; to: window.targetPalette.cyan || Theme.cyan; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "mid"; to: window.targetPalette.mid || Theme.mid; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "far"; to: window.targetPalette.far || Theme.far; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "ice"; to: window.targetPalette.ice || Theme.ice; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "muted"; to: window.targetPalette.muted || Theme.muted; duration: 450; easing.type: Easing.InOutCubic }
        ColorAnimation { target: Theme; property: "onAccent"; to: window.targetPalette.onAccent || Theme.onAccent; duration: 450; easing.type: Easing.InOutCubic }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 16

        // Header: the mark, drawn as a tesseract, and the name.
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            Item {
                id: mark
                Layout.preferredWidth: 72
                Layout.preferredHeight: 72

                property real angle: 0
                // It turns for a few seconds when the window opens or comes to the front, and
                // while the pointer rests on it. A canvas is painted by the processor and Qt
                // Quick draws the whole window again for each new picture, so a mark that never
                // stopped kept a processor core busy on a computer without 3D.
                readonly property bool turning: window.visible && (settle.running || hover.hovered)
                HoverHandler { id: hover }
                Timer { id: settle; interval: 8000 }
                Connections {
                    target: window
                    function onActiveChanged() { if (window.active) settle.restart() }
                }
                Component.onCompleted: settle.start()
                Timer {
                    interval: 33
                    repeat: true
                    running: mark.turning
                    onTriggered: mark.angle = (mark.angle + Math.PI * 2 * 33 / 24000) % (Math.PI * 2)
                }
                onAngleChanged: canvas.requestPaint()
                Connections {
                    target: Theme
                    function onCyanChanged() { canvas.requestPaint() }
                }

                Canvas {
                    id: canvas
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        var verts = []
                        for (var i = 0; i < 16; i++) {
                            var v = [(i & 1) ? 1 : -1, (i & 2) ? 1 : -1, (i & 4) ? 1 : -1, (i & 8) ? 1 : -1]
                            var a = mark.angle, b = mark.angle * 0.7
                            var x = v[0] * Math.cos(a) - v[3] * Math.sin(a)
                            var w = v[0] * Math.sin(a) + v[3] * Math.cos(a)
                            var y = v[1] * Math.cos(b) - v[2] * Math.sin(b)
                            var z = v[1] * Math.sin(b) + v[2] * Math.cos(b)
                            var depth = 1 / (2.4 - w * 0.6)
                            verts.push({x: width / 2 + x * depth * width * 0.3, y: height / 2 + y * depth * height * 0.3,
                                        near: (w + 1) / 2})
                        }
                        ctx.lineCap = "round"
                        for (var p = 0; p < 16; p++) {
                            for (var bit = 0; bit < 4; bit++) {
                                var q = p ^ (1 << bit)
                                if (q < p) continue
                                var nearness = (verts[p].near + verts[q].near) / 2
                                ctx.strokeStyle = Qt.rgba(Theme.cyan.r, Theme.cyan.g, Theme.cyan.b, 0.25 + 0.75 * nearness)
                                ctx.lineWidth = 1 + 1.4 * nearness
                                ctx.beginPath()
                                ctx.moveTo(verts[p].x, verts[p].y)
                                ctx.lineTo(verts[q].x, verts[q].y)
                                ctx.stroke()
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: backend.tr("Welcome to OziOS")
                    color: Theme.ice
                    font.family: Theme.family
                    font.pixelSize: 28
                }
                Text {
                    text: window.version === "" ? "" : backend.tr("Version") + " " + window.version
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 14
                }
            }
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: backend.tr("Everything you need first is below. You can open this window again from the menu.")
            color: Theme.muted
            font.family: Theme.family
            font.pixelSize: 15
        }

        // The colours of the whole desktop, one swatch per theme; this window changes with it.
        RowLayout {
            Layout.fillWidth: true
            visible: window.themeChoices.length > 0
            spacing: 10

            Text {
                Layout.preferredWidth: 182
                leftPadding: 8
                text: backend.tr("Colours")
                color: Theme.cyan
                font.family: Theme.family
                font.pixelSize: 17
            }
            Repeater {
                model: window.themeChoices
                delegate: Item {
                    id: swatch
                    required property var modelData
                    objectName: "theme-" + modelData.id
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34

                    Rectangle {
                        anchors.centerIn: parent
                        width: swatchArea.containsMouse ? 34 : 30
                        height: width
                        radius: width / 2
                        color: swatch.modelData.background
                        border.width: swatch.modelData.current ? 2 : 1
                        border.color: swatch.modelData.current ? Theme.ice : Theme.far
                        Behavior on width { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.5
                            height: width
                            radius: width / 2
                            color: swatch.modelData.accent
                        }
                    }
                    MouseArea {
                        id: swatchArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            window.message = ""
                            backend.call("setTheme", "setTheme", JSON.stringify([swatch.modelData.id]))
                        }
                    }
                    ToolTip.visible: swatchArea.containsMouse
                    ToolTip.text: swatch.modelData.name
                    ToolTip.delay: 300
                }
            }
            Text {
                Layout.fillWidth: true
                leftPadding: 8
                wrapMode: Text.WordWrap
                text: backend.tr("The whole desktop changes with it. The panel has the same choice later.")
                color: Theme.muted
                font.family: Theme.family
                font.pixelSize: 13
            }
        }

        // Only in a live session: this is how the system gets onto a disk.
        Card {
            visible: window.live
            Layout.fillWidth: true
            Layout.preferredHeight: 84
            emphasis: true

            RowLayout {
                anchors.fill: parent
                spacing: 16
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: backend.tr("Install OziOS")
                        color: Theme.cyan
                        font.family: Theme.family
                        font.pixelSize: 18
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: backend.tr("You are running from the install medium. Put OziOS on this computer when you are ready; nothing changes until you confirm.")
                        color: Theme.muted
                        font.family: Theme.family
                        font.pixelSize: 13
                    }
                }
                OButton {
                    primary: true
                    text: backend.tr("Install")
                    onClicked: window.launch("install")
                }
            }
        }

        // Things to do, as plain rows: a name, what it does, a line under each.
        Flickable {
            id: listing
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: rows.implicitHeight
            ScrollBar.vertical: ScrollBar {}

            Column {
                id: rows
                width: listing.width
                Repeater {
                    model: (window.edu ? [
                        { key: "pen", title: backend.tr("Screen pen"), text: backend.tr("Draw on top of anything on the screen with a pen or a finger.") },
                        { key: "whiteboard", title: backend.tr("Whiteboard"), text: backend.tr("A blank page to write on, with pages, images and PDF markup.") },
                        { key: "classroom", title: backend.tr("Classroom"), text: backend.tr("Pick a student, make groups and time an activity.") },
                        { key: "eba", title: backend.tr("EBA portal"), text: backend.tr("Open the Education Information Network in the browser.") }
                    ] : [
                        { key: "gaming", title: backend.tr("Games"), text: backend.tr("Install Steam, game mode and the graphics libraries that fit this computer.") }
                    ]).concat([
                        { key: "store", title: backend.tr("Get software"), text: backend.tr("Install programs, check a package before it goes on your system, and keep everything updated.") },
                        { key: "windows", title: backend.tr("Windows programs"), text: backend.tr("Set up the Windows layer so .exe files open from your file manager.") },
                        { key: "network", title: backend.tr("Network"), text: backend.tr("Connect to Wi-Fi or a wired network.") },
                        { key: "display", title: backend.tr("Display"), text: backend.tr("Resolution, scaling and refresh rate.") },
                        { key: "settings", title: backend.tr("All settings"), text: backend.tr("Everything else about how the system looks and works.") }
                    ]).concat(window.edu ? [] : [
                        { key: "terminal", title: backend.tr("Terminal"), text: backend.tr("The OziOS terminal, with the turning tesseract.") }
                    ])
                    delegate: Rectangle {
                        id: row
                        required property var modelData
                        width: rows.width
                        height: Math.max(48, rowText.implicitHeight + 20)
                        color: area.containsMouse ? Theme.raised : "transparent"

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.control
                        }
                        Text {
                            id: rowTitle
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            width: 190
                            text: row.modelData.title
                            color: area.containsMouse ? Theme.ice : Theme.cyan
                            font.family: Theme.family
                            font.pixelSize: 17
                        }
                        Text {
                            id: rowText
                            x: 212
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 232
                            wrapMode: Text.WordWrap
                            text: row.modelData.text
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 14
                        }
                        MouseArea {
                            id: area
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: window.launch(row.modelData.key)
                        }
                    }
                }
            }
        }

        Text {
            visible: window.message !== ""
            Layout.fillWidth: true
            text: window.message
            color: Theme.danger
            font.family: Theme.family
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            OSwitch {
                text: backend.tr("Show this window when I log in")
                checked: window.showAtLogin
                onToggled: backend.call("showAtLogin", "showAtLogin", JSON.stringify([checked]))
            }
            Item { Layout.fillWidth: true }
            OButton {
                text: backend.tr("Apply the OziOS look again")
                onClicked: window.launch("theme")
            }
        }
    }
}
