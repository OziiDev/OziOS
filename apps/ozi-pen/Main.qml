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

    // pen | marker | line | arrow | box | circle | eraser | laser | spot
    property string tool: "pen"
    property color ink: "#FF3B30"
    property real thickness: 4
    property bool passThrough: false
    property var strokes: []               // finished strokes, oldest first
    property var trail: []                 // the laser pointer's recent positions
    property real pointerX: -1000
    property real pointerY: -1000
    property string note: ""
    readonly property bool demo: backend.demo()
    readonly property var shapeTools: ["line", "arrow", "box", "circle"]

    readonly property var inks: ["#FF3B30", "#0A84FF", "#30D158", "#FFD60A", "#F4FCFF", "#080B10"]
    readonly property var sizes: [3, 6, 12]

    function isShape(name) { return shapeTools.indexOf(name) >= 0 }

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

    // Points along the visible outline of a stroke, so the eraser can find shapes too.
    function outline(s) {
        var p = s.points
        if (!s.shape || p.length < 2) return p
        var a = p[0], b = p[p.length - 1], out = []
        function edge(x0, y0, x1, y1) {
            for (var i = 0; i <= 24; i++) out.push({ x: x0 + (x1 - x0) * i / 24, y: y0 + (y1 - y0) * i / 24 })
        }
        if (s.shape === "line" || s.shape === "arrow") {
            edge(a.x, a.y, b.x, b.y)
        } else if (s.shape === "box") {
            edge(a.x, a.y, b.x, a.y); edge(b.x, a.y, b.x, b.y); edge(b.x, b.y, a.x, b.y); edge(a.x, b.y, a.x, a.y)
        } else {
            var cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2, rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2
            for (var k = 0; k < 48; k++) out.push({ x: cx + rx * Math.cos(k * Math.PI / 24), y: cy + ry * Math.sin(k * Math.PI / 24) })
        }
        return out
    }
    // Take away every stroke that passes close to the point.
    function eraseAt(px, py) {
        var reach = 18
        var kept = []
        for (var i = 0; i < strokes.length; i++) {
            var hit = false
            var pts = outline(strokes[i])
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

    function drawStroke(ctx, s) {
        var p = s.points
        if (p.length === 0) return
        ctx.beginPath()
        ctx.strokeStyle = "" + s.color
        ctx.globalAlpha = s.marker ? 0.38 : 1
        ctx.lineWidth = s.width
        var a = p[0], b = p[p.length - 1]
        if (s.shape === "line" || s.shape === "arrow") {
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            if (s.shape === "arrow") {
                var angle = Math.atan2(b.y - a.y, b.x - a.x), head = 14 + s.width * 2
                ctx.moveTo(b.x, b.y)
                ctx.lineTo(b.x - head * Math.cos(angle - 0.45), b.y - head * Math.sin(angle - 0.45))
                ctx.moveTo(b.x, b.y)
                ctx.lineTo(b.x - head * Math.cos(angle + 0.45), b.y - head * Math.sin(angle + 0.45))
            }
        } else if (s.shape === "box") {
            ctx.rect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y))
        } else if (s.shape === "circle") {
            ctx.ellipse(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y))
        } else {
            ctx.moveTo(a.x, a.y)
            if (p.length === 1) ctx.lineTo(a.x + 0.1, a.y)
            for (var j = 1; j < p.length; j++) ctx.lineTo(p[j].x, p[j].y)
        }
        ctx.stroke()
    }

    function showNote(text) {
        note = text
        noteTimer.restart()
    }
    // Save the drawing, without the screen under it, as a PNG in the Pictures folder.
    function save() {
        var dir = backend.picturesDir()
        if (dir === "" || strokes.length === 0) {
            showNote(backend.tr("Nothing to save"))
            return
        }
        var path = dir + "/ozi-pen-" + Qt.formatDateTime(new Date(), "yyyyMMdd-hhmmss") + ".png"
        surface.grabToImage(function(result) {
            showNote(result.saveToFile(path) ? backend.tr("Saved") + ": " + path : backend.tr("Could not save"))
        })
    }

    Component.onCompleted: {
        if (demo) {
            // For checking the drawing without a pointer: a few strokes.
            var wave = []
            for (var i = 0; i <= 60; i++) wave.push({ x: 300 + i * 12, y: 300 + Math.sin(i / 5) * 60 })
            addStroke({ color: "#FF3B30", width: 6, marker: false, shape: "", points: wave })
            var line = []
            for (var k = 0; k <= 30; k++) line.push({ x: 320 + k * 20, y: 460 })
            addStroke({ color: "#FFD60A", width: 26, marker: true, shape: "", points: line })
            addStroke({ color: "#0A84FF", width: 5, marker: false, shape: "box", points: [{ x: 360, y: 180 }, { x: 560, y: 270 }] })
            addStroke({ color: "#30D158", width: 5, marker: false, shape: "circle", points: [{ x: 640, y: 150 }, { x: 800, y: 260 }] })
            addStroke({ color: "#F4FCFF", width: 5, marker: false, shape: "arrow", points: [{ x: 860, y: 520 }, { x: 1020, y: 380 }] })
        }
    }

    Shortcut { sequence: "Ctrl+Z"; onActivated: board.undo() }
    Shortcut { sequence: "Delete"; onActivated: board.clearAll() }
    Shortcut { sequence: "Escape"; onActivated: board.passThrough = !board.passThrough }

    // The stroke being drawn right now.
    QtObject {
        id: live
        property var points: []
        property color color: board.ink
        property real width: board.thickness
        property bool marker: false
        property string shape: ""
    }

    Canvas {
        id: surface
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            for (var i = 0; i < board.strokes.length; i++) board.drawStroke(ctx, board.strokes[i])
            if (live.points.length > 0) board.drawStroke(ctx, live)
            ctx.globalAlpha = 1
        }
    }

    // Laser pointer: a red dot with a short fading trail.
    Canvas {
        id: laser
        anchors.fill: parent
        visible: board.tool === "laser"
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var now = Date.now(), t = board.trail
            ctx.lineCap = "round"
            for (var i = 1; i < t.length; i++) {
                var age = (now - t[i].t) / 700
                if (age >= 1) continue
                ctx.strokeStyle = Qt.rgba(1, 0.1, 0.1, 0.9 * (1 - age))
                ctx.lineWidth = 10 * (1 - age) + 2
                ctx.beginPath()
                ctx.moveTo(t[i - 1].x, t[i - 1].y)
                ctx.lineTo(t[i].x, t[i].y)
                ctx.stroke()
            }
            if (t.length > 0 && now - t[t.length - 1].t < 700) {
                ctx.fillStyle = "#FF2020"
                ctx.beginPath()
                ctx.arc(t[t.length - 1].x, t[t.length - 1].y, 9, 0, Math.PI * 2)
                ctx.fill()
            }
        }
    }
    Timer {
        interval: 33
        repeat: true
        running: board.tool === "laser" && board.trail.length > 0
        onTriggered: {
            var now = Date.now(), kept = []
            for (var i = 0; i < board.trail.length; i++) if (now - board.trail[i].t < 700) kept.push(board.trail[i])
            board.trail = kept
            laser.requestPaint()
        }
    }

    // Spotlight: the screen goes dim except around the pointer.
    Canvas {
        id: dim
        anchors.fill: parent
        visible: board.tool === "spot"
        onPaint: {
            var ctx = getContext("2d")
            ctx.globalCompositeOperation = "source-over"
            ctx.clearRect(0, 0, width, height)
            ctx.fillStyle = "rgba(0, 0, 0, 0.72)"
            ctx.fillRect(0, 0, width, height)
            ctx.globalCompositeOperation = "destination-out"
            var radius = 150
            var glow = ctx.createRadialGradient(board.pointerX, board.pointerY, radius * 0.75, board.pointerX, board.pointerY, radius)
            glow.addColorStop(0, "rgba(0, 0, 0, 1)")
            glow.addColorStop(1, "rgba(0, 0, 0, 0)")
            ctx.fillStyle = glow
            ctx.fillRect(board.pointerX - radius, board.pointerY - radius, radius * 2, radius * 2)
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: !board.passThrough
        hoverEnabled: board.tool === "spot" || board.tool === "laser"
        acceptedButtons: Qt.LeftButton
        cursorShape: board.tool === "eraser" ? Qt.PointingHandCursor : Qt.CrossCursor

        function follow(mouse) {
            if (board.tool === "laser") {
                var list = board.trail.slice()
                list.push({ x: mouse.x, y: mouse.y, t: Date.now() })
                board.trail = list.slice(-80)
                laser.requestPaint()
            } else if (board.tool === "spot") {
                board.pointerX = mouse.x
                board.pointerY = mouse.y
                dim.requestPaint()
            }
        }

        onPressed: function(mouse) {
            follow(mouse)
            if (board.tool === "eraser") { board.eraseAt(mouse.x, mouse.y); return }
            if (board.tool === "laser" || board.tool === "spot") return
            live.color = board.ink
            live.marker = board.tool === "marker"
            live.shape = board.isShape(board.tool) ? board.tool : ""
            live.width = live.marker ? board.thickness * 4 : board.thickness
            live.points = [{ x: mouse.x, y: mouse.y }]
            surface.requestPaint()
        }
        onPositionChanged: function(mouse) {
            follow(mouse)
            if (board.tool === "eraser") { if (pressed) board.eraseAt(mouse.x, mouse.y); return }
            if (live.points.length === 0) return
            if (live.shape !== "") live.points = [live.points[0], { x: mouse.x, y: mouse.y }]
            else live.points.push({ x: mouse.x, y: mouse.y })
            surface.requestPaint()
        }
        onReleased: {
            var drawing = board.tool !== "eraser" && board.tool !== "laser" && board.tool !== "spot"
            if (drawing && live.points.length > 0) {
                board.addStroke({ color: "" + live.color, width: live.width, marker: live.marker, shape: live.shape, points: live.points })
            }
            live.points = []
            surface.requestPaint()
        }
    }

    // --- the toolbar -------------------------------------------------------------
    Window {
        id: bar
        width: column.implicitWidth + 24
        height: column.implicitHeight + 20
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

            ColumnLayout {
                id: column
                anchors.centerIn: parent
                spacing: 8

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 8
                    Repeater {
                        model: [["pen", backend.tr("Pen")], ["marker", backend.tr("Marker")], ["line", backend.tr("Line")],
                                ["arrow", backend.tr("Arrow")], ["box", backend.tr("Box")], ["circle", backend.tr("Circle")],
                                ["eraser", backend.tr("Eraser")], ["laser", backend.tr("Laser")], ["spot", backend.tr("Spotlight")]]
                        delegate: OButton {
                            required property var modelData
                            text: modelData[1]
                            primary: board.tool === modelData[0]
                            onClicked: { board.tool = modelData[0]; board.passThrough = false }
                        }
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 8

                    Repeater {
                        model: board.inks
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
                                    if (board.tool === "eraser" || board.tool === "laser" || board.tool === "spot") board.tool = "pen"
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
                    OButton { text: backend.tr("Save"); onClicked: board.save() }
                    OButton {
                        text: board.passThrough ? backend.tr("Draw") : backend.tr("Use screen")
                        onClicked: board.passThrough = !board.passThrough
                    }
                    OButton { text: backend.tr("Close"); onClicked: Qt.quit() }
                }

                Text {
                    visible: board.note !== ""
                    Layout.alignment: Qt.AlignHCenter
                    text: board.note
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 13
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 900
                }
            }
        }
    }

    Timer { id: noteTimer; interval: 4000; onTriggered: board.note = "" }
}
