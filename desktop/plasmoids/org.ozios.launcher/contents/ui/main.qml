import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.private.kicker as Kicker
import org.kde.coreaddons as KCoreAddons
import org.kde.kirigami as Kirigami
// Avatar left Kirigami in KDE Frameworks 6; Kickoff takes it from Kirigami Addons too.
import org.kde.kirigamiaddons.components as KirigamiComponents

// The OziOS launcher: a greeting, a search field, the categories as chips and
// every program in a grid that flows in when it opens. The Meta key opens it.
// The models are the ones Plasma's own launchers use (Kicker); the look and the
// motion are OziOS's.
PlasmoidItem {
    id: launcher

    property string query: ""
    readonly property bool animations: Kirigami.Units.longDuration > 1

    readonly property bool turkish: Qt.locale().name.indexOf("tr") === 0
    function tx(english, turkish) {
        return launcher.turkish ? turkish : english
    }

    Plasmoid.icon: Plasmoid.configuration.icon
    preferredRepresentation: compactRepresentation
    switchWidth: Kirigami.Units.gridUnit * 30
    switchHeight: Kirigami.Units.gridUnit * 22
    onExpandedChanged: if (!launcher.expanded) launcher.query = ""

    // Set up like Kickoff's, so the rows mean the same: 0 favourites, 1 all programs, 2.. categories.
    readonly property Kicker.RootModel rootModel: Kicker.RootModel {
        autoPopulate: false
        appletInterface: launcher
        appNameFormat: 0
        flat: true
        sorted: true
        showSeparators: false
        showRootSeparator: true
        showTopLevelItems: true
        showAllApps: true
        showAllAppsCategorized: false
        showRecentApps: false
        showRecentDocs: false
        showPowerSession: false
        showFavoritesPlaceholder: true
        Component.onCompleted: favoritesModel.initForClient("org.ozios.launcher.favorites.instance-" + Plasmoid.id)
    }

    readonly property Kicker.RunnerModel runnerModel: Kicker.RunnerModel {
        query: launcher.query
        appletInterface: launcher
        mergeResults: true
        favoritesModel: launcher.rootModel.favoritesModel
    }

    Kicker.SystemModel {
        id: systemModel
        favoritesModel: launcher.rootModel.systemFavoritesModel
    }

    KCoreAddons.KUser { id: user }

    Component.onCompleted: rootModel.refresh()

    compactRepresentation: MouseArea {
        id: button
        property bool wasExpanded: false
        hoverEnabled: true
        Layout.minimumWidth: height
        Layout.preferredWidth: height
        onPressed: wasExpanded = launcher.expanded
        onClicked: launcher.expanded = !wasExpanded

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) * 0.9
            height: width
            radius: width * 0.3
            color: Kirigami.Theme.highlightColor
            opacity: launcher.expanded ? 0.2 : button.containsMouse ? 0.12 : 0
            Behavior on opacity { NumberAnimation { duration: 180 } }
        }
        Kirigami.Icon {
            anchors.centerIn: parent
            width: Math.round(Math.min(parent.width, parent.height) * 0.72)
            height: width
            source: Plasmoid.icon
            active: button.containsMouse
            // The mark turns a quarter while the launcher is open, and leans toward the pointer.
            rotation: launcher.expanded ? 90 : 0
            scale: button.containsMouse ? 1.1 : 1
            Behavior on rotation {
                enabled: launcher.animations
                NumberAnimation { duration: 420; easing.type: Easing.OutBack }
            }
            Behavior on scale {
                enabled: launcher.animations
                SpringAnimation { spring: 5; damping: 0.3; epsilon: 0.002 }
            }
        }
    }

    fullRepresentation: FocusScope {
        id: full

        Layout.preferredWidth: Kirigami.Units.gridUnit * 46
        Layout.preferredHeight: Kirigami.Units.gridUnit * 32
        Layout.minimumWidth: Kirigami.Units.gridUnit * 30
        Layout.minimumHeight: Kirigami.Units.gridUnit * 22
        focus: true

        property int category: 1
        property int generation: 0         // goes up when the program list is rebuilt
        readonly property bool searching: launcher.query.length > 0
        readonly property var appsModel: {
            full.generation;
            return launcher.rootModel.count > full.category ? launcher.rootModel.modelForRow(full.category) : null
        }
        readonly property var resultsModel: {
            launcher.runnerModel.count;      // re-run whenever the results change
            return launcher.runnerModel.count ? launcher.runnerModel.modelForRow(0) : null
        }
        readonly property var categories: {
            full.generation;
            const out = [{ row: 1, name: launcher.tx("All", "Tümü") }]
            const model = launcher.rootModel
            for (let row = 2; row < model.count; row++) {
                const name = model.data(model.index(row, 0), Qt.DisplayRole)
                if (name)
                    out.push({ row: row, name: name })
            }
            return out
        }

        function greeting() {
            const hour = new Date().getHours()
            const name = user.fullName || user.loginName
            let text
            if (hour < 5) text = launcher.tx("Good night", "İyi geceler")
            else if (hour < 12) text = launcher.tx("Good morning", "Günaydın")
            else if (hour < 18) text = launcher.tx("Good afternoon", "İyi günler")
            else text = launcher.tx("Good evening", "İyi akşamlar")
            return name ? text + ", " + name.split(" ")[0] : text
        }

        function launch(index) {
            const model = grid.model
            if (model && model.trigger && index >= 0 && model.trigger(index, "", null))
                launcher.expanded = false
        }

        Connections {
            target: launcher.rootModel
            function onRefreshed() { full.generation++ }
        }
        Connections {
            target: launcher
            function onExpandedChanged() {
                if (launcher.expanded) {
                    search.text = ""
                    full.category = 1
                    // A fresh set of tiles, so they flow in again each time the launcher opens.
                    grid.model = null
                    grid.model = Qt.binding(() => full.searching ? full.resultsModel : full.appsModel)
                    search.forceActiveFocus()
                }
            }
        }

        // Typing anywhere goes to the search field.
        Keys.onPressed: event => {
            if (event.text.length > 0 && event.text.trim().length > 0 && !search.activeFocus) {
                search.forceActiveFocus()
                search.text += event.text
                event.accepted = true
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                KirigamiComponents.Avatar {
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                    source: user.faceIconUrl
                    name: user.fullName || user.loginName
                }
                PlasmaComponents.Label {
                    text: full.greeting()
                    font.pixelSize: Math.round(Kirigami.Theme.defaultFont.pixelSize * 1.35)
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                PlasmaExtras.SearchField {
                    id: search
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 16
                    placeholderText: launcher.tx("Search programs, settings, files...", "Program, ayar, dosya ara...")
                    focus: true
                    onTextChanged: launcher.query = text
                    Keys.onDownPressed: event => { grid.forceActiveFocus(); grid.currentIndex = 0 }
                    Keys.onReturnPressed: event => full.launch(Math.max(0, grid.currentIndex))
                    Keys.onEnterPressed: event => full.launch(Math.max(0, grid.currentIndex))
                    Keys.onEscapePressed: event => {
                        if (text.length > 0) text = ""
                        else launcher.expanded = false
                    }
                }
            }

            // The categories, with a light that slides to the chosen one.
            ListView {
                id: chips
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 1.8
                visible: !full.searching
                orientation: ListView.Horizontal
                spacing: Kirigami.Units.smallSpacing
                clip: true
                model: full.categories
                currentIndex: Math.max(0, full.categories.findIndex(c => c.row === full.category))
                highlightMoveDuration: launcher.animations ? 260 : 0
                highlightResizeDuration: launcher.animations ? 260 : 0
                highlight: Rectangle {
                    radius: height / 2
                    color: Kirigami.Theme.highlightColor
                    opacity: 0.22
                }
                delegate: MouseArea {
                    id: chip
                    required property var modelData
                    required property int index
                    width: chipLabel.implicitWidth + Kirigami.Units.gridUnit * 1.2
                    height: chips.height
                    hoverEnabled: true
                    onClicked: full.category = modelData.row

                    Rectangle {
                        anchors.fill: parent
                        radius: height / 2
                        color: "transparent"
                        border.width: 1
                        border.color: Kirigami.Theme.highlightColor
                        opacity: chip.containsMouse ? 0.6 : 0.18
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }
                    PlasmaComponents.Label {
                        id: chipLabel
                        anchors.centerIn: parent
                        text: chip.modelData.name
                        color: chip.index === chips.currentIndex ? Kirigami.Theme.highlightColor : Kirigami.Theme.textColor
                    }
                }
            }

            GridView {
                id: grid
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                focus: false
                keyNavigationEnabled: true
                keyNavigationWraps: true
                boundsBehavior: Flickable.StopAtBounds
                readonly property int columns: Math.max(3, Math.floor(width / (Kirigami.Units.gridUnit * 6.5)))
                cellWidth: Math.floor(width / columns)
                cellHeight: Math.round(Kirigami.Units.iconSizes.large * 2.3)
                model: full.searching ? full.resultsModel : full.appsModel
                currentIndex: -1
                highlightMoveDuration: launcher.animations ? 140 : 0
                highlight: Rectangle {
                    radius: Kirigami.Units.cornerRadius * 2
                    color: Kirigami.Theme.highlightColor
                    opacity: 0.14
                }
                onModelChanged: currentIndex = full.searching && count > 0 ? 0 : -1
                // Search results arrive after the model is set: light the first one, which Enter opens.
                onCountChanged: if (full.searching && count > 0 && currentIndex < 0) currentIndex = 0
                Keys.onReturnPressed: event => full.launch(currentIndex)
                Keys.onEnterPressed: event => full.launch(currentIndex)
                Keys.onEscapePressed: event => launcher.expanded = false

                delegate: MouseArea {
                    id: cell
                    required property int index
                    required property var model
                    width: grid.cellWidth
                    height: grid.cellHeight
                    hoverEnabled: true
                    onContainsMouseChanged: if (containsMouse) grid.currentIndex = index
                    onClicked: full.launch(index)

                    AppTile {
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        label: cell.model.display || ""
                        hovered: cell.containsMouse
                        pressed: cell.pressed
                        current: grid.currentIndex === cell.index
                        order: cell.index
                        animate: launcher.animations
                        iconSize: Kirigami.Units.iconSizes.large
                        textColor: Kirigami.Theme.textColor
                        accent: Kirigami.Theme.highlightColor
                        font: Kirigami.Theme.defaultFont

                        Kirigami.Icon {
                            anchors.fill: parent
                            source: cell.model.decoration
                            active: cell.containsMouse
                        }
                    }
                }

                PlasmaComponents.Label {
                    anchors.centerIn: parent
                    visible: full.searching && grid.count === 0
                    text: launcher.tx("Nothing found", "Bir şey bulunamadı")
                    opacity: 0.7
                }
            }

            // Lock, log out, restart, shut down.
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: user.loginName + "@" + user.host
                    opacity: 0.55
                    elide: Text.ElideRight
                }
                Repeater {
                    model: systemModel
                    delegate: MouseArea {
                        id: power
                        required property int index
                        required property var model
                        readonly property var wanted: ["lock-screen", "logout", "reboot", "shutdown"]
                        objectName: "power-" + model.favoriteId
                        visible: wanted.indexOf(model.favoriteId) >= 0
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2.2
                        Layout.preferredHeight: Kirigami.Units.gridUnit * 2.2
                        hoverEnabled: true
                        onClicked: {
                            launcher.expanded = false
                            systemModel.trigger(index, "", null)
                        }

                        PlasmaCore.ToolTipArea {
                            anchors.fill: parent
                            mainText: power.model.display || ""
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: width * 0.3
                            color: power.model.favoriteId === "shutdown" ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.highlightColor
                            opacity: power.containsMouse ? 0.22 : 0
                            Behavior on opacity { NumberAnimation { duration: 150 } }
                        }
                        Kirigami.Icon {
                            anchors.centerIn: parent
                            width: Kirigami.Units.iconSizes.smallMedium
                            height: width
                            source: power.model.decoration
                            scale: power.pressed ? 0.85 : power.containsMouse ? 1.12 : 1
                            Behavior on scale {
                                enabled: launcher.animations
                                SpringAnimation { spring: 5; damping: 0.3; epsilon: 0.002 }
                            }
                        }
                    }
                }
            }
        }
    }
}
