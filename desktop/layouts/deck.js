// OziOS layout "deck": one tall bar along the bottom with large targets, for
// a couch, a handheld or a controller-first setup. Games are pinned first.
panels().forEach(function (p) { p.remove() })

var bar = new Panel
bar.location = "bottom"
bar.height = Math.round(gridUnit * 3.6)
bar.lengthMode = "fill"
bar.hiding = "none"
bar.floating = false

bar.addWidget("org.kde.plasma.kickoff")

var tasks = bar.addWidget("org.kde.plasma.icontasks")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("launchers", [
    "applications:steam.desktop",
    "applications:net.lutris.Lutris.desktop",
    "applications:com.heroicgameslauncher.hgl.desktop",
    "preferred://browser",
    "preferred://filemanager",
    "applications:ozi-store.desktop"
])

bar.addWidget("org.kde.plasma.panelspacer")
bar.addWidget("org.ozios.control")
bar.addWidget("org.kde.plasma.systemtray")
bar.addWidget("org.kde.plasma.digitalclock")
