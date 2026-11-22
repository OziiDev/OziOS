import QtQuick

// The shell's own line icons, so they look the same with any icon theme.
// Drawn once per change on a small canvas.
Canvas {
    id: glyph
    property string kind: "dots"
    property real level: 1          // volume or battery, 0..1
    property color color: "white"
    property real size: 16

    width: size; height: size
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    onKindChanged: requestPaint()
    onLevelChanged: requestPaint()
    onColorChanged: requestPaint()

    onPaint: {
        const g = getContext("2d")
        const s = size
        g.reset()
        g.strokeStyle = color
        g.fillStyle = color
        g.lineWidth = Math.max(1.4, s / 11)
        g.lineCap = "round"
        g.lineJoin = "round"
        const arc = (x, y, r, a0, a1) => { g.beginPath(); g.arc(x, y, r, a0, a1); g.stroke() }
        const line = (pts) => { g.beginPath(); g.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) g.lineTo(pts[i], pts[i + 1]); g.stroke() }
        switch (kind) {
        case "wifi":
            for (let i = 1; i <= 3; i++) arc(s / 2, s * 0.86, s * 0.24 * i, Math.PI * 1.25, Math.PI * 1.75)
            g.beginPath(); g.arc(s / 2, s * 0.84, s * 0.07, 0, Math.PI * 2); g.fill()
            break
        case "wired":
            g.strokeRect(s * 0.3, s * 0.2, s * 0.4, s * 0.35)
            line([s / 2, s * 0.55, s / 2, s * 0.85])
            line([s * 0.42, s * 0.2, s * 0.42, s * 0.08]); line([s * 0.58, s * 0.2, s * 0.58, s * 0.08])
            break
        case "offline":
            arc(s / 2, s * 0.86, s * 0.48, Math.PI * 1.25, Math.PI * 1.75)
            line([s * 0.2, s * 0.2, s * 0.8, s * 0.8])
            break
        case "volume":
        case "muted":
            line([s * 0.12, s * 0.38, s * 0.3, s * 0.38, s * 0.52, s * 0.16, s * 0.52, s * 0.84, s * 0.3, s * 0.62, s * 0.12, s * 0.62, s * 0.12, s * 0.38])
            if (kind === "muted") {
                line([s * 0.66, s * 0.36, s * 0.9, s * 0.64]); line([s * 0.9, s * 0.36, s * 0.66, s * 0.64])
            } else {
                if (level > 0.01) arc(s * 0.52, s / 2, s * 0.18, -Math.PI / 4, Math.PI / 4)
                if (level > 0.5) arc(s * 0.52, s / 2, s * 0.34, -Math.PI / 4, Math.PI / 4)
            }
            break
        case "battery":
        case "charging":
            g.strokeRect(s * 0.06, s * 0.28, s * 0.78, s * 0.44)
            g.fillRect(s * 0.86, s * 0.4, s * 0.08, s * 0.2)
            g.fillRect(s * 0.13, s * 0.35, s * 0.64 * Math.max(0.05, Math.min(1, level)), s * 0.3)
            if (kind === "charging") {
                g.fillStyle = "black"
                g.beginPath(); g.moveTo(s * 0.5, s * 0.3); g.lineTo(s * 0.36, s * 0.52); g.lineTo(s * 0.48, s * 0.52)
                g.lineTo(s * 0.42, s * 0.7); g.lineTo(s * 0.6, s * 0.46); g.lineTo(s * 0.48, s * 0.46); g.closePath(); g.fill()
            }
            break
        case "power":
            arc(s / 2, s * 0.55, s * 0.32, -Math.PI * 0.3, Math.PI * 1.3)
            line([s / 2, s * 0.12, s / 2, s * 0.5])
            break
        case "reboot":
            arc(s / 2, s / 2, s * 0.32, -Math.PI * 0.4, Math.PI * 1.5)
            line([s * 0.62, s * 0.08, s * 0.62, s * 0.22, s * 0.76, s * 0.22])
            break
        case "logout":
            line([s * 0.45, s * 0.15, s * 0.15, s * 0.15, s * 0.15, s * 0.85, s * 0.45, s * 0.85])
            line([s * 0.4, s / 2, s * 0.88, s / 2]); line([s * 0.72, s * 0.34, s * 0.88, s / 2, s * 0.72, s * 0.66])
            break
        case "suspend":
            g.beginPath(); g.arc(s / 2, s / 2, s * 0.34, Math.PI * 0.3, Math.PI * 1.7); g.arc(s * 0.62, s * 0.42, s * 0.26, Math.PI * 1.55, Math.PI * 0.45, true); g.stroke()
            break
        case "lock":
            g.strokeRect(s * 0.22, s * 0.45, s * 0.56, s * 0.42)
            arc(s / 2, s * 0.45, s * 0.18, Math.PI, Math.PI * 2)
            line([s * 0.32, s * 0.45, s * 0.32, s * 0.4]); line([s * 0.68, s * 0.45, s * 0.68, s * 0.4])
            break
        case "bluetooth":
            line([s * 0.3, s * 0.3, s * 0.7, s * 0.68, s * 0.5, s * 0.86, s * 0.5, s * 0.14, s * 0.7, s * 0.32, s * 0.3, s * 0.7])
            break
        case "airplane":
            g.beginPath()
            g.moveTo(s * 0.5, s * 0.08); g.lineTo(s * 0.56, s * 0.42); g.lineTo(s * 0.92, s * 0.6); g.lineTo(s * 0.92, s * 0.68)
            g.lineTo(s * 0.56, s * 0.58); g.lineTo(s * 0.56, s * 0.8); g.lineTo(s * 0.66, s * 0.9); g.lineTo(s * 0.34, s * 0.9)
            g.lineTo(s * 0.44, s * 0.8); g.lineTo(s * 0.44, s * 0.58); g.lineTo(s * 0.08, s * 0.68); g.lineTo(s * 0.08, s * 0.6)
            g.lineTo(s * 0.44, s * 0.42); g.closePath(); g.fill()
            break
        case "moon":
            g.beginPath(); g.arc(s * 0.48, s * 0.52, s * 0.34, 0, Math.PI * 2); g.fill()
            g.globalCompositeOperation = "destination-out"
            g.beginPath(); g.arc(s * 0.66, s * 0.36, s * 0.3, 0, Math.PI * 2); g.fill()
            g.globalCompositeOperation = "source-over"
            break
        case "bolt":
            g.beginPath(); g.moveTo(s * 0.58, s * 0.06); g.lineTo(s * 0.2, s * 0.56); g.lineTo(s * 0.48, s * 0.56)
            g.lineTo(s * 0.4, s * 0.94); g.lineTo(s * 0.8, s * 0.42); g.lineTo(s * 0.52, s * 0.42); g.closePath(); g.fill()
            break
        case "sun":
            g.beginPath(); g.arc(s / 2, s / 2, s * 0.18, 0, Math.PI * 2); g.fill()
            for (let i = 0; i < 8; i++) {
                const a = i * Math.PI / 4
                line([s / 2 + Math.cos(a) * s * 0.3, s / 2 + Math.sin(a) * s * 0.3, s / 2 + Math.cos(a) * s * 0.42, s / 2 + Math.sin(a) * s * 0.42])
            }
            break
        case "cube":
            g.strokeRect(s * 0.12, s * 0.12, s * 0.76, s * 0.76)
            g.strokeRect(s * 0.32, s * 0.32, s * 0.36, s * 0.36)
            line([s * 0.12, s * 0.12, s * 0.32, s * 0.32]); line([s * 0.88, s * 0.12, s * 0.68, s * 0.32])
            line([s * 0.12, s * 0.88, s * 0.32, s * 0.68]); line([s * 0.88, s * 0.88, s * 0.68, s * 0.68])
            break
        case "mic":
            g.strokeRect(s * 0.38, s * 0.1, s * 0.24, s * 0.46)
            arc(s / 2, s * 0.46, s * 0.26, 0, Math.PI)
            line([s / 2, s * 0.72, s / 2, s * 0.9])
            line([s * 0.15, s * 0.85, s * 0.85, s * 0.15])
            break
        case "search":
            arc(s * 0.42, s * 0.42, s * 0.28, 0, Math.PI * 2)
            line([s * 0.63, s * 0.63, s * 0.88, s * 0.88])
            break
        default: // dots
            for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(s * (0.2 + 0.3 * i), s / 2, s * 0.08, 0, Math.PI * 2); g.fill() }
        }
    }
}
