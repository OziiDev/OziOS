import QtQuick
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    Rectangle {
        anchors.fill: parent
        color: "#080B10"
    }

    // Soft glow behind the figure. Painted once per size, never per frame.
    Canvas {
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const r = Math.max(width, height) * 0.5
            const g = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, r)
            g.addColorStop(0.0, Qt.rgba(0, 0.9, 1, 0.13))
            g.addColorStop(0.5, Qt.rgba(0, 0.9, 1, 0.03))
            g.addColorStop(1.0, Qt.rgba(0, 0.9, 1, 0))
            ctx.fillStyle = g
            ctx.fillRect(0, 0, width, height)
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Loader {
        id: coverage
        source: "Coverage.qml"
    }

    // Stops outright while a maximized or full screen window hides the desktop.
    Tesseract {
        anchors.centerIn: parent
        width: Math.round(Math.min(parent.width, parent.height) * 0.64)
        height: width
        running: !(coverage.item && coverage.item.covered)
    }
}
