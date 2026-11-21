import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager

// The desktops as a row of lights, as in a tiling desktop's bar. The desktop in use
// is a wide pill in the accent colours with its number; desktops that hold windows
// are filled dots, empty ones are rings. Click one to go there, scroll to step.
// The pill stretches over to the new desktop with a little spring.
PlasmoidItem {
    id: root

    preferredRepresentation: fullRepresentation
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    readonly property bool animate: Kirigami.Units.longDuration > 1
    readonly property color accent: Kirigami.Theme.highlightColor
    // The accent's partner, as in the window frames' glow: up to 70° toward violet, the
    // short way round (cyan turns blue, orange pink, green blue; a violet turns magenta).
    readonly property color accent2: {
        const hue = Math.max(0, accent.hsvHue) * 360
        const d = ((270 - hue + 540) % 360) - 180
        const shift = Math.abs(d) < 20 ? 40 : Math.sign(d) * Math.min(Math.abs(d), 70)
        return Qt.hsva((((hue + shift) % 360) + 360) % 360 / 360, accent.hsvSaturation, accent.hsvValue, 1)
    }
    readonly property color ink: Kirigami.Theme.textColor
    readonly property real dot: Math.max(7, Math.round(Kirigami.Units.gridUnit * 0.42))

    property var busy: ({})

    TaskManager.VirtualDesktopInfo { id: desktops }

    TaskManager.TasksModel {
        id: tasks
        filterByVirtualDesktop: false
        groupMode: TaskManager.TasksModel.GroupDisabled
        onCountChanged: recount.restart()
        onDataChanged: recount.restart()
    }

    // Which desktops hold a window; worked out a moment after the windows change.
    Timer {
        id: recount
        interval: 150
        onTriggered: {
            const out = {}
            for (let i = 0; i < tasks.count; ++i) {
                const index = tasks.makeModelIndex(i)
                if (!tasks.data(index, TaskManager.AbstractTasksModel.IsWindow))
                    continue
                const on = tasks.data(index, TaskManager.AbstractTasksModel.VirtualDesktops) || []
                for (let j = 0; j < on.length; ++j)
                    out[on[j]] = true
            }
            root.busy = out
        }
    }
    Component.onCompleted: recount.start()

    function step(by) {
        const ids = desktops.desktopIds
        if (!ids || ids.length < 2)
            return
        const at = ids.indexOf(desktops.currentDesktop)
        desktops.requestActivate(ids[(at + by + ids.length) % ids.length])
    }

    fullRepresentation: MouseArea {
        Layout.minimumWidth: row.implicitWidth + Kirigami.Units.smallSpacing * 2
        Layout.preferredWidth: Layout.minimumWidth
        Layout.fillHeight: true
        acceptedButtons: Qt.NoButton
        onWheel: function(wheel) {
            const delta = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y : -wheel.angleDelta.x
            root.step(delta < 0 ? 1 : -1)
        }

        Row {
            id: row
            anchors.centerIn: parent
            spacing: Math.round(root.dot * 0.55)

            Repeater {
                model: desktops.desktopIds

                delegate: Item {
                    id: light
                    required property var modelData
                    required property int index
                    readonly property bool current: modelData === desktops.currentDesktop
                    readonly property bool occupied: root.busy[modelData] === true

                    width: shape.width
                    height: root.dot * 2.2

                    // Width and height each head for their own end value: a height that
                    // followed the springing width would chase it and lag behind.
                    readonly property real small: hover.hovered ? root.dot * 1.35 : root.dot

                    Rectangle {
                        id: shape
                        anchors.centerIn: parent
                        width: light.current ? root.dot * 3.1 : light.small
                        height: light.current ? Math.round(root.dot * 1.6) : light.small
                        radius: Math.min(width, height) / 2
                        gradient: light.current ? pill : null
                        color: light.occupied ? Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.72) : "transparent"
                        border.width: light.current || light.occupied ? 0 : Math.max(1, root.dot * 0.2)
                        border.color: Qt.rgba(root.ink.r, root.ink.g, root.ink.b, 0.5)

                        Behavior on width {
                            enabled: root.animate
                            SpringAnimation { spring: 5.5; damping: 0.42; epsilon: 0.25 }
                        }
                        Behavior on height {
                            enabled: root.animate
                            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
                        }

                        Gradient {
                            id: pill
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: root.accent }
                            GradientStop { position: 1; color: root.accent2 }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: light.current && shape.width > root.dot * 2.4
                            text: light.index + 1
                            color: Qt.rgba(0, 0, 0, 0.72)
                            font.pixelSize: Math.round(shape.height * 0.72)
                            font.weight: Font.Bold
                        }
                    }

                    HoverHandler { id: hover }
                    TapHandler {
                        onTapped: desktops.requestActivate(light.modelData)
                    }
                }
            }
        }
    }
}
