// OziOS Education layout "board": one tall bar along the bottom with large
// targets for fingers and a pen. The screen pen and the whiteboard come first.
panels().forEach(function (p) { p.remove() })

var bar = new Panel
bar.location = "bottom"
bar.height = Math.round(gridUnit * 4)
bar.lengthMode = "fill"
bar.hiding = "none"
bar.floating = false

bar.addWidget("org.kde.plasma.kickoff")

var tasks = bar.addWidget("org.kde.plasma.icontasks")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("launchers", [
    "applications:ozi-pen.desktop",
    "applications:com.github.xournalpp.xournalpp.desktop",
    "applications:libreoffice-impress.desktop",
    "applications:org.kde.okular.desktop",
    "applications:firefox.desktop",
    "applications:ozi-eba.desktop",
    "preferred://filemanager",
    "applications:org.kde.kcalc.desktop",
    "applications:ozi-store.desktop"
])

bar.addWidget("org.kde.plasma.panelspacer")
bar.addWidget("org.ozios.control")
bar.addWidget("org.kde.plasma.systemtray")
bar.addWidget("org.kde.plasma.digitalclock")
