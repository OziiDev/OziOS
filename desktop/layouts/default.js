// OziOS layout "default": three floating islands along the top, as on a tiling
// desktop's bar (the launcher and the desktops on the left, the clock in the
// middle, the tray and the control centre on the right), and a floating dock at
// the bottom for windows and pinned programs.
panels().forEach(function (p) { p.remove() })

function island(alignment) {
    var p = new Panel
    p.location = "top"
    p.height = Math.round(gridUnit * 1.8)
    p.lengthMode = "fit"
    p.alignment = alignment
    p.floating = true
    p.hiding = "none"
    return p
}

var left = island("left")
left.addWidget("org.ozios.launcher")
left.addWidget("org.ozios.workspaces")

var middle = island("center")
middle.addWidget("org.ozios.clock")

var right = island("right")
right.addWidget("org.kde.plasma.systemtray")
right.addWidget("org.ozios.control")

var dock = new Panel
dock.location = "bottom"
dock.height = Math.round(gridUnit * 3.6)
dock.alignment = "center"
dock.lengthMode = "fit"
dock.floating = true
dock.hiding = "dodgewindows"

var tasks = dock.addWidget("org.ozios.dock")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("launchers", [
    "preferred://filemanager",
    "preferred://browser",
    "applications:org.kde.konsole.desktop",
    "applications:ozi-store.desktop",
    "applications:systemsettings.desktop"
])
