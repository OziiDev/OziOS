// OziOS desktop layout: a thin bar across the top for the launcher, clock and
// tray, and a floating dock at the bottom for windows and pinned programs.

var bar = new Panel
bar.location = "top"
bar.height = Math.round(gridUnit * 1.7)
bar.lengthMode = "fill"
bar.hiding = "none"
bar.floating = false

bar.addWidget("org.kde.plasma.kickoff")
bar.addWidget("org.kde.plasma.pager")
bar.addWidget("org.kde.plasma.panelspacer")
bar.addWidget("org.kde.plasma.digitalclock")
bar.addWidget("org.kde.plasma.panelspacer")
bar.addWidget("org.ozios.control")
bar.addWidget("org.kde.plasma.systemtray")

var dock = new Panel
dock.location = "bottom"
dock.height = Math.round(gridUnit * 3)
dock.alignment = "center"
dock.lengthMode = "fit"
dock.floating = true
dock.hiding = "dodgewindows"

var tasks = dock.addWidget("org.kde.plasma.icontasks")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("launchers", [
    "preferred://filemanager",
    "preferred://browser",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop"
])

var desktops = desktopsForActivity(currentActivity())
for (var i = 0; i < desktops.length; i++) {
    desktops[i].wallpaperPlugin = "org.ozios.tesseract"
}
