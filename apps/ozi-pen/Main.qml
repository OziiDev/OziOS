import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window
import OziUi

// A transparent layer over the whole screen holds the strokes; a small toolbar
// (a child window, so it always stays above the layer) chooses the tool. While
// "Use screen" is on, the layer lets every touch and click through to the
// programs underneath.
Window {
    id: board
    visibility: Window.FullScreen
    visible: true
    color: "transparent"
    title: backend.tr("Screen pen")
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
           | (passThrough ? Qt.WindowTransparentForInput : 0)

    property string tool: "pen"            // pen | marker | eraser
    property color ink: "#FF3B30"
    property real thickness: 4
    property bool passThrough: false
    property var strokes: []               // finished strokes, oldest first
    readonly property bool demo: backend.demo()

    readonly property var palette: ["#FF3B30", "#0A84FF", "#30D158", "#FFD60A", "#F4FCFF", "#080B10"]
    readonly property var sizes: [3, 6, 12]

    function addStroke(stroke) {
        var list = strokes.slice()
        list.push(stroke)
        strokes = list
        surface.requestPaint()
    }
    function undo() {
        if (strokes.length === 0) return
        var list = strokes.slice()
        list.pop()
        strokes = list
        surface.requestPaint()
    }
    function clearAll() {
        strokes = []
        surface.requestPaint()
    }
    // Take away every stroke that passes close to the point.
    function eraseAt(px, py) {
        var reach = 18
        var kept = []
        for (var i = 0; i < strokes.length; i++) {
            var hit = false
            var pts = strokes[i].points
            for (var j = 0; j < pts.length && !hit; j++) {
                var dx = pts[j].x - px, dy = pts[j].y - py
                hit = dx * dx + dy * dy < reach * reach
            }
            if (!hit) kept.push(strokes[i])
        }
        if (kept.length !== strokes.length) {
            strokes = kept
            surface.requestPaint()
        }
    }

    Component.onCompleted: {
        if (demo) {
            // For checking the drawing without a pointer: a few strokes.
            var wave = []
            for (var i = 0; i <= 60; i++) wave.push({ x: 300 + i * 12, y: 300 + Math.sin(i / 5) * 60 })
            addStroke({ color: "#FF3B30", width: 6, marker: false, points: wave })
            var line = []
            for (var k = 0; k <= 30; k++) line.push({ x: 320 + k * 20, y: 460 })
            addStroke({ color: "#FFD60A", width: 26, marker: true, points: line })
        }
    }

    // The stroke being drawn right now.
    QtObject {
        id: live
        property var points: []
        property color color: board.ink
        property real width: board.thickness
        property bool marker: false
    }

    Canvas {
        id: surface
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            var all = board.strokes.concat(live.points.length > 0 ? [live] : [])
            for (var i = 0; i < all.length; i++) {
                var s = all[i]
                if (s.points.length === 0) continue
                ctx.beginPath()
                ctx.strokeStyle = "" + s.color
                ctx.globalAlpha = s.marker ? 0.38 : 1
                ctx.lineWidth = s.width
                ctx.moveTo(s.points[0].x, s.points[0].y)
                if (s.points.length === 1) ctx.lineTo(s.points[0].x + 0.1, s.points[0].y)
                for (var j = 1; j < s.points.length; j++) ctx.lineTo(s.points[j].x, s.points[j].y)
                ctx.stroke()
            }
            ctx.globalAlpha = 1
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: !board.passThrough
        acceptedButtons: Qt.LeftButton
        cursorShape: board.tool === "eraser" ? Qt.PointingHandCursor : Qt.CrossCursor

        onPressed: function(mouse) {
            if (board.tool === "eraser") { board.eraseAt(mouse.x, mouse.y); return }
            live.color = board.ink
            live.marker = board.tool === "marker"
            live.width = live.marker ? board.thickness * 4 : board.thickness
            live.points = [{ x: mouse.x, y: mouse.y }]
            surface.requestPaint()
        }
        onPositionChanged: function(mouse) {
            if (board.tool === "eraser") { board.eraseAt(mouse.x, mouse.y); return }
            if (live.points.length === 0) return
            live.points.push({ x: mouse.x, y: mouse.y })
            surface.requestPaint()
        }
        onReleased: {
            if (board.tool !== "eraser" && live.points.length > 0) {
                board.addStroke({ color: "" + live.color, width: live.width, marker: live.marker, points: live.points })
            }
            live.points = []
        }
    }

    // --- the toolbar -------------------------------------------------------------
    Window {
        id: bar
        width: row.implicitWidth + 24
        height: 64
        x: (Screen.width - width) / 2
        y: Screen.height - height - 24
        visible: true
        color: "transparent"
        title: backend.tr("Screen pen")
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

        Rectangle {
            anchors.fill: parent
            radius: 14
            color: Theme.raised
            border.color: Theme.mid
            border.width: 1

            // Dragging the empty parts moves the whole bar.
            DragHandler {
                target: null
                onActiveChanged: if (active) bar.startSystemMove()
            }

            RowLayout {
                id: row
                anchors.centerIn: parent
                spacing: 8

                Repeater {
                    model: [["pen", backend.tr("Pen")], ["marker", backend.tr("Marker")], ["eraser", backend.tr("Eraser")]]
                    delegate: OButton {
                        required property var modelData
                        text: modelData[1]
                        primary: board.tool === modelData[0]
                        onClicked: { board.tool = modelData[0]; board.passThrough = false }
                    }
                }

                Rectangle { width: 1; height: 32; color: Theme.far }

                Repeater {
                    model: board.palette
                    delegate: Rectangle {
                        required property string modelData
                        width: 34; height: 34; radius: 17
                        color: modelData
                        border.width: board.ink == modelData ? 3 : 1
                        border.color: board.ink == modelData ? Theme.cyan : Theme.far
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                board.ink = parent.modelData
                                if (board.tool === "eraser") board.tool = "pen"
                                board.passThrough = false
                            }
                        }
                    }
                }

                Rectangle { width: 1; height: 32; color: Theme.far }

                Repeater {
                    model: board.sizes
                    delegate: Rectangle {
                        required property real modelData
                        width: 34; height: 34; radius: 8
                        color: board.thickness === modelData ? Theme.control : "transparent"
                        border.width: 1
                        border.color: board.thickness === modelData ? Theme.cyan : Theme.far
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.modelData + 4; height: width; radius: width / 2
                            color: Theme.ice
                        }
                        MouseArea { anchors.fill: parent; onClicked: board.thickness = parent.modelData }
                    }
                }

                Rectangle { width: 1; height: 32; color: Theme.far }

                OButton { text: backend.tr("Undo"); onClicked: board.undo() }
                OButton { text: backend.tr("Clear"); onClicked: board.clearAll() }
                OButton {
                    text: board.passThrough ? backend.tr("Draw") : backend.tr("Use screen")
                    onClicked: board.passThrough = !board.passThrough
                }
                OButton { text: backend.tr("Close"); onClicked: Qt.quit() }
            }
        }
    }
}
