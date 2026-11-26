import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// Quick settings, from the bar's status corner or its clock. Two pages:
//   Hızlı    Wi-Fi (with the networks), Bluetooth (with the devices), airplane
//            mode, do not disturb, power profile, tiling, sound and brightness.
//   Görünüm  theme, accent edge, corners, motion, idle lock and the wallpaper; every
//            window frame follows while the sliders move.
Window {
    id: panel
    property var shell
    readonly property var c: shell.c
    readonly property var look: Shell.look
    readonly property var s: Shell.status

    visible: false
    color: "transparent"
    // Always a real size: when Qt shows the window again it sends the size before
    // the anchors, and a 0 size without anchors is a protocol error that ends the shell.
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-quickpanel"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityOnDemand

    property bool open: false
    property string page: "quick"      // quick | look
    property string drawer: ""         // "" | wifi | bluetooth
    function toggle() { open ? close() : show() }
    function show() { Shell.refreshStatus(); drawer = ""; visible = true; open = true; card.forceActiveFocus() }
    function close() { open = false; hideTimer.restart() }
    Timer { id: hideTimer; interval: panel.shell.ms(200); onTriggered: if (!panel.open) panel.visible = false }

    MouseArea { anchors.fill: parent; onClicked: panel.close() }

    Rectangle {
        id: card
        focus: true
        Keys.onEscapePressed: panel.drawer ? panel.drawer = "" : panel.close()
        anchors { right: parent.right; top: parent.top; rightMargin: 8; topMargin: 42 }
        width: 360
        height: Math.min(panel.height - 56, flick.contentHeight + 74)
        radius: 16
        color: panel.c.raised
        border.width: 1
        border.color: Qt.alpha(panel.c.text, 0.08)
        clip: true
        opacity: panel.open ? 1 : 0
        transform: Translate { y: panel.open ? 0 : -8; Behavior on y { NumberAnimation { duration: panel.shell.ms(180); easing.type: Easing.OutCubic } } }
        Behavior on opacity { NumberAnimation { duration: panel.shell.ms(180) } }
        Behavior on height { NumberAnimation { duration: panel.shell.ms(200); easing.type: Easing.OutCubic } }
        MouseArea { anchors.fill: parent }

        // Page switch.
        Row {
            id: tabs
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 4
            Repeater {
                model: [{ id: "quick", label: "Hızlı ayarlar" }, { id: "look", label: "Görünüm" }]
                Rectangle {
                    required property var modelData
                    readonly property bool chosen: panel.page === modelData.id
                    width: (tabs.width - 4) / 2; height: 32; radius: 8
                    color: chosen ? Qt.alpha(panel.c.text, 0.10) : "transparent"
                    Text { anchors.centerIn: parent; text: modelData.label; color: chosen ? panel.c.text : panel.c.muted; font.pixelSize: 13; font.weight: Font.DemiBold }
                    MouseArea { anchors.fill: parent; onClicked: { panel.page = parent.modelData.id; panel.drawer = "" } }
                }
            }
        }

        Flickable {
            id: flick
            anchors { left: parent.left; right: parent.right; top: tabs.bottom; bottom: parent.bottom; topMargin: 14; leftMargin: 18; rightMargin: 18; bottomMargin: 14 }
            contentHeight: (panel.page === "quick" ? quickPage.implicitHeight : lookPage.implicitHeight)
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            // ---------------------------------------------------------- quick
            Column {
                id: quickPage
                visible: panel.page === "quick"
                width: flick.width
                spacing: 12

                Grid {
                    columns: 2
                    columnSpacing: 10; rowSpacing: 10
                    readonly property real tileWidth: (quickPage.width - 10) / 2

                    Tile {
                        c: panel.c; width: parent.tileWidth
                        glyph: panel.s.wifi.wifi ? "wifi" : "offline"
                        title: "Wi-Fi"
                        subtitle: !panel.s.wifi.wifi ? "Kapalı" : (panel.s.network.kind === "wifi" ? panel.s.network.name : (panel.s.network.kind === "wired" ? "Kablolu bağlı" : "Bağlı değil"))
                        on: panel.s.wifi.wifi === true
                        more: true
                        onToggled: Shell.setWifi(!panel.s.wifi.wifi)
                        onOpened: { panel.drawer = panel.drawer === "wifi" ? "" : "wifi"; if (panel.drawer) Shell.scanNetworks() }
                    }
                    Tile {
                        c: panel.c; width: parent.tileWidth
                        visible: panel.s.bluetooth.available === true
                        glyph: "bluetooth"
                        title: "Bluetooth"
                        subtitle: !panel.s.bluetooth.powered ? "Kapalı" : (panel.s.bluetooth.devices.filter(d => d.connected).map(d => d.name)[0] || "Açık")
                        on: panel.s.bluetooth.powered === true
                        more: true
                        onToggled: Shell.setBluetooth(!panel.s.bluetooth.powered)
                        onOpened: panel.drawer = panel.drawer === "bluetooth" ? "" : "bluetooth"
                    }
                    Tile {
                        c: panel.c; width: parent.tileWidth
                        glyph: "airplane"
                        title: "Uçak modu"
                        subtitle: panel.s.airplane ? "Açık" : "Kapalı"
                        on: panel.s.airplane === true
                        onToggled: Shell.setAirplane(!panel.s.airplane)
                    }
                    Tile {
                        c: panel.c; width: parent.tileWidth
                        glyph: "moon"
                        title: "Rahatsız etme"
                        subtitle: Notes.quiet ? "Yalnız acil olanlar" : "Kapalı"
                        on: Notes.quiet
                        onToggled: Notes.setQuiet(!Notes.quiet)
                    }
                    Tile {
                        c: panel.c; width: parent.tileWidth
                        visible: panel.s.power !== ""
                        glyph: "bolt"
                        title: "Güç"
                        subtitle: ({ "power-saver": "Tasarruf", "balanced": "Dengeli", "performance": "Performans" })[panel.s.power] || ""
                        on: panel.s.power === "performance"
                        onToggled: {
                            const order = ["power-saver", "balanced", "performance"]
                            Shell.setPowerProfile(order[(order.indexOf(panel.s.power) + 1) % 3])
                        }
                    }
                    Tile {
                        readonly property var desk: Shell.workspaces.find(w => w.active) || {}
                        c: panel.c; width: parent.tileWidth
                        glyph: "tiles"
                        title: "Döşeme"
                        subtitle: desk.tiling ? "Açık" : "Kapalı"
                        on: desk.tiling === true
                        onToggled: Shell.toggleTiling()
                    }
                    Tile {
                        c: panel.c; width: parent.tileWidth
                        visible: panel.s.battery.present === true
                        glyph: panel.s.battery.charging ? "charging" : "battery"
                        level: (panel.s.battery.percent || 0) / 100
                        title: (panel.s.battery.percent || 0) + "%"
                        subtitle: panel.s.battery.charging ? "Şarj oluyor" : "Pil"
                        on: false
                    }
                }

                // Wi-Fi networks.
                Column {
                    visible: panel.drawer === "wifi"
                    width: parent.width
                    spacing: 6
                    Text { text: Shell.networks.length ? "Ağlar" : "Ağlar aranıyor…"; color: panel.c.muted; font.pixelSize: 12 }
                    Repeater {
                        model: Shell.networks
                        Rectangle {
                            id: net
                            required property var modelData
                            property bool asking: false
                            width: quickPage.width; height: asking ? 92 : 42; radius: 12
                            color: modelData.active ? Qt.alpha(panel.c.accent, 0.16) : (netMouse.containsMouse ? panel.c.control : "transparent")
                            Glyph { kind: "wifi"; color: panel.c.text; size: 15; anchors { left: parent.left; leftMargin: 12; top: parent.top; topMargin: 13 } }
                            Text {
                                anchors { left: parent.left; leftMargin: 38; top: parent.top; topMargin: 12; right: parent.right; rightMargin: 70 }
                                text: net.modelData.ssid; color: panel.c.text; font.pixelSize: 13; elide: Text.ElideRight
                            }
                            Text {
                                anchors { right: parent.right; rightMargin: 12; top: parent.top; topMargin: 13 }
                                text: (net.modelData.secure ? "Parolalı · " : "") + net.modelData.signal + "%"; color: panel.c.muted; font.pixelSize: 11
                            }
                            MouseArea {
                                id: netMouse
                                anchors { left: parent.left; right: parent.right; top: parent.top }
                                height: 42; hoverEnabled: true
                                onClicked: if (!net.modelData.active) Shell.connectWifi(net.modelData.ssid, "")
                            }
                            // Asked for a password: a field right under the network.
                            Rectangle {
                                visible: net.asking
                                anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 8 }
                                height: 38; radius: 10
                                color: Qt.alpha(panel.c.text, 0.06); border.width: 1; border.color: Qt.alpha(panel.c.accent, 0.7)
                                TextInput {
                                    id: pass
                                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                                    verticalAlignment: TextInput.AlignVCenter
                                    echoMode: TextInput.Password
                                    color: panel.c.text; font.pixelSize: 13
                                    onAccepted: { Shell.connectWifi(net.modelData.ssid, text); text = ""; net.asking = false }
                                    Text { visible: !pass.text; anchors.verticalCenter: parent.verticalCenter; text: "Parola, sonra Enter"; color: panel.c.muted; font.pixelSize: 12 }
                                }
                            }
                            Connections {
                                target: Shell
                                function onWifiResult(ssid, ok, needsPassword, message) {
                                    if (ssid === net.modelData.ssid && needsPassword) { net.asking = true; pass.forceActiveFocus() }
                                }
                            }
                        }
                    }
                }

                // Bluetooth devices.
                Column {
                    visible: panel.drawer === "bluetooth"
                    width: parent.width
                    spacing: 6
                    Text { text: panel.s.bluetooth.devices.length ? "Eşleşmiş cihazlar" : "Eşleşmiş cihaz yok"; color: panel.c.muted; font.pixelSize: 12 }
                    Repeater {
                        model: panel.s.bluetooth.devices
                        Rectangle {
                            required property var modelData
                            width: quickPage.width; height: 42; radius: 12
                            color: modelData.connected ? Qt.alpha(panel.c.accent, 0.16) : (devMouse.containsMouse ? panel.c.control : "transparent")
                            Text { anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter } text: parent.modelData.name; color: panel.c.text; font.pixelSize: 13 }
                            Text { anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter } text: parent.modelData.connected ? "Bağlı" : "Bağlan"; color: parent.modelData.connected ? panel.c.accent : panel.c.muted; font.pixelSize: 12 }
                            MouseArea { id: devMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Shell.bluetoothDevice(parent.modelData.mac, !parent.modelData.connected) }
                        }
                    }
                    Rectangle {
                        width: quickPage.width; height: 38; radius: 12; color: panel.c.control
                        Text { anchors.centerIn: parent; text: "Yeni cihaz eşleştir…"; color: panel.c.text; font.pixelSize: 12 }
                        MouseArea { anchors.fill: parent; onClicked: { panel.close(); Shell.openSettings("kcm_bluetooth") } }
                    }
                }

                // Sound and brightness.
                Repeater {
                    model: [
                        { id: "volume", show: panel.s.volume.available, glyph: panel.s.volume.muted ? "muted" : "volume", value: panel.s.volume.percent, max: 100 },
                        { id: "brightness", show: panel.s.brightness.available, glyph: "sun", value: panel.s.brightness.percent, max: 100 },
                    ]
                    Row {
                        required property var modelData
                        visible: modelData.show === true
                        width: quickPage.width
                        spacing: 12
                        Rectangle {
                            width: 34; height: 34; radius: 17
                            color: parent.modelData.id === "volume" && panel.s.volume.muted ? Qt.alpha(panel.c.danger, 0.2) : panel.c.control
                            Glyph { anchors.centerIn: parent; kind: parent.parent.modelData.glyph; level: parent.parent.modelData.value / 100; color: panel.c.text }
                            MouseArea { anchors.fill: parent; onClicked: if (parent.parent.modelData.id === "volume") Shell.toggleMute() }
                        }
                        OziSlider {
                            c: panel.c
                            width: parent.width - 34 - 12 - 44
                            anchors.verticalCenter: parent.verticalCenter
                            from: parent.modelData.id === "brightness" ? 1 : 0; to: 100; stepSize: 1
                            value: parent.modelData.value
                            onMoved: (v) => parent.modelData.id === "volume" ? Shell.setVolume(v) : Shell.setBrightness(v)
                        }
                        Text { width: 32; text: parent.modelData.value + "%"; color: panel.c.muted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }
                }

                Rectangle {
                    width: quickPage.width; height: 38; radius: 12; color: panel.c.control
                    Text { anchors.centerIn: parent; text: "Tüm ayarlar"; color: panel.c.text; font.pixelSize: 12 }
                    MouseArea { anchors.fill: parent; onClicked: { panel.close(); Shell.openSettings("") } }
                }
            }

            // ----------------------------------------------------------- look
            Column {
                id: lookPage
                visible: panel.page === "look"
                width: flick.width
                spacing: 14

                // How a window looks with these settings.
                Item {
                    width: parent.width; height: 92
                    Rectangle {
                        id: preview
                        anchors.centerIn: parent
                        width: 190; height: 70
                        radius: panel.look.corner_radius
                        color: panel.c.ink
                        border.width: 1
                        border.color: Qt.tint(Qt.alpha(panel.c.text, 0.16), Qt.alpha(panel.c.accent, panel.look.glow * 0.6))
                        Rectangle {
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 1 }
                            height: 20; radius: Math.max(0, parent.radius - 1)
                            color: panel.c.raised
                            Row {
                                anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                                spacing: 9
                                Glyph { kind: "minimize"; color: panel.c.muted; size: 8 }
                                Glyph { kind: "maximize"; color: panel.c.muted; size: 8 }
                                Glyph { kind: "close"; color: panel.c.muted; size: 8 }
                            }
                        }
                    }
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 12
                    Repeater {
                        model: Shell.themes
                        Rectangle {
                            required property var modelData
                            readonly property bool chosen: modelData.id === panel.look.theme
                            // "auto": the two colours taken from the wallpaper.
                            readonly property bool auto: modelData.id === "auto"
                            width: 30; height: 30; radius: 15
                            color: modelData.accent
                            gradient: auto ? autoFill : null
                            Gradient {
                                id: autoFill
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.45; color: modelData.accent }
                                GradientStop { position: 0.55; color: modelData.accent2 }
                            }
                            border.width: chosen ? 2 : 0
                            border.color: panel.c.text
                            Rectangle {
                                anchors.centerIn: parent
                                width: 12; height: 12; radius: 6
                                color: parent.modelData.ink
                                visible: parent.chosen
                            }
                            MouseArea { id: themeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: Shell.setLook("theme", parent.modelData.id) }
                        }
                    }
                }

                Repeater {
                    model: [
                        { key: "glow", label: "Renkli kenar", from: 0, to: 1, step: 0.05, fmt: (v) => v === 0 ? "kapalı" : Math.round(v * 100) + "%" },
                        { key: "corner_radius", label: "Köşeler", from: 0, to: 16, step: 1, fmt: (v) => v + " px" },
                        { key: "animation_speed", label: "Hareket", from: 0, to: 2, step: 0.1, fmt: (v) => v === 0 ? "kapalı" : v.toFixed(1) + "×" },
                        { key: "lock_after_minutes", label: "Boşta kilitle", from: 0, to: 60, step: 5, fmt: (v) => v === 0 ? "hiçbir zaman" : v + " dk" },
                    ]
                    Column {
                        required property var modelData
                        width: lookPage.width
                        spacing: 4
                        Row {
                            width: parent.width
                            Text { text: modelData.label; color: panel.c.text; font.pixelSize: 13; width: parent.width - valueText.width }
                            Text { id: valueText; text: modelData.fmt(panel.look[modelData.key] ?? modelData.from); color: panel.c.muted; font.pixelSize: 12 }
                        }
                        OziSlider {
                            c: panel.c
                            width: parent.width
                            from: modelData.from; to: modelData.to; stepSize: modelData.step
                            value: panel.look[modelData.key] ?? modelData.from
                            onMoved: (v) => Shell.setLook(modelData.key, v)
                        }
                    }
                }

                // Wallpapers: the moving tesseract first, then every picture found.
                Text { text: "Duvar kâğıdı"; color: panel.c.text; font.pixelSize: 15; font.weight: Font.Bold }
                Grid {
                    columns: 3
                    spacing: 8
                    Repeater {
                        model: [{ path: "tesseract", title: "Canlı tesseract" }].concat(Shell.wallpapers)
                        Rectangle {
                            required property var modelData
                            readonly property bool chosen: panel.look.wallpaper === modelData.path
                            width: (lookPage.width - 16) / 3; height: width * 9 / 16; radius: 10
                            color: panel.c.ink
                            border.width: chosen ? 2 : 1
                            border.color: chosen ? panel.c.accent : Qt.alpha(panel.c.text, 0.10)
                            clip: true
                            Image {
                                anchors { fill: parent; margins: 2 }
                                visible: parent.modelData.path !== "tesseract"
                                source: visible ? "file://" + parent.modelData.path : ""
                                sourceSize: Qt.size(240, 135)
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                            }
                            Glyph { visible: parent.modelData.path === "tesseract"; anchors.centerIn: parent; kind: "cube"; color: panel.c.accent; size: 26 }
                            MouseArea { anchors.fill: parent; onClicked: Shell.setLook("wallpaper", parent.modelData.path) }
                        }
                    }
                }
            }
        }
    }
}
