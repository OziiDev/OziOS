import QtQuick
import org.kde.plasma.plasmoid
import org.kde.kirigami as Kirigami

// The OziOS wallpaper: a turning tesseract in a slowly breathing glow, with a few
// motes of light drifting upward. It takes its colours from the colour scheme, so
// every OziOS theme gets its own wallpaper.
//
// Cost: Qt Quick draws the whole desktop again for every change, so the number of
// frames is what matters. Everything here moves as a function of one clock that
// ticks 25 times a second; animators would run at the screen's rate (60 or more)
// and keep the desktop busy. The clock stops while a window covers the desktop,
// when animations are off, and in the light effects profile (`Animated` false),
// which is what a computer drawing in software gets: there each frame of a full
// screen costs a whole processor core.
WallpaperItem {
    id: root

    readonly property color ink: Kirigami.Theme.backgroundColor
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color light: Kirigami.Theme.textColor
    readonly property bool animated: root.configuration.Animated !== false && Kirigami.Units.longDuration > 1
    readonly property bool covered: coverage.item ? coverage.item.covered : false
    readonly property bool moving: animated && !covered && width > 0 && height > 0
    // Seconds of motion so far. It only advances while moving, so a covered
    // desktop picks up where it stopped instead of jumping.
    property real clock: 0

    Rectangle {
        anchors.fill: parent
        color: root.ink
        Behavior on color { ColorAnimation { duration: 600 } }
    }

    // Soft glow behind the figure, painted once per size and colour; it breathes
    // with the clock through its opacity, which costs nothing to change.
    Canvas {
        id: glow
        anchors.fill: parent
        opacity: 0.81 + 0.19 * Math.cos(root.clock * 2 * Math.PI / 10.4)
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
    }

    // Motes of light that drift up through the glow, each on its own cycle:
    // fade in, rise, fade out, rest. Fixed pseudo-random values per mote, so the
    // field looks the same each start, and the cycles start part way through so
    // the motes are spread out from the first frame.
    Repeater {
        model: 22
        Rectangle {
            id: mote
            required property int index
            readonly property real seed: Math.abs(Math.sin(index * 12.9898 + 4.1414) * 43758.5453) % 1
            readonly property real seed2: Math.abs(Math.sin(index * 78.233 + 1.7) * 24634.6345) % 1
            readonly property real size: 2 + seed2 * 3.5
            readonly property real rise: 22 + seed * 26                  // seconds from bottom to top
            readonly property real shown: Math.min(rise, 22 + seed * 20) // seconds it is lit
            readonly property real cycle: rise + 2 + seed2 * 9           // plus a rest in the dark
            readonly property real u: (root.clock + seed2 * cycle) % cycle
            readonly property real from: root.height * (0.75 + seed * 0.3)
            readonly property real to: root.height * (0.05 + seed2 * 0.3)
            readonly property real peak: 0.25 + seed2 * 0.45
            width: size
            height: size
            radius: size / 2
            color: seed > 0.7 ? root.accent : root.light
            x: seed * root.width
            y: u < rise ? from + (to - from) * (0.5 - 0.5 * Math.cos(Math.PI * u / rise)) : from
            opacity: u < 4 ? peak * u / 4
                   : u < shown - 6 ? peak
                   : u < shown ? peak * (shown - u) / 6
                   : 0
        }
    }

    Loader {
        id: coverage
        source: "Coverage.qml"
    }

    Tesseract {
        anchors.centerIn: parent
        width: Math.round(Math.min(parent.width, parent.height) * 0.64)
        height: width
        running: false                    // turned by the shared clock below
        t: 0.9 + root.clock * 0.15
        lineColor: root.accent
        dotColor: root.light
    }

    // 25 frames a second: smooth for motion this slow, and well under half the
    // frames of animators running at the screen's rate.
    Timer {
        interval: 40
        repeat: true
        running: root.moving
        onTriggered: root.clock += 0.04
    }
}
