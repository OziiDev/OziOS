import QtQuick

// ozi-shell: every piece is its own layer-shell window inside oziwm.
QtObject {
    id: root

    property var c: Shell.colors
    property real speed: Shell.look.animation_speed
    // Durations scale with the user's speed; 0 turns motion off.
    function ms(base) { return speed > 0 ? Math.round(base / speed) : 0 }

    property Wallpaper wallpaper: Wallpaper { shell: root }
    property Bar bar: Bar { shell: root; onQuickPanel: panel.toggle(); onLauncher: launcher.toggle() }
    property Dock dock: Dock { shell: root; onLauncher: launcher.toggle() }
    property Launcher launcher: Launcher { shell: root }
    property QuickPanel panel: QuickPanel { shell: root }

    property Connections events: Connections {
        target: Shell
        function onLauncherRequested() { root.launcher.toggle() }
    }
}
