// OziOS layout "classic": the familiar single panel along the bottom, with the
// menu on the left and the tray and clock on the right.
panels().forEach(function (p) { p.remove() })

var bar = new Panel
bar.location = "bottom"
bar.height = Math.round(gridUnit * 2.2)
bar.lengthMode = "fill"
bar.hiding = "none"
bar.floating = false

bar.addWidget("org.kde.plasma.kickoff")
bar.addWidget("org.kde.plasma.pager")

var tasks = bar.addWidget("org.kde.plasma.taskmanager")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("showToolTips", true)

bar.addWidget("org.kde.plasma.panelspacer")
bar.addWidget("org.ozios.control")
bar.addWidget("org.kde.plasma.systemtray")
bar.addWidget("org.kde.plasma.digitalclock")
bar.addWidget("org.kde.plasma.showdesktop")
