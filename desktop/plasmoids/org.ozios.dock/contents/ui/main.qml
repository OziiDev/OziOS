import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager

// The OziOS dock: pinned programs and open windows, grouped by program.
// The motion lives in DockItem.qml; this file connects it to Plasma's task model.
PlasmoidItem {
    id: dock

    readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
    readonly property real thickness: vertical ? width : height
    readonly property real iconSize: Math.max(16, Math.round(thickness * 0.62))
    readonly property real slot: Math.round(iconSize * 1.3)
    // The user's animation speed setting; zero turns all motion off.
    readonly property bool animations: Kirigami.Units.longDuration > 1
    readonly property real maxZoom: Plasmoid.configuration.magnify && animations ? 1.25 : 1
    readonly property real reach: slot * 2.4
    property real pointer: -1             // where the pointer is along the dock, or -1

    // Plasma looks translations up in compiled catalogs that this package does not
    // ship; Turkish is the language OziOS supports, so its words are kept here.
    readonly property bool turkish: Qt.locale().name.indexOf("tr") === 0
    function tx(english, turkish) {
        let text = dock.turkish ? turkish : english
        for (let i = 2; i < arguments.length; i++)
            text = text.replace("%" + (i - 1), arguments[i])
        return text
    }

    preferredRepresentation: fullRepresentation
    Plasmoid.constraintHints: Plasmoid.CanFillArea

    Layout.fillWidth: false
    Layout.fillHeight: false
    Layout.minimumWidth: vertical ? 0 : Math.max(slot, list.count * slot)
    Layout.preferredWidth: Layout.minimumWidth
    Layout.maximumWidth: Layout.minimumWidth
    Layout.minimumHeight: vertical ? Math.max(slot, list.count * slot) : 0
    Layout.preferredHeight: Layout.minimumHeight
    Layout.maximumHeight: vertical ? Layout.minimumHeight : -1

    // How much an icon whose middle is at `position` grows: a smooth bell around the pointer.
    function zoomFor(position) {
        if (pointer < 0 || maxZoom <= 1)
            return 1
        const distance = Math.abs(position - pointer)
        if (distance >= reach)
            return 1
        return 1 + (maxZoom - 1) * (Math.cos(Math.PI * distance / reach) + 1) / 2
    }

    function activate(task) {
        const index = tasksModel.makeModelIndex(task.index)
        if (task.model.IsLauncher) {
            task.face.bounce()
            tasksModel.requestActivate(index)
        } else if (task.model.IsActive && !task.model.IsGroupParent) {
            tasksModel.requestToggleMinimized(index)
        } else {
            tasksModel.requestActivate(index)
        }
    }

    function publishGeometry(task) {
        if (!task || task.model.IsLauncher || task.model.IsStartup)
            return
        const corner = task.mapToGlobal(0, 0)
        tasksModel.requestPublishDelegateGeometry(tasksModel.makeModelIndex(task.index),
                                                  Qt.rect(corner.x, corner.y, task.width, task.height), task)
    }

    TaskManager.VirtualDesktopInfo { id: virtualDesktopInfo }
    TaskManager.ActivityInfo { id: activityInfo }

    TaskManager.TasksModel {
        id: tasksModel
        screenGeometry: Plasmoid.containment.screenGeometry
        activity: activityInfo.currentActivity
        filterByCurrentVirtualDesktop: true
        filterByScreen: false
        filterByActivity: true
        hideActivatedLaunchers: true
        separateLaunchers: false
        launchInPlace: true
        sortMode: TaskManager.TasksModel.SortManual
        groupMode: TaskManager.TasksModel.GroupApplications
        groupInline: false

        onLauncherListChanged: Plasmoid.configuration.launchers = launcherList
        Component.onCompleted: {
            launcherList = Plasmoid.configuration.launchers
            list.model = tasksModel        // only after the launchers are in
        }
    }

    Connections {
        target: Plasmoid.configuration
        function onLaunchersChanged() {
            if (tasksModel.launcherList.toString() !== Plasmoid.configuration.launchers.toString())
                tasksModel.launcherList = Plasmoid.configuration.launchers
        }
    }

    // The minimize animation flies to the icon; tell the window manager where the icons are.
    Timer {
        id: geometryTimer
        interval: 400
        onTriggered: {
            for (let i = 0; i < list.count; i++)
                dock.publishGeometry(list.itemAtIndex(i))
        }
    }

    Binding {
        target: Plasmoid
        property: "status"
        value: tasksModel.anyTaskDemandsAttention ? PlasmaCore.Types.NeedsAttentionStatus : PlasmaCore.Types.PassiveStatus
        restoreMode: Binding.RestoreBinding
    }

    HoverHandler {
        id: hover
        onPointChanged: dock.pointer = hovered ? (dock.vertical ? point.position.y : point.position.x) : -1
        onHoveredChanged: if (!hovered) dock.pointer = -1
    }

    ListView {
        id: list
        anchors.fill: parent
        orientation: dock.vertical ? ListView.Vertical : ListView.Horizontal
        interactive: false
        spacing: 0
        boundsBehavior: Flickable.StopAtBounds
        onCountChanged: geometryTimer.restart()
        onWidthChanged: geometryTimer.restart()
        onHeightChanged: geometryTimer.restart()

        add: Transition {
            enabled: dock.animations
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220 }
        }
        remove: Transition {
            enabled: dock.animations
            ParallelAnimation {
                NumberAnimation { property: "opacity"; to: 0; duration: 200; easing.type: Easing.InQuad }
                NumberAnimation { property: "scale"; to: 0.4; duration: 220; easing.type: Easing.InBack }
            }
        }
        displaced: Transition {
            enabled: dock.animations
            NumberAnimation { properties: "x,y"; duration: 260; easing.type: Easing.OutCubic }
        }

        delegate: PlasmaCore.ToolTipArea {
            id: task

            required property int index
            required property var model
            readonly property alias face: face

            width: dock.vertical ? list.width : dock.slot
            height: dock.vertical ? dock.slot : list.height

            mainText: model.display || ""
            subText: model.ChildCount > 1 ? dock.tx("%1 windows", "%1 pencere", model.ChildCount) : ""
            location: Plasmoid.location
            active: !menu.opened

            DockItem {
                id: face
                anchors.fill: parent
                baseSize: dock.iconSize
                zoom: dock.zoomFor(dock.vertical ? task.y - list.contentY + task.height / 2
                                                 : task.x - list.contentX + task.width / 2)
                hovered: task.containsMouse
                pressed: leftTap.pressed
                running: !task.model.IsLauncher && !task.model.IsStartup
                active: task.model.IsActive === true
                attention: task.model.IsDemandingAttention === true
                starting: task.model.IsStartup === true
                windows: task.model.ChildCount > 0 ? task.model.ChildCount : (running ? 1 : 0)
                accent: Kirigami.Theme.highlightColor
                lightColor: Kirigami.Theme.textColor
                attentionColor: Kirigami.Theme.neutralTextColor
                animate: dock.animations

                Kirigami.Icon {
                    anchors.fill: parent
                    source: task.model.decoration
                    active: task.containsMouse
                    roundToIconSize: false
                }
            }

            TapHandler {
                id: leftTap
                acceptedButtons: Qt.LeftButton
                onTapped: dock.activate(task)
            }
            TapHandler {
                acceptedButtons: Qt.MiddleButton
                onTapped: tasksModel.requestNewInstance(tasksModel.makeModelIndex(task.index))
            }
            TapHandler {
                acceptedButtons: Qt.RightButton
                gesturePolicy: TapHandler.WithinBounds
                onPressedChanged: if (pressed) menu.openRelative()
            }

            PlasmaExtras.Menu {
                id: menu
                readonly property bool opened: status === PlasmaExtras.Menu.Open
                visualParent: task
                placement: dock.vertical ? PlasmaExtras.Menu.RightPosedTopAlignedPopup : PlasmaExtras.Menu.TopPosedLeftAlignedPopup

                PlasmaExtras.MenuItem {
                    text: dock.tx("Open a new window", "Yeni pencere aç")
                    icon: "window-new"
                    visible: task.model.CanLaunchNewInstance === true
                    onClicked: tasksModel.requestNewInstance(tasksModel.makeModelIndex(task.index))
                }
                PlasmaExtras.MenuItem {
                    readonly property bool pinned: tasksModel.launcherPosition(task.model.LauncherUrlWithoutIcon) !== -1
                    text: pinned ? dock.tx("Unpin from the dock", "Dock'tan çıkar") : dock.tx("Pin to the dock", "Dock'a sabitle")
                    icon: pinned ? "window-unpin" : "window-pin"
                    visible: String(task.model.LauncherUrlWithoutIcon || "") !== ""
                    onClicked: {
                        if (pinned)
                            tasksModel.requestRemoveLauncher(task.model.LauncherUrlWithoutIcon)
                        else
                            tasksModel.requestAddLauncher(task.model.LauncherUrl)
                    }
                }
                PlasmaExtras.MenuItem {
                    text: task.model.ChildCount > 1 ? dock.tx("Close all windows", "Tüm pencereleri kapat") : dock.tx("Close", "Kapat")
                    icon: "window-close"
                    visible: !task.model.IsLauncher && !task.model.IsStartup
                    onClicked: tasksModel.requestClose(tasksModel.makeModelIndex(task.index))
                }
            }
        }
    }
}
