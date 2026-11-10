import QtQuick

// A turning tesseract drawn with plain scene graph rectangles. Moving a few
// dozen rectangles costs next to nothing on the GPU; repainting a canvas
// every frame kept a CPU core busy.
Item {
    id: root

    property bool running: true
    property real speed: 0.0075          // how far the figure turns per tick
    property color lineColor: "#00E5FF"
    property color dotColor: "#F4FCFF"

    readonly property real side: Math.min(width, height)
    property real t: 0.9
    property var corners: []
    property var edges: []

    Repeater {
        id: halos
        model: 32
        Rectangle {
            transformOrigin: Item.Left
            radius: height / 2
            color: root.lineColor
            antialiasing: true
        }
    }
    Repeater {
        id: lines
        model: 32
        Rectangle {
            transformOrigin: Item.Left
            radius: height / 2
            color: root.lineColor
            antialiasing: true
        }
    }
    Repeater {
        id: dots
        model: 16
        Rectangle {
            radius: width / 2
            color: root.dotColor
            antialiasing: true
        }
    }

    function project() {
        const unit = side / 3.1
        const out = []
        for (const v of corners) {
            let x = v[0], y = v[1], z = v[2], w = v[3], c, s, k, n
            c = Math.cos(t * 0.80); s = Math.sin(t * 0.80)
            n = x * c - w * s; w = x * s + w * c; x = n
            c = Math.cos(t * 0.55); s = Math.sin(t * 0.55)
            n = y * c - z * s; z = y * s + z * c; y = n
            c = Math.cos(t * 0.25); s = Math.sin(t * 0.25)
            n = x * c - y * s; y = x * s + y * c; x = n
            k = 2.6 / (3.4 - w)
            x *= k; y *= k; z *= k
            k = 3.2 / (4.6 - z)
            const depth = Math.max(0, Math.min(1, (w + 1.5) / 3 * 0.6 + (z + 2) / 4 * 0.4))
            out.push([width / 2 + x * k * unit, height / 2 + y * k * unit, depth])
        }
        return out
    }

    function place(item, a, length, angle, thickness, opacity) {
        item.x = a[0]
        item.y = a[1] - thickness / 2
        item.width = length
        item.height = thickness
        item.rotation = angle
        item.opacity = opacity
    }

    function frame() {
        if (!corners.length || side <= 0)
            return
        const p = project()
        const scale = side / 700
        for (let i = 0; i < edges.length; i++) {
            const a = p[edges[i][0]], b = p[edges[i][1]]
            const dx = b[0] - a[0], dy = b[1] - a[1]
            const length = Math.sqrt(dx * dx + dy * dy)
            const angle = Math.atan2(dy, dx) * 180 / Math.PI
            const d = (a[2] + b[2]) / 2
            const halo = halos.itemAt(i), line = lines.itemAt(i)
            if (!halo || !line)
                return
            place(halo, a, length, angle, (6 + d * 8) * scale, 0.05 + d * 0.10)
            place(line, a, length, angle, Math.max(1, (1 + d * 2) * scale), 0.25 + d * 0.75)
        }
        for (let i = 0; i < p.length; i++) {
            const dot = dots.itemAt(i)
            if (!dot)
                return
            const size = Math.max(2, (4 + p[i][2] * 7) * scale)
            dot.width = size
            dot.height = size
            dot.x = p[i][0] - size / 2
            dot.y = p[i][1] - size / 2
            dot.opacity = 0.45 + p[i][2] * 0.55
        }
    }

    Component.onCompleted: {
        const c = []
        for (let i = 0; i < 16; i++)
            c.push([i & 8 ? 1 : -1, i & 4 ? 1 : -1, i & 2 ? 1 : -1, i & 1 ? 1 : -1])
        const e = []
        for (let a = 0; a < 16; a++)
            for (let b = a + 1; b < 16; b++) {
                const d = a ^ b
                if ((d & (d - 1)) === 0)
                    e.push([a, b])
            }
        corners = c
        edges = e
        frame()
    }
    onSideChanged: frame()

    // 20 frames a second is plenty for a turn this slow.
    Timer {
        interval: 50
        repeat: true
        running: root.running && root.visible
        onTriggered: {
            root.t += root.speed
            root.frame()
        }
    }
}
