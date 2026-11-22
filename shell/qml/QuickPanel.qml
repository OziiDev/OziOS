import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Quick settings, from the right island. Sound, connection, battery, and the
// look of the whole desktop: theme, glow, corners and motion change every
// window frame live while the sliders move.
Window {
    id: panel
    property var shell
    readonly property var c: shell.c
    readonly property var look: Shell.look

    visible: false
    color: "transparent"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityOnDemand

    property bool open: false
    function toggle() { open ? close() : show() }
    function show() { Shell.refreshStatus(); visible = true; open = true; card.forceActiveFocus() }
    function close() { open = false; hideTimer.restart() }
    Timer { id: hideTimer; interval: panel.shell.ms(200); onTriggered: if (!panel.open) panel.visible = false }

    MouseArea { anchors.fill: parent; onClicked: panel.close() }

    Rectangle {
        id: card
        focus: true
        Keys.onEscapePressed: panel.close()
        anchors { right: parent.right; top: parent.top; rightMargin: 10; topMargin: 50 }
        width: 360
        height: content.implicitHeight + 40
        radius: 24
        color: Qt.alpha(panel.c.raised, 0.97)
        border.width: 1
        border.color: Qt.alpha(panel.c.accent, 0.35)
        opacity: panel.open ? 1 : 0
        transform: Translate { y: panel.open ? 0 : -14; Behavior on y { NumberAnimation { duration: panel.shell.ms(260); easing.type: Easing.OutCubic } } }
        Behavior on opacity { NumberAnimation { duration: panel.shell.ms(180) } }
        MouseArea { anchors.fill: parent }

        Column {
            id: content
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 20 }
            spacing: 16
            readonly property var s: Shell.status

            // Connection and battery.
            Row {
                spacing: 10
                Rectangle {
                    width: 152; height: 54; radius: 16
                    color: content.s.network.kind === "none" ? panel.c.control : Qt.alpha(panel.c.accent, 0.16)
                    border.width: 1; border.color: Qt.alpha(panel.c.accent, content.s.network.kind === "none" ? 0.15 : 0.5)
                    Row {
                        anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                        spacing: 10
                        Glyph { kind: content.s.network.kind === "none" ? "offline" : content.s.network.kind; color: panel.c.text; size: 18 }
                        Column {
                            Text { text: content.s.network.kind === "wired" ? "Kablolu" : content.s.network.kind === "wifi" ? "Wi-Fi" : "Bağlı değil"; color: panel.c.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Text { text: content.s.network.name || "—"; color: panel.c.muted; font.pixelSize: 11; width: 96; elide: Text.ElideRight }
                        }
                    }
                }
                Rectangle {
                    visible: content.s.battery.present === true
                    width: 152; height: 54; radius: 16
                    color: panel.c.control
                    Row {
                        anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                        spacing: 10
                        Glyph { kind: content.s.battery.charging ? "charging" : "battery"; level: (content.s.battery.percent || 0) / 100; color: panel.c.text; size: 18 }
                        Column {
                            Text { text: (content.s.battery.percent || 0) + "%"; color: panel.c.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Text { text: content.s.battery.charging ? "Şarj oluyor" : "Pil"; color: panel.c.muted; font.pixelSize: 11 }
                        }
                    }
                }
            }

            // Sound.
            Row {
                visible: content.s.volume.available
                width: parent.width
                spacing: 12
                Rectangle {
                    width: 34; height: 34; radius: 17
                    color: content.s.volume.muted ? Qt.alpha("#FF556E", 0.2) : panel.c.control
                    Glyph { anchors.centerIn: parent; kind: content.s.volume.muted ? "muted" : "volume"; level: content.s.volume.percent / 100; color: panel.c.text }
                    MouseArea { anchors.fill: parent; onClicked: Shell.toggleMute() }
                }
                OziSlider {
                    c: panel.c
                    width: parent.width - 34 - 12 - 44
                    anchors.verticalCenter: parent.verticalCenter
                    from: 0; to: 100; stepSize: 1
                    value: content.s.volume.percent
                    onMoved: (v) => Shell.setVolume(v)
                }
                Text { width: 32; text: content.s.volume.percent + "%"; color: panel.c.muted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
            }

            // Do not disturb: only critical notifications get through.
            Rectangle {
                width: parent.width; height: 44; radius: 14
                color: Notes.quiet ? Qt.alpha(panel.c.accent, 0.16) : panel.c.control
                border.width: 1; border.color: Qt.alpha(panel.c.accent, Notes.quiet ? 0.5 : 0.12)
                Text { anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
                       text: "Rahatsız etme"; color: panel.c.text; font.pixelSize: 13 }
                Rectangle {
                    anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    width: 40; height: 22; radius: 11
                    color: Notes.quiet ? panel.c.accent : Qt.alpha(panel.c.muted, 0.35)
                    Rectangle {
                        width: 18; height: 18; radius: 9; color: panel.c.text
                        anchors.verticalCenter: parent.verticalCenter
                        x: Notes.quiet ? parent.width - width - 2 : 2
                        Behavior on x { NumberAnimation { duration: panel.shell.ms(160); easing.type: Easing.OutCubic } }
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: Notes.setQuiet(!Notes.quiet) }
            }

            Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.c.muted, 0.2) }

            // Look: a live preview of a window frame, then the controls.
            Text { text: "Görünüm"; color: panel.c.text; font.pixelSize: 15; font.weight: Font.Bold }

            Item {
                width: parent.width; height: 92
                Rectangle {
                    id: preview
                    anchors.centerIn: parent
                    width: 190; height: 70
                    radius: panel.look.corner_radius
                    color: panel.c.ink
                    border.width: 2
                    border.color: panel.c.accent
                    // The glow, as a few soft rings.
                    Repeater {
                        model: 4
                        Rectangle {
                            anchors.centerIn: parent
                            width: preview.width + (index + 1) * 6; height: preview.height + (index + 1) * 6
                            radius: preview.radius + (index + 1) * 3
                            color: "transparent"
                            border.width: 3
                            border.color: index % 2 ? panel.c.accent2 : panel.c.accent
                            opacity: panel.look.glow * 0.18 * (1 - index / 4)
                        }
                    }
                    Rectangle {
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 2 }
                        height: 20; radius: Math.max(0, parent.radius - 2)
                        color: panel.c.raised
                        Row {
                            anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                            spacing: 5
                            Repeater { model: ["#FFBE5A", "#3CE6A0", "#FF556E"]; Rectangle { width: 8; height: 8; radius: 4; color: modelData } }
                        }
                    }
                }
            }

            // Themes: each dot shows its two glow colours.
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12
                Repeater {
                    model: Shell.themes
                    Rectangle {
                        required property var modelData
                        readonly property bool chosen: modelData.id === panel.look.theme
                        width: 34; height: 34; radius: 17
                        border.width: chosen ? 3 : 1
                        border.color: chosen ? panel.c.text : Qt.alpha(panel.c.muted, 0.4)
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: modelData.accent }
                            GradientStop { position: 1.0; color: modelData.accent2 }
                        }
                        scale: themeMouse.containsMouse ? 1.15 : 1
                        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutBack } }
                        MouseArea { id: themeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Shell.setLook("theme", parent.modelData.id) }
                    }
                }
            }

            Repeater {
                model: [
                    { key: "glow", label: "Işıltı", from: 0, to: 2, step: 0.05, fmt: (v) => v === 0 ? "kapalı" : Math.round(v * 100) + "%" },
                    { key: "corner_radius", label: "Köşeler", from: 0, to: 24, step: 1, fmt: (v) => v + " px" },
                    { key: "animation_speed", label: "Hareket", from: 0, to: 2, step: 0.1, fmt: (v) => v === 0 ? "kapalı" : v.toFixed(1) + "×" },
                    { key: "lock_after_minutes", label: "Boşta kilitle", from: 0, to: 60, step: 5, fmt: (v) => v === 0 ? "hiçbir zaman" : v + " dk" },
                ]
                Column {
                    required property var modelData
                    width: content.width
                    spacing: 4
                    Row {
                        width: parent.width
                        Text { text: modelData.label; color: panel.c.text; font.pixelSize: 13; width: parent.width - valueText.width }
                        Text { id: valueText; text: modelData.fmt(panel.look[modelData.key]); color: panel.c.muted; font.pixelSize: 12 }
                    }
                    OziSlider {
                        c: panel.c
                        width: parent.width
                        from: modelData.from; to: modelData.to; stepSize: modelData.step
                        value: panel.look[modelData.key]
                        onMoved: (v) => Shell.setLook(modelData.key, v)
                    }
                }
            }
        }
    }
}
