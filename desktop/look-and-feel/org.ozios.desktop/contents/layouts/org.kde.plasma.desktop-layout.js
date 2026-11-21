// OziOS desktop layout: three floating islands along the top (launcher and
// desktops, clock, tray and control centre) and a floating dock at the bottom
// for windows and pinned programs.

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

var desktops = desktopsForActivity(currentActivity())
for (var i = 0; i < desktops.length; i++) {
    desktops[i].wallpaperPlugin = "org.ozios.tesseract"
}
