import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The OziOS wallpaper on the background layer: ink, a breathing glow in the
// theme's two colours and the turning tesseract. One 25 fps clock drives it all.
Window {
    id: win
    property var shell
    readonly property var c: shell.c

    visible: true
    color: c.ink
    LS.Window.layer: LS.Window.LayerBackground
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone
    Behavior on color { ColorAnimation { duration: 600 } }

    property real clock: 0
    Timer {
        interval: 40; repeat: true
        running: win.shell.speed > 0
        onTriggered: win.clock += 0.04
    }

    // Two soft lights that drift slowly.
    Repeater {
        model: 2
        Rectangle {
            readonly property real phase: index * Math.PI
            width: win.width * 0.9; height: width; radius: width / 2
            x: win.width * (0.15 + 0.25 * index) + Math.cos(win.clock * 0.07 + phase) * win.width * 0.06 - width / 4
            y: win.height * (0.05 + 0.35 * index) + Math.sin(win.clock * 0.05 + phase) * win.height * 0.08 - height / 4
            opacity: 0.16 + 0.05 * Math.sin(win.clock * 0.6 + phase)
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: Qt.alpha(index === 0 ? win.c.accent : win.c.accent2, 0.55) }
                GradientStop { position: 0.6; color: Qt.alpha(index === 0 ? win.c.accent : win.c.accent2, 0.0) }
            }
        }
    }

    Tesseract {
        anchors.centerIn: parent
        width: Math.min(win.width, win.height) * 0.62
        height: width
        lineColor: win.c.accent
        dotColor: win.c.text
        running: win.shell.speed > 0
        opacity: 0.55
    }
}
