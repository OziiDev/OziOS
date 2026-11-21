import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// The control centre at the right of the bar. No logic of its own: every tile and
// row runs an `ozi` command and shows what `ozi quick --json`, `ozi status --json`
// and `ozi theme --json` report. On top the quick settings (Wi-Fi, Bluetooth,
// night light, do not disturb, game mode, the volume); a tile the computer has no
// use for (no Wi-Fi card, say) is left out. Below them the desktop's own settings.
PlasmoidItem {
    id: root

    property var status: ({ version: "", kernel: "", effects: "full", game_mode: false, layout: "default",
                            power_profile: "unknown", windows_guest: "missing", updates: 0 })
    property var themes: []
    property var quick: ({ volume: null, muted: false, wifi: null, wifi_network: "", bluetooth: null,
                           night: null, dnd: false })

    // Plasma looks translations up in compiled catalogs that this package does not
    // ship; Turkish is the language OziOS supports, so its words are kept here.
    readonly property bool turkish: Qt.locale().name.indexOf("tr") === 0
    function tx(english, turkish) {
        let text = root.turkish ? turkish : english
        for (let i = 2; i < arguments.length; i++)
            text = text.replace("%" + (i - 1), arguments[i])
        return text
    }

    Plasmoid.icon: "ozios"
    toolTipMainText: "OziOS " + status.version
    toolTipSubText: status.game_mode ? tx("Game mode is on", "Oyun modu açık") : tx("Kernel %1", "Çekirdek %1", status.kernel)

    Plasma5Support.DataSource {
        id: shell
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            if (data["exit code"] === 0) {
                try {
                    if (source.indexOf("status --json") >= 0) root.status = JSON.parse(data["stdout"])
                    else if (source.indexOf("theme --json") >= 0) root.themes = JSON.parse(data["stdout"])
                    else if (source.indexOf("quick --json") >= 0) root.quick = JSON.parse(data["stdout"])
                } catch (e) {}
            }
            disconnectSource(source)
            if (source.indexOf("--json") < 0) refresh.restart()
        }
    }

    function run(command) { shell.connectSource(command) }
    function reload() {
        shell.connectSource("ozi status --json")
        shell.connectSource("ozi theme --json")
        // The quick settings only while they are seen: each look starts a program.
        if (root.expanded) shell.connectSource("ozi quick --json")
    }
    // A tile shows its new state at once; the next reading confirms it.
    function setQuick(name, value) {
        const next = Object.assign({}, root.quick)
        next[name] = value
        root.quick = next
        root.run("ozi quick " + name + " " + (value === true ? "on" : value === false ? "off" : value))
    }

    // A command that was just run changes the state; ask again shortly after.
    Timer { id: refresh; interval: 1200; onTriggered: root.reload() }
    Timer { interval: 60000; repeat: true; running: true; triggeredOnStart: true; onTriggered: root.reload() }
    onExpandedChanged: if (expanded) shell.connectSource("ozi quick --json")

    compactRepresentation: Kirigami.Icon {
        source: "ozios"
        active: mouse.containsMouse
        scale: mouse.containsMouse ? 1.1 : 1
        Behavior on scale { SpringAnimation { spring: 5; damping: 0.3; epsilon: 0.002 } }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.expanded = !root.expanded
        }
    }

    // A quick setting: a rounded tile, filled with the accent colours while it is on.
    component Tile: MouseArea {
        id: tile
        property string icon
        property string title
        property string detail
        property bool on: false
        // An inline component does not see the ids around it, so it has its own colours.
        readonly property color accent: Kirigami.Theme.highlightColor
        readonly property color accent2: {
            const hue = Math.max(0, accent.hsvHue) * 360
            const d = ((270 - hue + 540) % 360) - 180
            const shift = Math.abs(d) < 20 ? 40 : Math.sign(d) * Math.min(Math.abs(d), 70)
            return Qt.hsva((((hue + shift) % 360) + 360) % 360 / 360, accent.hsvSaturation, accent.hsvValue, 1)
        }

        Layout.fillWidth: true
        Layout.preferredHeight: Math.round(Kirigami.Units.gridUnit * 2.9)
        hoverEnabled: true

        Rectangle {
            anchors.fill: parent
            radius: Kirigami.Units.smallSpacing * 3
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b,
                           tile.containsMouse ? 0.12 : 0.07)
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                opacity: tile.on ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration } }
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: tile.accent }
                    GradientStop { position: 1; color: tile.accent2 }
                }
            }
            scale: tile.pressed ? 0.97 : 1
            Behavior on scale { NumberAnimation { duration: 90 } }
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Kirigami.Units.largeSpacing
            anchors.rightMargin: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.largeSpacing
            Kirigami.Icon {
                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                Layout.preferredHeight: Layout.preferredWidth
                source: tile.icon
                isMask: true
                color: tile.on ? Qt.rgba(0, 0, 0, 0.8) : Kirigami.Theme.textColor
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: tile.title
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    color: tile.on ? Qt.rgba(0, 0, 0, 0.85) : Kirigami.Theme.textColor
                }
                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: tile.detail
                    elide: Text.ElideRight
                    font.pixelSize: Math.round(Kirigami.Theme.defaultFont.pixelSize * 0.9)
                    color: tile.on ? Qt.rgba(0, 0, 0, 0.65) : Kirigami.Theme.textColor
                    opacity: tile.on ? 1 : 0.6
                }
            }
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 20
        Layout.minimumHeight: implicitHeight
        spacing: Kirigami.Units.smallSpacing * 2

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: Kirigami.Units.smallSpacing * 2
            columnSpacing: Kirigami.Units.smallSpacing * 2

            Tile {
                objectName: "tile-wifi"
                visible: root.quick.wifi !== null && root.quick.wifi !== undefined
                icon: root.quick.wifi ? "network-wireless" : "network-wireless-disconnected"
                title: "Wi-Fi"
                detail: root.quick.wifi ? (root.quick.wifi_network || root.tx("On", "Açık")) : root.tx("Off", "Kapalı")
                on: !!root.quick.wifi
                onClicked: root.setQuick("wifi", !root.quick.wifi)
            }
            Tile {
                objectName: "tile-bluetooth"
                visible: root.quick.bluetooth !== null && root.quick.bluetooth !== undefined
                icon: root.quick.bluetooth ? "network-bluetooth" : "network-bluetooth-inactive"
                title: "Bluetooth"
                detail: root.quick.bluetooth ? root.tx("On", "Açık") : root.tx("Off", "Kapalı")
                on: !!root.quick.bluetooth
                onClicked: root.setQuick("bluetooth", !root.quick.bluetooth)
            }
            Tile {
                objectName: "tile-night"
                visible: root.quick.night !== null && root.quick.night !== undefined
                icon: "redshift-status-on"
                title: root.tx("Night light", "Gece ışığı")
                detail: root.quick.night ? root.tx("Warm screen", "Sıcak ekran") : root.tx("Off", "Kapalı")
                on: !!root.quick.night
                onClicked: root.setQuick("night", !root.quick.night)
            }
            Tile {
                objectName: "tile-dnd"
                icon: root.quick.dnd ? "notifications-disabled" : "notifications"
                title: root.tx("Do not disturb", "Rahatsız etme")
                detail: root.quick.dnd ? root.tx("Notifications wait", "Bildirimler bekler") : root.tx("Off", "Kapalı")
                on: !!root.quick.dnd
                onClicked: root.setQuick("dnd", !root.quick.dnd)
            }
            Tile {
                objectName: "tile-game"
                icon: "input-gaming"
                title: root.tx("Game mode", "Oyun modu")
                detail: root.status.game_mode ? root.tx("Full speed", "Tam güç") : root.tx("Off", "Kapalı")
                on: !!root.status.game_mode
                onClicked: {
                    const next = Object.assign({}, root.status)
                    next.game_mode = !root.status.game_mode
                    root.status = next
                    root.run("ozi mode game " + (next.game_mode ? "on" : "off"))
                }
            }
        }

        // The volume of the default output; the icon mutes. A drag sends the level at
        // most every 120 ms, so the sound server is not flooded.
        RowLayout {
            objectName: "volumeRow"
            Layout.fillWidth: true
            visible: root.quick.volume !== null && root.quick.volume !== undefined
            spacing: Kirigami.Units.smallSpacing

            PlasmaComponents.ToolButton {
                objectName: "mute"
                icon.name: root.quick.muted || root.quick.volume === 0 ? "audio-volume-muted"
                         : root.quick.volume < 34 ? "audio-volume-low"
                         : root.quick.volume < 67 ? "audio-volume-medium" : "audio-volume-high"
                text: root.quick.muted ? root.tx("Sound on", "Sesi aç") : root.tx("Mute", "Sessiz")
                display: PlasmaComponents.ToolButton.IconOnly
                onClicked: {
                    const next = Object.assign({}, root.quick)
                    next.muted = !root.quick.muted
                    root.quick = next
                    root.run("ozi quick mute " + (next.muted ? "on" : "off"))
                }
            }
            PlasmaComponents.Slider {
                id: volume
                objectName: "volume"
                Layout.fillWidth: true
                from: 0
                to: 100
                stepSize: 1
                value: root.quick.volume || 0
                opacity: root.quick.muted ? 0.5 : 1
                onMoved: send.restart()
                Timer {
                    id: send
                    interval: 120
                    onTriggered: root.run("ozi quick volume " + Math.round(volume.value))
                }
                Connections {
                    target: root
                    function onQuickChanged() {
                        if (!volume.pressed && root.quick.volume !== null && root.quick.volume !== undefined)
                            volume.value = Math.min(100, root.quick.volume)
                    }
                }
            }
            PlasmaComponents.Label {
                Layout.minimumWidth: Kirigami.Units.gridUnit * 2.2
                horizontalAlignment: Text.AlignRight
                text: Math.round(volume.value) + "%"
                opacity: 0.75
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        // The colours of the whole desktop: one swatch per theme.
        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label { text: root.tx("Theme", "Tema"); Layout.fillWidth: true }
            Repeater {
                model: root.themes
                delegate: MouseArea {
                    id: swatch
                    required property var modelData
                    objectName: "theme-" + modelData.id
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 1.4
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 1.4
                    hoverEnabled: true
                    onClicked: root.run("ozi theme " + modelData.id)

                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        mainText: swatch.modelData.name
                    }
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: swatch.modelData.background
                        border.width: swatch.modelData.current ? 2 : 1
                        border.color: swatch.modelData.current ? Kirigami.Theme.textColor : Qt.rgba(1, 1, 1, 0.2)
                        scale: swatch.containsMouse ? 1.12 : 1
                        Behavior on scale { SpringAnimation { spring: 5; damping: 0.3; epsilon: 0.002 } }
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.5
                            height: width
                            radius: width / 2
                            color: swatch.modelData.accent
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label { text: root.tx("Effects", "Efektler"); Layout.fillWidth: true }
            Repeater {
                model: [["full", root.tx("Full", "Tam")], ["light", root.tx("Light", "Hafif")], ["off", root.tx("Off", "Kapalı")]]
                delegate: PlasmaComponents.ToolButton {
                    required property var modelData
                    text: modelData[1]
                    checkable: true
                    checked: root.status.effects === modelData[0]
                    onClicked: root.run("ozi effects " + modelData[0])
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label { text: root.tx("Layout", "Düzen"); Layout.fillWidth: true }
            Repeater {
                model: [["default", root.tx("Default", "Varsayılan")], ["deck", root.tx("Deck", "Deck")], ["classic", root.tx("Classic", "Klasik")]]
                delegate: PlasmaComponents.ToolButton {
                    required property var modelData
                    text: modelData[1]
                    checkable: true
                    checked: root.status.layout === modelData[0]
                    // The panel holding this popup is replaced, so the command must outlive it.
                    onClicked: root.run("setsid -f ozi layout " + modelData[0])
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: root.status.windows_guest === "missing" ? root.tx("Windows guest: not set up", "Windows misafiri: kurulmadı")
                                                              : root.tx("Windows guest: %1", "Windows misafiri: %1", root.status.windows_guest)
            }
            PlasmaComponents.Button {
                text: root.status.windows_guest === "missing" ? root.tx("Set up", "Kur") : root.tx("Open", "Aç")
                onClicked: root.run(root.status.windows_guest === "missing" ? "ozi-winsetup --gui" : "virsh -c qemu:///system start ozi-win; virt-viewer -c qemu:///system ozi-win")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: root.status.updates > 0 ? root.tx("%1 updates waiting", "%1 güncelleme bekliyor", root.status.updates)
                                              : root.tx("Up to date", "Güncel")
            }
            PlasmaComponents.Button {
                text: root.tx("Software", "Yazılım")
                onClicked: root.run("ozi-store")
            }
        }

        Kirigami.Separator { Layout.fillWidth: true }

        PlasmaComponents.Label {
            Layout.fillWidth: true
            text: "OziOS " + root.status.version + "  ·  " + root.tx("Kernel %1", "Çekirdek %1", root.status.kernel)
            opacity: 0.55
            elide: Text.ElideRight
            font.pixelSize: Math.round(Kirigami.Theme.defaultFont.pixelSize * 0.9)
        }
    }
}
