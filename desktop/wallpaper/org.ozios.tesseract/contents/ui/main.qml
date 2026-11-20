import QtQuick
import org.kde.plasma.plasmoid
import org.kde.kirigami as Kirigami

// The OziOS wallpaper: a turning tesseract in a slowly breathing glow, with a few
// motes of light drifting upward. It takes its colours from the colour scheme, so
// every OziOS theme gets its own wallpaper. All of it stops while a window covers
// the desktop, and the motion that remains runs on the GPU (animators, not timers).
WallpaperItem {
    id: root

    readonly property color ink: Kirigami.Theme.backgroundColor
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color light: Kirigami.Theme.textColor
    readonly property bool still: coverage.item ? coverage.item.covered : false

    Rectangle {
        anchors.fill: parent
        color: root.ink
        Behavior on color { ColorAnimation { duration: 600 } }
    }

    // Soft glow behind the figure. Painted once per size and colour, never per frame;
    // the breathing is an opacity change, which costs nothing.
    Canvas {
        id: glow
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const r = Math.max(width, height) * 0.55
            const g = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, r)
            const a = root.accent
            g.addColorStop(0.0, Qt.rgba(a.r, a.g, a.b, 0.16))
            g.addColorStop(0.45, Qt.rgba(a.r, a.g, a.b, 0.045))
            g.addColorStop(1.0, Qt.rgba(a.r, a.g, a.b, 0))
            ctx.fillStyle = g
            ctx.fillRect(0, 0, width, height)
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: root
            function onAccentChanged() { glow.requestPaint() }
        }

        SequentialAnimation on opacity {
            running: !root.still
            loops: Animation.Infinite
            OpacityAnimator { from: 1; to: 0.62; duration: 5200; easing.type: Easing.InOutSine }
            OpacityAnimator { from: 0.62; to: 1; duration: 5200; easing.type: Easing.InOutSine }
        }
    }

    // Motes of light that drift up through the glow.
    Repeater {
        model: 22
        Rectangle {
            id: mote
            required property int index
            // Fixed pseudo-random values per mote, so the field looks the same each start.
            readonly property real seed: Math.abs(Math.sin(index * 12.9898 + 4.1414) * 43758.5453) % 1
            readonly property real seed2: Math.abs(Math.sin(index * 78.233 + 1.7) * 24634.6345) % 1
            readonly property real size: 2 + seed2 * 3.5
            width: size
            height: size
            radius: size / 2
            color: seed > 0.7 ? root.accent : root.light
            x: seed * root.width
            y: root.height
            opacity: 0

            SequentialAnimation {
                running: !root.still && root.width > 0
                loops: Animation.Infinite
                PauseAnimation { duration: mote.seed2 * 9000 }
                ParallelAnimation {
                    YAnimator {
                        target: mote
                        from: root.height * (0.75 + mote.seed * 0.3)
                        to: root.height * (0.05 + mote.seed2 * 0.3)
                        duration: 22000 + mote.seed * 26000
                        easing.type: Easing.InOutSine
                    }
                    SequentialAnimation {
                        OpacityAnimator { target: mote; from: 0; to: 0.25 + mote.seed2 * 0.45; duration: 4000 }
                        PauseAnimation { duration: 12000 + mote.seed * 20000 }
                        OpacityAnimator { target: mote; to: 0; duration: 6000 }
                    }
                }
            }
        }
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
        running: !root.still
        lineColor: root.accent
        dotColor: root.light
    }
}
