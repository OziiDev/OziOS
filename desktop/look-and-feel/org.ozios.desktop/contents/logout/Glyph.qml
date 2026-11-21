import QtQuick

// A line drawing for the logout screen's tiles, the same on every icon theme:
// power, restart, sleep (a moon), hibernate (a snowflake), lock and log out (a door).
Canvas {
    id: glyph
    property string name: "power"
    property color color: "#F4FCFF"
    implicitWidth: 44
    implicitHeight: 44

    onNameChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        const c = getContext("2d")
        c.reset()
        const s = Math.min(width, height)
        const x = width / 2, y = height / 2, r = s * 0.36
        c.strokeStyle = glyph.color
        c.fillStyle = glyph.color
        c.lineWidth = Math.max(2, s * 0.075)
        c.lineCap = "round"
        c.lineJoin = "round"
        const line = (x1, y1, x2, y2) => { c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2); c.stroke() }

        switch (glyph.name) {
        case "power":
            c.beginPath()
            c.arc(x, y + s * 0.03, r, -Math.PI / 2 + 0.75, -Math.PI / 2 - 0.75 + 2 * Math.PI)
            c.stroke()
            line(x, y - r - s * 0.06, x, y - s * 0.02)
            break
        case "restart": {
            const end = -Math.PI / 2 - 0.7 + 2 * Math.PI
            c.beginPath()
            c.arc(x, y, r, -Math.PI / 2 + 0.2, end)
            c.stroke()
            // a filled head where the circle ends, pointing the way it runs
            const ex = x + r * Math.cos(end), ey = y + r * Math.sin(end)
            const tx = -Math.sin(end), ty = Math.cos(end)
            const nx = Math.cos(end), ny = Math.sin(end)
            const t = s * 0.2
            c.beginPath()
            c.moveTo(ex + tx * t * 0.9, ey + ty * t * 0.9)
            c.lineTo(ex + nx * t * 0.62 - tx * t * 0.15, ey + ny * t * 0.62 - ty * t * 0.15)
            c.lineTo(ex - nx * t * 0.62 - tx * t * 0.15, ey - ny * t * 0.62 - ty * t * 0.15)
            c.closePath()
            c.fill()
            break
        }
        case "sleep":
            c.beginPath()
            c.arc(x, y, r * 1.02, 0, 2 * Math.PI)
            c.fill()
            c.globalCompositeOperation = "destination-out"
            c.beginPath()
            c.arc(x + r * 0.55, y - r * 0.42, r * 0.86, 0, 2 * Math.PI)
            c.fill()
            c.globalCompositeOperation = "source-over"
            break
        case "hibernate":
            for (let i = 0; i < 3; i++) {
                const a = i * Math.PI / 3 + Math.PI / 2
                const dx = Math.cos(a) * r * 1.1, dy = Math.sin(a) * r * 1.1
                line(x - dx, y - dy, x + dx, y + dy)
                for (const end of [1, -1]) {
                    const px = x + end * dx * 0.62, py = y + end * dy * 0.62
                    const qx = Math.cos(a) * end * r * 0.3, qy = Math.sin(a) * end * r * 0.3
                    const nx = -Math.sin(a) * r * 0.26, ny = Math.cos(a) * r * 0.26
                    c.beginPath()
                    c.moveTo(px + nx + qx, py + ny + qy)
                    c.lineTo(px, py)
                    c.lineTo(px - nx + qx, py - ny + qy)
                    c.stroke()
                }
            }
            break
        case "lock": {
            const w = r * 1.55, h = r * 1.2, top = y - h * 0.1
            c.beginPath()
            c.arc(x, top, w * 0.32, Math.PI, 0)
            c.lineTo(x + w * 0.32, top + s * 0.02)
            c.moveTo(x - w * 0.32, top)
            c.lineTo(x - w * 0.32, top + s * 0.02)
            c.stroke()
            c.beginPath()
            c.roundedRect(x - w / 2, top, w, h, s * 0.08, s * 0.08)
            c.fill()
            c.globalCompositeOperation = "destination-out"
            c.beginPath()
            c.arc(x, top + h * 0.45, s * 0.055, 0, 2 * Math.PI)
            c.fill()
            c.globalCompositeOperation = "source-over"
            break
        }
        case "logout": {
            const d = r * 1.05
            // the door, open on the right
            c.beginPath()
            c.moveTo(x + d * 0.15, y - d * 0.6)
            c.lineTo(x + d * 0.15, y - d)
            c.lineTo(x - d, y - d)
            c.lineTo(x - d, y + d)
            c.lineTo(x + d * 0.15, y + d)
            c.lineTo(x + d * 0.15, y + d * 0.6)
            c.stroke()
            // and the way out
            line(x - d * 0.4, y, x + d * 1.05, y)
            c.beginPath()
            c.moveTo(x + d * 0.65, y - d * 0.4)
            c.lineTo(x + d * 1.05, y)
            c.lineTo(x + d * 0.65, y + d * 0.4)
            c.stroke()
            break
        }
        }
    }
}
