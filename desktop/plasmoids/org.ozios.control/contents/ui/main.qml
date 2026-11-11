import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

// A tray popup with no logic of its own: every row runs an `ozi` command and
// shows what `ozi status --json` reports.
PlasmoidItem {
    id: root

    property var status: ({ version: "", kernel: "", effects: "full", game_mode: false,
                            power_profile: "unknown", windows_guest: "missing", updates: 0 })

    Plasmoid.icon: "ozios"
    toolTipMainText: "OziOS " + status.version
    toolTipSubText: status.game_mode ? i18n("Game mode is on") : i18n("Kernel %1", status.kernel)

    Plasma5Support.DataSource {
        id: shell
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            if (source.indexOf("status --json") >= 0 && data["exit code"] === 0) {
                try { root.status = JSON.parse(data["stdout"]) } catch (e) {}
            }
            disconnectSource(source)
            if (source.indexOf("status --json") < 0) refresh.restart()
        }
    }

    function run(command) { shell.connectSource(command) }
    function reload() { shell.connectSource("ozi status --json") }

    // A command that was just run changes the state; ask again shortly after.
    Timer { id: refresh; interval: 1200; onTriggered: root.reload() }
    Timer { interval: 60000; repeat: true; running: true; triggeredOnStart: true; onTriggered: root.reload() }

    compactRepresentation: Kirigami.Icon {
        source: "ozios"
        active: mouse.containsMouse
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.expanded = !root.expanded
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 18
        Layout.minimumHeight: Kirigami.Units.gridUnit * 14
        spacing: Kirigami.Units.smallSpacing

        PlasmaComponents.Label {
            text: "OziOS " + root.status.version
            font.pixelSize: Kirigami.Theme.defaultFont.pixelSize * 1.4
            color: "#00E5FF"
        }
        PlasmaComponents.Label {
            text: i18n("Kernel %1", root.status.kernel)
            opacity: 0.7
        }

        Kirigami.Separator { Layout.fillWidth: true }

        PlasmaComponents.Switch {
            Layout.fillWidth: true
            text: i18n("Game mode")
            checked: root.status.game_mode
            onToggled: root.run("ozi mode game " + (checked ? "on" : "off"))
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label { text: i18n("Effects"); Layout.fillWidth: true }
            Repeater {
                model: [["full", i18n("Full")], ["light", i18n("Light")], ["off", i18n("Off")]]
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
            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: i18n("Windows guest: %1", root.status.windows_guest === "missing" ? i18n("not set up") : root.status.windows_guest)
            }
            PlasmaComponents.Button {
                text: root.status.windows_guest === "missing" ? i18n("Set up") : i18n("Open")
                onClicked: root.run(root.status.windows_guest === "missing" ? "ozi-winsetup --gui" : "virsh -c qemu:///system start ozi-win; virt-viewer -c qemu:///system ozi-win")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            PlasmaComponents.Label {
                Layout.fillWidth: true
                text: root.status.updates > 0 ? i18n("%1 updates waiting", root.status.updates) : i18n("Up to date")
            }
            PlasmaComponents.Button {
                text: i18n("Software")
                onClicked: root.run("ozi-store")
            }
        }

        Item { Layout.fillHeight: true }
    }
}
