import QtQuick
import org.kde.taskmanager as TaskManager

// Tells the wallpaper when nobody can see it: some window on the current
// desktop is maximized or full screen. Kept in its own file so the wallpaper
// still loads if the task manager module is unavailable.
Item {
    id: root
    property bool covered: false

    function refresh() {
        let hidden = false
        for (let i = 0; i < tasks.count && !hidden; i++) {
            const idx = tasks.index(i, 0)
            hidden = tasks.data(idx, TaskManager.AbstractTasksModel.IsMaximized) === true
                  || tasks.data(idx, TaskManager.AbstractTasksModel.IsFullScreen) === true
        }
        covered = hidden
    }

    TaskManager.VirtualDesktopInfo { id: desktops }
    TaskManager.ActivityInfo { id: activities }

    TaskManager.TasksModel {
        id: tasks
        sortMode: TaskManager.TasksModel.SortDisabled
        groupMode: TaskManager.TasksModel.GroupDisabled
        virtualDesktop: desktops.currentDesktop
        activity: activities.currentActivity
        filterByVirtualDesktop: true
        filterByActivity: true
        filterMinimized: true

        onCountChanged: root.refresh()
        onDataChanged: root.refresh()
        onVirtualDesktopChanged: root.refresh()
        Component.onCompleted: root.refresh()
    }
}
