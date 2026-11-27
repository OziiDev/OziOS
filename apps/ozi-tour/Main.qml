import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi
// layer: import

// Ozi-chan along the bottom of the screen: she says what the program above
// her does, then the next one opens. Touching her bubble pauses; the arrows
// go back and forth; × ends the tour.
Window {
    id: window
    width: Screen.width
    height: 360
    visible: true
    color: "transparent"
    title: "OziOS turu"
    // layer: window

    property var scenes: []
    property int index: -1
    property bool paused: false
    property real progress: 0          // 0..1 through the scene
    readonly property var scene: index >= 0 && index < scenes.length ? scenes[index] : null

    Component.onCompleted: backend.call("scenes", "scenes", "[]")

    function go(i) {
        if (scenes.length === 0)
            return
        if (index >= 0)
            backend.call("leave", "leave", "[]")
        if (i >= scenes.length) {
            if (!backend.loop()) {
                Qt.quit()
                return
            }
            i = 0
        }
        index = Math.max(0, i)
        progress = 0
        bubble.show()
        // Give the program a moment to open before Ozi-chan starts talking about it.
        enterLater.restart()
    }

    Timer {
        id: enterLater
        interval: 350
        onTriggered: backend.call("enter", "enter", JSON.stringify([window.index]))
    }

    Connections {
        target: backend
        function onDone(task, json) {
            if (task === "scenes") {
                window.scenes = JSON.parse(json).scenes
                window.go(0)
            }
        }
    }

    // The clock of a scene.
    Timer {
        interval: 50
        running: window.scene !== null && !window.paused
        repeat: true
        onTriggered: {
            window.progress += 0.05 / window.scene.seconds
            if (window.progress >= 1)
                window.go(window.index + 1)
        }
    }

    Item {
        anchors.fill: parent
        anchors.leftMargin: 24
        anchors.rightMargin: 24
        anchors.bottomMargin: 92          // above the dock

        // Ozi-chan: bobs a little, hops when a new scene starts.
        Image {
            id: chan
            width: 150
            height: 195
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            sourceSize.width: 300
            sourceSize.height: 390
            source: window.scene ? backend.mascot(window.scene.mascot) : ""
            fillMode: Image.PreserveAspectFit
            transform: Translate { id: bob; y: 0 }
            SequentialAnimation {
                running: !window.paused
                loops: Animation.Infinite
                NumberAnimation { target: bob; property: "y"; from: 0; to: -6; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { target: bob; property: "y"; from: -6; to: 0; duration: 900; easing.type: Easing.InOutSine }
            }
        }

        Rectangle {
            id: bubble
            anchors.left: chan.right
            anchors.leftMargin: 14
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 18
            width: Math.min(parent.width - chan.width - 40, 900)
            height: content.implicitHeight + 36
            radius: 22
            color: Theme.raised
            border.color: Theme.cyan
            border.width: 2
            opacity: 0
            scale: 0.96
            transformOrigin: Item.BottomLeft

            function show() {
                pop.restart()
            }
            ParallelAnimation {
                id: pop
                NumberAnimation { target: bubble; property: "opacity"; from: 0; to: 0.97; duration: 260; easing.type: Easing.OutCubic }
                NumberAnimation { target: bubble; property: "scale"; from: 0.9; to: 1; duration: 320; easing.type: Easing.OutBack }
            }

            // The bubble's tail, pointing at Ozi-chan.
            Rectangle {
                width: 22
                height: 22
                rotation: 45
                color: Theme.raised
                border.color: Theme.cyan
                border.width: 2
                x: -10
                y: parent.height - 52
                z: -1
            }

            MouseArea {
                anchors.fill: parent
                onClicked: window.paused = !window.paused
            }

            RowLayout {
                id: content
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 18
                spacing: 18

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        Layout.fillWidth: true
                        text: window.scene ? window.scene.title : ""
                        color: Theme.cyan
                        font.family: Theme.family
                        font.pixelSize: 26
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: window.scene ? window.scene.text : ""
                        color: Theme.ice
                        font.family: Theme.family
                        font.pixelSize: 19
                        wrapMode: Text.WordWrap
                        maximumLineCount: 4
                        elide: Text.ElideRight
                    }
                    // Where the tour is: a dot per scene, the current one fills as it goes.
                    Row {
                        spacing: 8
                        topPadding: 4
                        Repeater {
                            model: window.scenes.length
                            Rectangle {
                                required property int index
                                width: index === window.index ? 46 : 10
                                height: 10
                                radius: 5
                                color: index < window.index ? Theme.cyan : Theme.control
                                Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                                Rectangle {
                                    visible: index === window.index
                                    width: parent.width * window.progress
                                    height: parent.height
                                    radius: 5
                                    color: Theme.cyan
                                }
                            }
                        }
                        Text {
                            text: window.paused ? "  ⏸  durdu: devam için dokun" : ""
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 15
                        }
                    }
                }

                Rectangle {
                    visible: !!(window.scene && window.scene.qrImage)
                    Layout.preferredWidth: 140
                    Layout.preferredHeight: 140
                    radius: 10
                    color: "white"
                    Image {
                        anchors.fill: parent
                        anchors.margins: 8
                        source: window.scene && window.scene.qrImage ? window.scene.qrImage : ""
                        sourceSize.width: 400
                        sourceSize.height: 400
                        smooth: false
                    }
                }

                ColumnLayout {
                    spacing: 8
                    Repeater {
                        model: [{ t: "×", a: "close" }, { t: "‹", a: "prev" }, { t: "›", a: "next" }]
                        Rectangle {
                            required property var modelData
                            width: 52
                            height: 44
                            radius: 12
                            color: tap.pressed ? Theme.mid : Theme.control
                            Text {
                                anchors.centerIn: parent
                                text: modelData.t
                                color: Theme.ice
                                font.pixelSize: 26
                            }
                            MouseArea {
                                id: tap
                                anchors.fill: parent
                                onClicked: {
                                    if (modelData.a === "close") {
                                        backend.call("leave", "leave", "[]")
                                        quitLater.start()
                                    } else if (modelData.a === "prev") {
                                        window.go(Math.max(0, window.index - 1))
                                    } else {
                                        window.go(window.index + 1)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Timer { id: quitLater; interval: 300; onTriggered: Qt.quit() }
}
