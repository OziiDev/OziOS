import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

// Tahta Köprüsü: two QR codes on the board. The teacher's makes their phone a
// remote, the students' gives them the lesson's notes. Big enough to scan
// from the back of the class.
ApplicationWindow {
    id: window
    width: 1100
    height: 720
    minimumWidth: 820
    minimumHeight: 560
    visible: true
    title: backend.tr("Board Bridge")
    color: Theme.ink

    property var info: ({})
    property bool busy: false
    property string message: ""
    property bool showTeacher: true

    Component.onCompleted: backend.call("start", "start", "[]")

    // Addresses change (Wi-Fi joins, the hotspot starts): look again now and then.
    Timer {
        interval: 5000
        running: true
        repeat: true
        onTriggered: backend.call("info", "info", "[]")
    }

    Connections {
        target: backend
        function onDone(task, json) {
            var r = JSON.parse(json)
            window.busy = false
            if (task === "share") {
                window.message = r.path ? backend.tr("Shared: the class can download it") : backend.tr("Could not share")
                window.info = Object.assign({}, window.info, { notes: r.notes })
                hide.restart()
            } else if (task !== "folder") {
                window.info = r
            }
        }
        function onFailed(task, text) {
            window.busy = false
            window.message = text
            hide.restart()
        }
    }

    Timer { id: hide; interval: 4000; onTriggered: window.message = "" }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Image {
                source: backend.mascot ? backend.mascot() : ""
                sourceSize.height: 72
                visible: source != ""
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    text: backend.tr("Board Bridge")
                    color: Theme.ice
                    font.family: Theme.family
                    font.pixelSize: 30
                    font.bold: true
                }
                Text {
                    Layout.fillWidth: true
                    text: backend.tr("Phones on the same Wi-Fi scan a code. Nothing to install.")
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 16
                    wrapMode: Text.WordWrap
                }
            }
            OButton {
                text: window.info.hotspot ? backend.tr("Turn off the board's Wi-Fi") : backend.tr("Board's own Wi-Fi")
                enabled: !window.busy
                implicitHeight: 48
                onClicked: {
                    window.busy = true
                    backend.call("hotspot", "hotspot", JSON.stringify([!window.info.hotspot]))
                }
            }
        }

        // No network at all: say what to do instead of showing dead codes.
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: window.info.online === false
            Text {
                anchors.centerIn: parent
                width: parent.width * 0.8
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: backend.tr("The board is on no network. Join the school Wi-Fi, or turn on the board's own Wi-Fi above and let the phones join it.")
                color: Theme.ice
                font.family: Theme.family
                font.pixelSize: 20
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 18
            visible: window.info.online === true

            Repeater {
                model: [
                    { key: "students", title: backend.tr("Students: lesson notes"), qr: "studentsQr",
                      note: backend.tr("Drawings from the screen pen and shared boards, one tap to download, or all as one PDF.") },
                    { key: "teacher", title: backend.tr("Teacher: phone remote"), qr: "teacherQr",
                      note: backend.tr("Next slide, touchpad, live view of the board. Only for you: hide it after scanning.") },
                    { key: "wifi", title: backend.tr("Board's Wi-Fi"), qr: "wifiQr", note: "" }
                ]
                delegate: Card {
                    id: tile
                    required property var modelData
                    readonly property bool shown: modelData.key === "wifi" ? !!window.info.hotspot
                                                  : (modelData.key === "teacher" ? window.showTeacher : true)
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: modelData.key !== "wifi" || !!window.info.hotspot
                    emphasis: modelData.key === "students"
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        Text {
                            Layout.fillWidth: true
                            text: modelData.title
                            color: Theme.ice
                            font.family: Theme.family
                            font.pixelSize: 20
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            Rectangle {
                                anchors.centerIn: parent
                                width: Math.min(parent.width, parent.height)
                                height: width
                                radius: 12
                                color: "white"
                                visible: tile.shown
                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    source: window.info[modelData.qr] || ""
                                    sourceSize.width: 600
                                    sourceSize.height: 600
                                    smooth: false
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                            OButton {
                                anchors.centerIn: parent
                                visible: !tile.shown
                                text: backend.tr("Show the code")
                                onClicked: window.showTeacher = true
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.key === "wifi"
                                  ? backend.tr("Network") + ": " + (window.info.ssid || "") + "   " + backend.tr("Password") + ": " + (window.info.password || "")
                                  : (window.info[modelData.key] || "")
                            color: modelData.key === "wifi" ? Theme.ice : Theme.cyan
                            font.family: Theme.mono
                            font.pixelSize: modelData.key === "wifi" ? 18 : 14
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideMiddle
                            visible: modelData.key !== "teacher" || window.showTeacher
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.note
                            visible: text !== ""
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                        }
                        OButton {
                            Layout.alignment: Qt.AlignHCenter
                            visible: modelData.key === "teacher" && window.showTeacher
                            text: backend.tr("Hide the code")
                            onClicked: window.showTeacher = false
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            OButton {
                primary: true
                implicitHeight: 52
                font.pixelSize: 17
                text: backend.tr("Share this board")
                enabled: !window.busy && window.info.online === true
                onClicked: {
                    window.busy = true
                    window.message = backend.tr("Taking the board…")
                    backend.call("share", "share", "[]")
                }
            }
            OButton {
                implicitHeight: 52
                text: backend.tr("Notes folder")
                onClicked: backend.call("folder", "folder", "[]")
            }
            Text {
                Layout.fillWidth: true
                text: window.message !== "" ? window.message
                      : backend.tr("Shared today") + ": " + (window.info.notes || 0)
                color: window.message !== "" ? Theme.good : Theme.muted
                font.family: Theme.family
                font.pixelSize: 16
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }
    }
}
