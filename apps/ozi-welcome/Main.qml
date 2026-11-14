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

    Component.onCompleted: backend.call("info", "info", "[]")

    Connections {
        target: backend
        function onDone(task, json) {
            var result = JSON.parse(json)
            if (task === "info") {
                window.version = result.version
                window.showAtLogin = result.show
                window.live = result.live
                window.edu = result.edu
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 24

        // Header: the mark, drawn as a tesseract, and the name.
        RowLayout {
            Layout.fillWidth: true
            spacing: 20

            Item {
                id: mark
                Layout.preferredWidth: 96
                Layout.preferredHeight: 96

                property real angle: 0
                NumberAnimation on angle { from: 0; to: Math.PI * 2; duration: 24000; loops: Animation.Infinite; running: window.visible }
                onAngleChanged: canvas.requestPaint()

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
                                ctx.strokeStyle = Qt.rgba(0, 0.9, 1, 0.25 + 0.75 * nearness)
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
                    font.pixelSize: 32
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

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: window.width > 760 ? 3 : 2
            rowSpacing: 16
            columnSpacing: 16

            Repeater {
                model: (window.edu ? [
                    { key: "pen", title: backend.tr("Screen pen"), text: backend.tr("Draw on top of anything on the screen with a pen or a finger.") },
                    { key: "whiteboard", title: backend.tr("Whiteboard"), text: backend.tr("A blank page to write on, with pages, images and PDF markup.") },
                    { key: "classroom", title: backend.tr("Classroom"), text: backend.tr("Pick a student, make groups and time an activity.") },
                    { key: "eba", title: backend.tr("EBA portal"), text: backend.tr("Open the Education Information Network in the browser.") }
                ] : []).concat([
                    { key: "store", title: backend.tr("Get software"), text: backend.tr("Install programs, check a package before it goes on your system, and keep everything updated.") },
                    { key: "windows", title: backend.tr("Windows programs"), text: backend.tr("Set up the Windows layer so .exe files open from your file manager.") },
                    { key: "network", title: backend.tr("Network"), text: backend.tr("Connect to Wi-Fi or a wired network.") },
                    { key: "display", title: backend.tr("Display"), text: backend.tr("Resolution, scaling and refresh rate.") },
                    { key: "settings", title: backend.tr("All settings"), text: backend.tr("Everything else about how the system looks and works.") }
                ]).concat(window.edu ? [] : [
                    { key: "terminal", title: backend.tr("Terminal"), text: backend.tr("The OziOS terminal, with the turning tesseract.") }
                ])
                delegate: Card {
                    id: tile
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 104
                    border.color: area.containsMouse ? Theme.cyan : Theme.far
                    Behavior on border.color { ColorAnimation { duration: 140 } }

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 6
                        Text {
                            text: tile.modelData.title
                            color: Theme.cyan
                            font.family: Theme.family
                            font.pixelSize: 18
                        }
                        Text {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            wrapMode: Text.WordWrap
                            text: tile.modelData.text
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 13
                        }
                    }

                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: window.launch(tile.modelData.key)
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
