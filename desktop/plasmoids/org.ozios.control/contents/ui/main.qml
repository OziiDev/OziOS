import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// A tray popup with no logic of its own: every row runs an `ozi` command and
// shows what `ozi status --json` and `ozi theme --json` report.
PlasmoidItem {
    id: root

    property var status: ({ version: "", kernel: "", effects: "full", game_mode: false, layout: "default",
                            power_profile: "unknown", windows_guest: "missing", updates: 0 })
    property var themes: []

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
    }

    // A command that was just run changes the state; ask again shortly after.
    Timer { id: refresh; interval: 1200; onTriggered: root.reload() }
    Timer { interval: 60000; repeat: true; running: true; triggeredOnStart: true; onTriggered: root.reload() }

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

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 19
        Layout.minimumHeight: Kirigami.Units.gridUnit * 16
        spacing: Kirigami.Units.smallSpacing

        PlasmaComponents.Label {
            text: "OziOS " + root.status.version
            font.pixelSize: Kirigami.Theme.defaultFont.pixelSize * 1.4
            color: Kirigami.Theme.highlightColor
        }
        PlasmaComponents.Label {
            text: root.tx("Kernel %1", "Çekirdek %1", root.status.kernel)
            opacity: 0.7
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

        PlasmaComponents.Switch {
            Layout.fillWidth: true
            text: root.tx("Game mode", "Oyun modu")
            checked: root.status.game_mode
            onToggled: root.run("ozi mode game " + (checked ? "on" : "off"))
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

        Item { Layout.fillHeight: true }
    }
}
