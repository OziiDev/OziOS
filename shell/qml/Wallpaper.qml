import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The OziOS wallpaper on the background layer. "tesseract": ink, a breathing
// glow in the theme's two colours and the turning tesseract, one 25 fps clock
// driving it all. Anything else is a picture, cross-faded when it changes.
Window {
    id: win
    property var shell
    readonly property var c: shell.c

    visible: true
    color: c.ink
    LS.Window.scope: "ozi-wallpaper"
    LS.Window.layer: LS.Window.LayerBackground
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone
    Behavior on color { ColorAnimation { duration: 600 } }

    property real clock: 0
    // It keeps moving behind windows (see-through terminals show it); only a
    // fullscreen window (a game, a video) hides it completely, and then it rests.
    readonly property bool covered: {
        const active = Shell.workspaces.find(w => w.active)
        const index = active ? active.index : 1
        return Shell.windows.some(w => !w.minimized && w.fullscreen && w.workspace === index)
    }
    readonly property string chosen: Shell.look.wallpaper || "tesseract"
    readonly property bool live: chosen === "tesseract"
    readonly property bool moving: live && win.shell.speed > 0 && !covered
    Timer {
        interval: 40; repeat: true
        running: win.moving
        onTriggered: win.clock += 0.04
    }

    // Two soft lights that drift slowly.
    Repeater {
        id: lights
        model: 2
        Rectangle {
            visible: win.live
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
        visible: win.live
        anchors.centerIn: parent
        width: Math.min(win.width, win.height) * 0.62
        height: width
        lineColor: win.c.accent
        dotColor: win.c.text
        running: win.moving
        opacity: 0.55
    }

    // A picture: the new one fades in over the old.
    property int front: 0
    function showPicture(path) {
        const next = front === 0 ? pictureB : pictureA
        next.source = path ? "file://" + path : ""
        front = front === 0 ? 1 : 0
    }
    // Decide from `chosen` itself: in this handler `live` may still hold the
    // value from before the change, which left the screen black when going
    // from the tesseract to a picture.
    onChosenChanged: showPicture(chosen === "tesseract" ? "" : chosen)
    Component.onCompleted: showPicture(chosen === "tesseract" ? "" : chosen)
    Image {
        id: pictureA
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(win.width, win.height)
        asynchronous: true
        // Shown or not is worked out on each change, not bound: a binding over
        // the picture's state looped while it loaded.
        property bool shown: false
        function sync() {
            const want = win.front === 0 && !win.live && status === Image.Ready
            if (want === shown) return
            shown = want
            fade0.to = want ? 1 : 0
            fade0.restart()
        }
        onStatusChanged: sync()
        Connections { target: win; function onFrontChanged() { pictureA.sync() } function onLiveChanged() { pictureA.sync() } }
        opacity: 0
        NumberAnimation on opacity { id: fade0; running: false; duration: win.shell.ms(500) }
    }
    Image {
        id: pictureB
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(win.width, win.height)
        asynchronous: true
        // Shown or not is worked out on each change, not bound: a binding over
        // the picture's state looped while it loaded.
        property bool shown: false
        function sync() {
            const want = win.front === 1 && !win.live && status === Image.Ready
            if (want === shown) return
            shown = want
            fade1.to = want ? 1 : 0
            fade1.restart()
        }
        onStatusChanged: sync()
        Connections { target: win; function onFrontChanged() { pictureB.sync() } function onLiveChanged() { pictureB.sync() } }
        opacity: 0
        NumberAnimation on opacity { id: fade1; running: false; duration: win.shell.ms(500) }
    }
}
