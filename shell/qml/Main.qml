import QtQuick

// ozi-shell: every piece is its own layer-shell window inside oziwm.
QtObject {
    id: root

    property var c: Shell.colors
    property real speed: Shell.look.animation_speed
    // Durations scale with the user's speed; 0 turns motion off.
    function ms(base) { return speed > 0 ? Math.round(base / speed) : 0 }

    property Wallpaper wallpaper: Wallpaper { shell: root }
    // Inside Bar and Dock, `launcher` is their own signal: reach the windows through root.
    property Bar bar: Bar { shell: root; onQuickPanel: root.panel.toggle(); onLauncher: root.launcher.toggle() }
    property Dock dock: Dock { shell: root; onLauncher: root.launcher.toggle() }
    property Launcher launcher: Launcher { shell: root }
    property QuickPanel panel: QuickPanel { shell: root }
    property Notifications notes: Notifications { shell: root }

    property Connections events: Connections {
        target: Shell
        function onLauncherRequested() { root.launcher.toggle() }
    }
}
