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
    property Bar bar: Bar { shell: root; onQuickPanel: root.panel.toggle(); onLauncher: root.launcher.toggle(); onCalendar: root.calendar.toggle(); onTrayMenuAt: (x) => root.trayMenu.anchorX = x; onKeyboard: root.keyboard.toggle() }
    property Dock dock: Dock { shell: root; onLauncher: root.launcher.toggle() }
    property Launcher launcher: Launcher { shell: root }
    property QuickPanel panel: QuickPanel { shell: root }
    property Notifications notes: Notifications { shell: root }
    property Osd osd: Osd { shell: root }
    property Switcher switcher: Switcher { shell: root }
    property ClipboardPanel clipboard: ClipboardPanel { shell: root }
    property AreaShot areaShot: AreaShot { shell: root }
    property Calendar calendar: Calendar { shell: root }
    property TrayMenu trayMenu: TrayMenu { shell: root }
    property Keyboard keyboard: Keyboard { shell: root }

    property Connections events: Connections {
        target: Shell
        function onLauncherRequested() { root.launcher.toggle() }
        function onPanelRequested() { root.panel.toggle() }
        function onClipboardRequested() { root.clipboard.toggle() }
        function onAreaShotRequested() { root.areaShot.start() }
        function onOsd(kind, value) { root.osd.popup(kind, value) }
    }
    property Connections trayEvents: Connections {
        target: Tray
        function onMenuReady(service, entries) { root.trayMenu.openWith(service, entries) }
    }
}
