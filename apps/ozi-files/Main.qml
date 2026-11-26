import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

// Ozi Files: places on the left, the folder on the right as icons or a list.
// Click selects, double click (or Enter) opens; Ctrl/Shift pick more. Right
// click for everything else. Copy and cut use the system clipboard, so they
// work with other programs too.
ApplicationWindow {
    id: win
    width: 1040; height: 660
    minimumWidth: 620; minimumHeight: 420
    visible: true
    color: Theme.ink
    title: (path === "trash:" ? backend.tr("Trash") : folderName(path)) + " — " + backend.tr("Files")

    // ---- state ---------------------------------------------------------
    property string path: ""
    property var entries: []
    property var shown: entries               // entries, or search results
    property var places: []
    property var drives: []
    property var history: []
    property int historyAt: -1
    property bool hidden: false
    property bool grid: true
    property string sort: "name"
    property bool writable: true
    property string freeText: ""
    property string query: ""
    property bool searching: false
    property var selected: ({})               // path -> true
    property int current: -1                  // keyboard position
    property int anchor: -1                   // Shift+click starts here
    property string renaming: ""
    property string message: ""
    property real progress: -1                // 0..1 while copying
    property string progressText: ""
    readonly property bool inTrash: path === "trash:"
    readonly property var selection: shown.filter(e => selected[e.path])
    readonly property var selectedPaths: selection.map(e => e.path)

    function folderName(p) {
        if (p === "/") return backend.tr("Computer")
        const home = places.length ? places[0].path : ""
        if (p === home) return backend.tr("Home")
        const parts = p.split("/").filter(x => x)
        return parts.length ? parts[parts.length - 1] : p
    }
    function iconUrl(e) { return "image://icon/" + e.icons.join("|") }
    function say(text) { message = text; messageTimer.restart() }
    Timer { id: messageTimer; interval: 4000; onTriggered: win.message = "" }

    // ---- talking to the backend ---------------------------------------------------
    property int seq: 0
    function call(task, name, args) { backend.call(task, name, JSON.stringify(args || [])) }

    function go(p, remember) {
        if (!p) return
        if (remember !== false) {
            history = history.slice(0, historyAt + 1).concat([p])
            historyAt = history.length - 1
        }
        path = p
        query = ""; searchField.text = ""; searching = false
        selected = ({}); current = -1; anchor = -1; renaming = ""
        reload()
        backend.watch(p)
    }
    function reload() { call("list", "list", [path, hidden, sort, false]) }
    function back() { if (historyAt > 0) { historyAt--; go(history[historyAt], false) } }
    function forward() { if (historyAt < history.length - 1) { historyAt++; go(history[historyAt], false) } }
    function up() {
        if (inTrash || path === "/") return
        const parent = path.replace(/\/[^\/]*\/?$/, "") || "/"
        go(parent)
    }

    function open(e) {
        if (!e) return
        if (e.dir) { go(e.path); return }
        if (inTrash) { say(backend.tr("Restore it to open it.")); return }
        call("open", "open", [e.path])
    }

    Component.onCompleted: {
        call("places", "places")
        go(backend.startPath())
    }

    Connections {
        target: backend
        function onFolderChanged() { if (!win.searching) win.reload(); win.call("places", "places") }
        function onLog(task, line) {
            const m = line.match(/^progress (\d+) (\d+)/)
            if (m) win.progress = Number(m[1]) / Math.max(1, Number(m[2]))
        }
        function onDone(task, json) {
            const r = JSON.parse(json)
            if (task === "list") {
                win.entries = r.entries
                win.writable = r.writable
                win.freeText = r.free.text
                if (!win.searching) win.shown = r.entries
                if (win.current >= win.shown.length) win.current = win.shown.length - 1
            } else if (task === "places") {
                win.places = r.places
                win.drives = r.drives
            } else if (task === "search") {
                win.shown = r
            } else if (task === "transfer" || task === "extract" || task === "compress") {
                win.progress = -1
                win.reload()
            } else if (task === "appsFor") {
                openWith.apps = r
                openWith.open()
            } else if (task === "properties") {
                props.info = r
            } else if (task === "mount") {
                win.call("places", "places")
                if (r) win.go(r)
            } else if (task === "mkdir" || task === "mkfile") {
                win.pendingSelect = r
                win.reload()
            } else if (task === "rename") {
                win.pendingSelect = r
                win.reload()
            } else {
                win.reload()
                win.call("places", "places")
            }
        }
        function onFailed(task, text) {
            win.progress = -1
            if (task === "list") { win.entries = []; win.shown = [] }
            win.say(text.indexOf("PermissionError") >= 0 ? backend.tr("You may not open this folder.")
                    : text.indexOf("FileNotFoundError") >= 0 ? backend.tr("It is not there any more.") : text)
        }
    }
    // After a new folder or a rename: select it and show it.
    property string pendingSelect: ""
    onShownChanged: {
        if (!pendingSelect) return
        const i = shown.findIndex(e => e.path === pendingSelect)
        if (i >= 0) { selectOnly(i); view.positionViewAtIndex(i, ListView.Contain) }
        pendingSelect = ""
    }

    // ---- selection -------------------------------------------------------------
    function selectOnly(i) {
        const s = {}
        if (i >= 0 && i < shown.length) s[shown[i].path] = true
        selected = s; current = i; anchor = i
    }
    function clickAt(i, mods) {
        if (mods & Qt.ControlModifier) {
            const s = Object.assign({}, selected)
            const p = shown[i].path
            if (s[p]) delete s[p]; else s[p] = true
            selected = s; current = i; anchor = i
        } else if ((mods & Qt.ShiftModifier) && anchor >= 0) {
            const s = {}
            for (let k = Math.min(anchor, i); k <= Math.max(anchor, i); k++) s[shown[k].path] = true
            selected = s; current = i
        } else {
            selectOnly(i)
        }
    }
    function selectAll() { const s = {}; shown.forEach(e => s[e.path] = true); selected = s }
    function moveCurrent(step, extend) {
        if (!shown.length) return
        const i = Math.max(0, Math.min(shown.length - 1, (current < 0 ? 0 : current + step)))
        if (extend) clickAt(i, Qt.ShiftModifier); else selectOnly(i)
        view.positionViewAtIndex(i, GridView.Contain)
    }

    // ---- actions -----------------------------------------------------------------
    function copy(cut) {
        if (!selectedPaths.length || inTrash) return
        backend.setClipboard(selectedPaths, cut)
        say(cut ? backend.tr("Cut: paste it where it should go") : backend.tr("Copied"))
    }
    function paste() {
        if (inTrash || !writable) return
        const c = backend.clipboard()
        if (!c.paths.length) return
        startTransfer(c.paths, path, c.cut)
        if (c.cut) backend.setClipboard([], false)
    }
    function startTransfer(paths, dest, move) {
        progress = 0
        progressText = move ? backend.tr("Moving…") : backend.tr("Copying…")
        call("transfer", "transfer", [paths, dest, move])
    }
    function toTrash() {
        if (!selectedPaths.length) return
        if (inTrash) { confirmDelete.open(); return }
        call("trash", "trash", [selectedPaths])
        say(selectedPaths.length === 1 ? backend.tr("Moved to the trash")
                                       : backend.tr("Moved to the trash") + " (" + selectedPaths.length + ")")
    }
    function startRename() {
        if (selection.length !== 1 || inTrash) return
        renaming = selection[0].path
    }
    function newFolder() {
        if (inTrash || !writable) return
        call("mkdir", "mkdir", [path, backend.tr("New folder")])
    }

    // ---- keys ------------------------------------------------------------------
    Shortcut { sequence: "Alt+Left"; onActivated: win.back() }
    Shortcut { sequence: "Back"; onActivated: win.back() }
    Shortcut { sequence: "Alt+Right"; onActivated: win.forward() }
    Shortcut { sequence: "Alt+Up"; onActivated: win.up() }
    Shortcut { sequence: "Alt+Home"; onActivated: win.go(win.places[0].path) }
    Shortcut { sequence: "F5"; onActivated: win.reload() }
    Shortcut { sequence: "Ctrl+L"; onActivated: { pathEdit.visible = true; pathEdit.forceActiveFocus(); pathEdit.selectAll() } }
    Shortcut { sequence: "Ctrl+F"; onActivated: searchField.forceActiveFocus() }
    Shortcut { sequence: "Ctrl+H"; onActivated: { win.hidden = !win.hidden; win.reload() } }
    Shortcut { sequence: "Ctrl+Shift+N"; onActivated: win.newFolder() }

    // ---- top bar -----------------------------------------------------------------
    component ToolIcon: Rectangle {
        id: tb
        property string glyph
        property string tip
        signal clicked()
        width: 34; height: 34; radius: 8
        opacity: enabled ? 1 : 0.35
        color: tbMouse.pressed ? Qt.alpha(Theme.ice, 0.14) : tbMouse.containsMouse ? Qt.alpha(Theme.ice, 0.08) : "transparent"
        Text { anchors.centerIn: parent; text: tb.glyph; color: Theme.ice; font.pixelSize: 17; font.family: Theme.family }
        MouseArea { id: tbMouse; anchors.fill: parent; hoverEnabled: true; onClicked: tb.clicked() }
        ToolTip.visible: tbMouse.containsMouse && tip !== ""
        ToolTip.text: tip
        ToolTip.delay: 600
    }

    header: Rectangle {
        height: 52
        color: Theme.raised
        Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: Qt.alpha(Theme.ice, 0.07) }
        RowLayout {
            anchors { fill: parent; leftMargin: 10; rightMargin: 10 }
            spacing: 4
            ToolIcon { glyph: "‹"; tip: backend.tr("Back"); enabled: win.historyAt > 0; onClicked: win.back() }
            ToolIcon { glyph: "›"; tip: backend.tr("Forward"); enabled: win.historyAt < win.history.length - 1; onClicked: win.forward() }
            ToolIcon { glyph: "↑"; tip: backend.tr("Up"); enabled: !win.inTrash && win.path !== "/"; onClicked: win.up() }

            // Where we are: each part is a button; a click on the empty end edits the path.
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 6
                height: 34; radius: 8
                color: Theme.control
                border.width: pathEdit.activeFocus ? 1 : 0
                border.color: Theme.cyan
                clip: true
                MouseArea { anchors.fill: parent; onClicked: { pathEdit.visible = true; pathEdit.forceActiveFocus(); pathEdit.selectAll() } }
                Flickable {
                    id: crumbsFlick
                    visible: !pathEdit.visible
                    anchors { fill: parent; leftMargin: 6; rightMargin: 6 }
                    contentWidth: crumbs.width
                    contentX: Math.max(0, contentWidth - width)
                    interactive: false
                    Row {
                        id: crumbs
                        height: parent.height
                        spacing: 0
                        readonly property var parts: {
                            if (win.inTrash) return [{ name: backend.tr("Trash"), path: "trash:" }]
                            const home = win.places.length ? win.places[0].path : ""
                            let base = "/", out = [{ name: backend.tr("Computer"), path: "/" }], rest = win.path
                            if (home && (win.path === home || win.path.startsWith(home + "/"))) {
                                out = [{ name: backend.tr("Home"), path: home }]; base = home; rest = win.path.slice(home.length)
                            }
                            let acc = base === "/" ? "" : base
                            rest.split("/").filter(x => x).forEach(p => { acc += "/" + p; out.push({ name: p, path: acc }) })
                            return out
                        }
                        Repeater {
                            model: crumbs.parts
                            Row {
                                required property var modelData
                                required property int index
                                anchors.verticalCenter: parent.verticalCenter
                                Text { visible: index > 0; text: " / "; color: Theme.far; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                Rectangle {
                                    width: crumbText.implicitWidth + 12; height: 26; radius: 6
                                    color: crumbMouse.containsMouse ? Qt.alpha(Theme.ice, 0.08) : "transparent"
                                    Text {
                                        id: crumbText
                                        anchors.centerIn: parent
                                        text: modelData.name
                                        color: index === crumbs.parts.length - 1 ? Theme.ice : Theme.muted
                                        font.pixelSize: 13; font.family: Theme.family
                                        font.weight: index === crumbs.parts.length - 1 ? Font.DemiBold : Font.Normal
                                    }
                                    MouseArea { id: crumbMouse; anchors.fill: parent; hoverEnabled: true; onClicked: win.go(modelData.path) }
                                }
                            }
                        }
                    }
                }
                TextField {
                    id: pathEdit
                    visible: false
                    anchors { fill: parent; leftMargin: 4; rightMargin: 4 }
                    text: win.inTrash ? "" : win.path
                    color: Theme.ice; font.pixelSize: 13; font.family: Theme.family
                    selectionColor: Theme.mid
                    background: null
                    onAccepted: { visible = false; win.go(text.replace(/^~/, win.places[0].path)) }
                    onActiveFocusChanged: if (!activeFocus) visible = false
                    Keys.onEscapePressed: { visible = false; view.forceActiveFocus() }
                }
            }

            // Search below the folder, as you type.
            Rectangle {
                Layout.preferredWidth: 220
                height: 34; radius: 8
                color: Theme.control
                border.width: searchField.activeFocus ? 1 : 0
                border.color: Theme.cyan
                Text { anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter } text: "⌕"; color: Theme.muted; font.pixelSize: 16 }
                TextField {
                    id: searchField
                    anchors { fill: parent; leftMargin: 26; rightMargin: 6 }
                    placeholderText: backend.tr("Search here")
                    placeholderTextColor: Theme.muted
                    color: Theme.ice; font.pixelSize: 13; font.family: Theme.family
                    selectionColor: Theme.mid
                    background: null
                    enabled: !win.inTrash
                    onTextChanged: searchTimer.restart()
                    Keys.onEscapePressed: { text = ""; view.forceActiveFocus() }
                    Keys.onDownPressed: view.forceActiveFocus()
                }
                Timer {
                    id: searchTimer
                    interval: 300
                    onTriggered: {
                        win.query = searchField.text.trim()
                        win.searching = win.query.length > 0
                        win.selected = ({}); win.current = -1
                        if (win.searching) win.call("search", "search", [win.path, win.query, win.hidden])
                        else win.shown = win.entries
                    }
                }
            }
            ToolIcon { glyph: win.grid ? "☰" : "▦"; tip: win.grid ? backend.tr("List") : backend.tr("Icons"); onClicked: win.grid = !win.grid }
            ToolIcon { glyph: "⋯"; tip: backend.tr("More"); onClicked: moreMenu.popup() }
        }
    }

    // ---- menus in the OziOS look ----------------------------------------------------
    component OMenu: Menu {
        padding: 6
        background: Rectangle {
            implicitWidth: 230
            radius: 12
            color: Theme.raised
            border.width: 1
            border.color: Qt.alpha(Theme.ice, 0.10)
        }
    }
    component OItem: MenuItem {
        id: oi
        height: visible ? 32 : 0
        leftPadding: 12
        rightPadding: 12
        indicator: Text {
            x: oi.width - width - 12
            anchors.verticalCenter: parent.verticalCenter
            visible: oi.checkable && oi.checked
            text: "✓"; color: Theme.cyan; font.pixelSize: 13
        }
        contentItem: Text {
            text: oi.text
            color: oi.enabled ? Theme.ice : Qt.alpha(Theme.ice, 0.35)
            font.pixelSize: 13; font.family: Theme.family
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 7
            color: oi.highlighted && oi.enabled ? Qt.alpha(Theme.ice, 0.08) : "transparent"
        }
    }
    component OSep: MenuSeparator {
        height: visible ? 9 : 0
        padding: 0
        topPadding: 4; bottomPadding: 4
        contentItem: Rectangle { implicitHeight: 1; color: Qt.alpha(Theme.ice, 0.10) }
    }

    OMenu {
        id: moreMenu
        OItem { text: backend.tr("New folder"); enabled: win.writable && !win.inTrash; onTriggered: win.newFolder() }
        OItem { text: backend.tr("New text file"); enabled: win.writable && !win.inTrash; onTriggered: win.call("mkfile", "mkfile", [win.path, backend.tr("New text file") + ".txt"]) }
        OItem { text: backend.tr("Open a terminal here"); enabled: !win.inTrash; onTriggered: win.call("terminal", "terminal", [win.path]) }
        OSep {}
        OItem { text: backend.tr("Show hidden files"); checkable: true; checked: win.hidden; onTriggered: { win.hidden = !win.hidden; win.reload() } }
        OItem { text: backend.tr("Sort by name"); checkable: true; checked: win.sort === "name"; onTriggered: { win.sort = "name"; win.reload() } }
        OItem { text: backend.tr("Sort by date"); checkable: true; checked: win.sort === "modified"; onTriggered: { win.sort = "modified"; win.reload() } }
        OItem { text: backend.tr("Sort by size"); checkable: true; checked: win.sort === "size"; onTriggered: { win.sort = "size"; win.reload() } }
        OItem { text: backend.tr("Sort by type"); checkable: true; checked: win.sort === "type"; onTriggered: { win.sort = "type"; win.reload() } }
    }

    // ---- places ----------------------------------------------------------------------
    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 210
            color: Theme.raised
            Rectangle { anchors { top: parent.top; bottom: parent.bottom; right: parent.right } width: 1; color: Qt.alpha(Theme.ice, 0.07) }
            Flickable {
                anchors { fill: parent; margins: 8 }
                contentHeight: side.height
                clip: true
                Column {
                    id: side
                    width: parent.width
                    spacing: 1
                    component Place: Rectangle {
                        id: place
                        property string label
                        property string icon
                        property string target
                        property bool eject: false
                        property bool dim: false
                        signal picked()
                        signal ejected()
                        width: side.width; height: 34; radius: 8
                        readonly property bool here: target !== "" && win.path === target
                        color: here ? Qt.alpha(Theme.cyan, 0.16) : placeMouse.containsMouse ? Qt.alpha(Theme.ice, 0.06) : "transparent"
                        Image {
                            id: placeIcon
                            anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                            width: 18; height: 18; sourceSize: Qt.size(36, 36)
                            source: "image://icon/" + place.icon
                            opacity: place.dim ? 0.5 : 1
                        }
                        Text {
                            anchors { left: placeIcon.right; leftMargin: 10; right: ejectButton.left; verticalCenter: parent.verticalCenter }
                            text: place.label; elide: Text.ElideRight
                            color: place.here ? Theme.ice : place.dim ? Theme.muted : Theme.ice
                            font.pixelSize: 13; font.family: Theme.family
                            font.weight: place.here ? Font.DemiBold : Font.Normal
                        }
                        MouseArea { id: placeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: place.picked() }
                        // Drop files on a place to move them there (Ctrl: copy).
                        DropArea {
                            anchors.fill: parent
                            enabled: place.target !== "" && place.target !== "trash:" || place.target === "trash:"
                            onDropped: (drop) => {
                                const paths = backend.localPaths(drop.urls.map(u => u.toString()))
                                if (place.target === "trash:") win.call("trash", "trash", [paths])
                                else win.startTransfer(paths, place.target, !(drop.modifiers & Qt.ControlModifier))
                            }
                        }
                        Rectangle {
                            id: ejectButton
                            visible: place.eject
                            anchors { right: parent.right; rightMargin: 4; verticalCenter: parent.verticalCenter }
                            width: visible ? 26 : 0; height: 26; radius: 6
                            color: ejectMouse.containsMouse ? Qt.alpha(Theme.ice, 0.12) : "transparent"
                            Text { anchors.centerIn: parent; text: "⏏"; color: Theme.muted; font.pixelSize: 13 }
                            MouseArea { id: ejectMouse; anchors.fill: parent; hoverEnabled: true; onClicked: place.ejected() }
                            ToolTip.visible: ejectMouse.containsMouse
                            ToolTip.text: backend.tr("Safely remove")
                        }
                    }
                    Text { text: backend.tr("Places"); color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold; leftPadding: 10; topPadding: 4; bottomPadding: 6; font.family: Theme.family }
                    Repeater {
                        model: win.places
                        Place {
                            required property var modelData
                            label: modelData.name; icon: modelData.icon; target: modelData.path
                            onPicked: win.go(modelData.path)
                        }
                    }
                    Text { visible: win.drives.length > 0; text: backend.tr("Drives"); color: Theme.muted; font.pixelSize: 11; font.weight: Font.DemiBold; leftPadding: 10; topPadding: 14; bottomPadding: 6; font.family: Theme.family }
                    Repeater {
                        model: win.drives
                        Place {
                            required property var modelData
                            label: modelData.name; icon: modelData.icon; target: modelData.path
                            dim: !modelData.mounted
                            eject: modelData.mounted && modelData.removable
                            onPicked: modelData.mounted ? win.go(modelData.path) : win.call("mount", "mount", [modelData.device])
                            onEjected: { if (win.path.startsWith(modelData.path)) win.go(win.places[0].path); win.call("unmount", "unmount", [modelData.device]); win.say(backend.tr("You can unplug it when its light stops.")) }
                        }
                    }
                }
            }
        }

        // ---- the folder ------------------------------------------------------------------
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Trash: its own bar with what can be done there.
            Rectangle {
                id: trashBar
                visible: win.inTrash
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: visible ? 44 : 0
                color: Qt.alpha(Theme.ice, 0.03)
                RowLayout {
                    anchors { fill: parent; leftMargin: 16; rightMargin: 12 }
                    Text { Layout.fillWidth: true; text: win.shown.length ? backend.tr("Things here are deleted for good only when you empty the trash.") : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight; font.family: Theme.family }
                    OButton { text: backend.tr("Restore"); enabled: win.selection.length > 0; onClicked: win.call("restore", "restore", [win.selection.map(e => e.trashName)]) }
                    OButton { text: backend.tr("Empty the trash"); enabled: win.shown.length > 0; onClicked: confirmEmpty.open() }
                }
            }

            GridView {
                id: view
                anchors { left: parent.left; right: parent.right; top: trashBar.bottom; bottom: statusBar.top; margins: 8 }
                clip: true
                focus: true
                model: win.shown
                cellWidth: win.grid ? Math.floor(width / Math.max(1, Math.floor(width / 116))) : width
                cellHeight: win.grid ? 118 : 34
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                currentIndex: win.current
                highlightFollowsCurrentItem: false
                keyNavigationEnabled: false
                activeFocusOnTab: true

                readonly property int perRow: win.grid ? Math.max(1, Math.floor(width / cellWidth)) : 1
                Keys.onPressed: (ev) => {
                    const shift = ev.modifiers & Qt.ShiftModifier
                    const ctrl = ev.modifiers & Qt.ControlModifier
                    if (ev.key === Qt.Key_Right && win.grid) win.moveCurrent(1, shift)
                    else if (ev.key === Qt.Key_Left && win.grid) win.moveCurrent(-1, shift)
                    else if (ev.key === Qt.Key_Down) win.moveCurrent(view.perRow, shift)
                    else if (ev.key === Qt.Key_Up) win.moveCurrent(-view.perRow, shift)
                    else if (ev.key === Qt.Key_Home) win.moveCurrent(-win.shown.length, shift)
                    else if (ev.key === Qt.Key_End) win.moveCurrent(win.shown.length, shift)
                    else if (ev.key === Qt.Key_Return || ev.key === Qt.Key_Enter) { if (win.selection.length === 1) win.open(win.selection[0]) }
                    else if (ev.key === Qt.Key_Backspace) win.up()
                    else if (ev.key === Qt.Key_Delete && shift) { if (win.selection.length) confirmDelete.open() }
                    else if (ev.key === Qt.Key_Delete) win.toTrash()
                    else if (ev.key === Qt.Key_F2) win.startRename()
                    else if (ctrl && ev.key === Qt.Key_A) win.selectAll()
                    else if (ctrl && ev.key === Qt.Key_C) win.copy(false)
                    else if (ctrl && ev.key === Qt.Key_X) win.copy(true)
                    else if (ctrl && ev.key === Qt.Key_V) win.paste()
                    else if (ev.key === Qt.Key_Escape) win.selected = ({})
                    else if (ev.key === Qt.Key_Menu) { contextMenu.popup() }
                    else if (ev.text && !ctrl && ev.text.trim() !== "") {
                        // Typing jumps to the first name that starts that way.
                        const t = ev.text.toLowerCase()
                        const start = win.current + 1
                        for (let k = 0; k < win.shown.length; k++) {
                            const i = (start + k) % win.shown.length
                            if (win.shown[i].name.toLowerCase().startsWith(t)) { win.selectOnly(i); view.positionViewAtIndex(i, GridView.Contain); break }
                        }
                    } else return
                    ev.accepted = true
                }

                // A click on empty space clears the selection; right click there: the folder's menu.
                MouseArea {
                    anchors.fill: parent
                    z: -1
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onPressed: (ev) => {
                        view.forceActiveFocus()
                        win.selected = ({}); win.current = -1
                        if (ev.button === Qt.RightButton) contextMenu.popup()
                    }
                }

                // Files dropped in from other programs (or other windows) come here.
                DropArea {
                    anchors.fill: parent
                    z: -2
                    enabled: !win.inTrash && win.writable
                    onDropped: (drop) => {
                        // Dropped back where they already are: nothing to do.
                        const paths = backend.localPaths(drop.urls.map(u => u.toString()))
                                             .filter(p => p && p.substring(0, p.lastIndexOf("/")) !== win.path)
                        if (paths.length) win.startTransfer(paths, win.path, drop.proposedAction === Qt.MoveAction && !(drop.modifiers & Qt.ControlModifier))
                    }
                }

                delegate: Item {
                    id: cell
                    required property var modelData
                    required property int index
                    width: view.cellWidth
                    height: view.cellHeight
                    readonly property bool isSelected: !!win.selected[modelData.path]
                    readonly property bool isRenaming: win.renaming === modelData.path

                    Rectangle {
                        id: card
                        anchors { fill: parent; margins: win.grid ? 4 : 1 }
                        radius: 8
                        color: cell.isSelected ? Qt.alpha(Theme.cyan, 0.20)
                             : cellMouse.containsMouse ? Qt.alpha(Theme.ice, 0.06) : "transparent"
                        border.width: index === win.current && view.activeFocus ? 1 : 0
                        border.color: Qt.alpha(Theme.cyan, 0.6)

                        // Icon or picture.
                        Item {
                            id: thumb
                            width: win.grid ? 64 : 22; height: width
                            x: win.grid ? (parent.width - width) / 2 : 10
                            y: win.grid ? 8 : (parent.height - height) / 2
                            Image {
                                anchors.fill: parent
                                visible: !cell.modelData.preview || pic.status !== Image.Ready
                                source: win.iconUrl(cell.modelData)
                                sourceSize: Qt.size(128, 128)
                                asynchronous: true
                            }
                            Image {
                                id: pic
                                anchors.fill: parent
                                visible: cell.modelData.preview && status === Image.Ready
                                source: cell.modelData.preview ? "file://" + encodeURI(cell.modelData.path).replace(/#/g, "%23").replace(/\?/g, "%3F") : ""
                                sourceSize: Qt.size(win.grid ? 160 : 44, win.grid ? 160 : 44)
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: true
                            }
                            Text {   // links get a small arrow
                                visible: cell.modelData.link
                                anchors { left: parent.left; bottom: parent.bottom }
                                text: "↗"; color: Theme.ice; font.pixelSize: win.grid ? 14 : 9
                                style: Text.Outline; styleColor: Theme.ink
                            }
                        }

                        Text {
                            id: nameText
                            visible: !cell.isRenaming
                            x: win.grid ? 6 : thumb.x + thumb.width + 10
                            y: win.grid ? thumb.y + thumb.height + 6 : (parent.height - height) / 2
                            width: win.grid ? parent.width - 12 : parent.width * 0.5
                            text: cell.modelData.name
                            color: Theme.ice
                            font.pixelSize: win.grid ? 12 : 13; font.family: Theme.family
                            horizontalAlignment: win.grid ? Text.AlignHCenter : Text.AlignLeft
                            wrapMode: win.grid ? Text.Wrap : Text.NoWrap
                            maximumLineCount: win.grid ? (cell.isSelected ? 4 : 2) : 1
                            elide: win.grid ? Text.ElideRight : Text.ElideMiddle
                        }
                        // In the list: size and date.
                        Text {
                            visible: !win.grid
                            anchors { right: dateLabel.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
                            width: 80; horizontalAlignment: Text.AlignRight
                            text: cell.modelData.dir ? "" : cell.modelData.sizeText
                            color: Theme.muted; font.pixelSize: 12; font.family: Theme.family
                        }
                        Text {
                            id: dateLabel
                            visible: !win.grid
                            anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                            width: 110; horizontalAlignment: Text.AlignRight
                            text: backend.dateText(win.inTrash ? cell.modelData.deleted : cell.modelData.modified)
                            color: Theme.muted; font.pixelSize: 12; font.family: Theme.family
                        }

                        TextField {
                            id: renameField
                            visible: cell.isRenaming
                            x: win.grid ? 2 : nameText.x
                            y: win.grid ? nameText.y - 4 : (parent.height - height) / 2
                            width: win.grid ? parent.width - 4 : parent.width * 0.5
                            height: 28
                            text: cell.modelData.name
                            color: Theme.ice; font.pixelSize: 12; font.family: Theme.family
                            selectionColor: Theme.mid
                            horizontalAlignment: win.grid ? Text.AlignHCenter : Text.AlignLeft
                            background: Rectangle { radius: 6; color: Theme.control; border.width: 1; border.color: Theme.cyan }
                            onVisibleChanged: if (visible) {
                                forceActiveFocus()
                                const dot = cell.modelData.dir ? -1 : text.lastIndexOf(".")
                                select(0, dot > 0 ? dot : text.length)
                            }
                            onAccepted: {
                                if (text !== cell.modelData.name) win.call("rename", "rename", [cell.modelData.path, text])
                                win.renaming = ""; view.forceActiveFocus()
                            }
                            Keys.onEscapePressed: { win.renaming = ""; view.forceActiveFocus() }
                            onActiveFocusChanged: if (!activeFocus && cell.isRenaming) win.renaming = ""
                        }
                    }

                    MouseArea {
                        id: cellMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                        enabled: !cell.isRenaming
                        drag.target: dragProxy
                        property bool moved: false
                        onPressed: (ev) => {
                            view.forceActiveFocus()
                            moved = false
                            if (ev.button === Qt.RightButton) {
                                if (!cell.isSelected) win.selectOnly(cell.index)
                                contextMenu.popup()
                            } else if (!cell.isSelected || (ev.modifiers & (Qt.ControlModifier | Qt.ShiftModifier))) {
                                win.clickAt(cell.index, ev.modifiers)
                            }
                        }
                        onReleased: (ev) => {
                            if (!moved && ev.button === Qt.LeftButton && !(ev.modifiers & (Qt.ControlModifier | Qt.ShiftModifier)) && cell.isSelected)
                                win.selectOnly(cell.index)
                            dragProxy.x = 0; dragProxy.y = 0
                        }
                        onPositionChanged: moved = true
                        onDoubleClicked: (ev) => { if (ev.button === Qt.LeftButton) win.open(cell.modelData) }
                        onClicked: (ev) => { if (ev.button === Qt.MiddleButton && cell.modelData.dir) win.go(cell.modelData.path) }
                    }
                    // Dragging the selection out: to another folder here, or to another program.
                    Item {
                        id: dragProxy
                        width: 1; height: 1
                        Drag.active: cellMouse.drag.active
                        Drag.dragType: Drag.Automatic
                        Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
                        Drag.proposedAction: Qt.MoveAction
                        Drag.mimeData: ({ "text/uri-list": backend.uriList(win.selectedPaths.length ? win.selectedPaths : [cell.modelData.path]) })
                        Drag.imageSource: win.iconUrl(cell.modelData)
                    }
                    // Folders take what is dropped on them.
                    DropArea {
                        anchors.fill: parent
                        enabled: cell.modelData.dir && !win.inTrash && !cell.isSelected
                        onEntered: (drag) => card.border.width = 2
                        onExited: card.border.width = 0
                        onDropped: (drop) => {
                            card.border.width = 0
                            const paths = backend.localPaths(drop.urls.map(u => u.toString()))
                            win.startTransfer(paths, cell.modelData.path, !(drop.modifiers & Qt.ControlModifier))
                        }
                    }
                }

                // An empty folder says so.
                Text {
                    anchors.centerIn: parent
                    visible: win.shown.length === 0
                    text: win.searching ? backend.tr("Nothing found.")
                          : win.inTrash ? backend.tr("The trash is empty.") : backend.tr("This folder is empty.")
                    color: Theme.muted; font.pixelSize: 14; font.family: Theme.family
                }
            }

            // ---- bottom: counts and free space, a copy in progress, messages --------------
            Rectangle {
                id: statusBar
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 30
                color: "transparent"
                Rectangle { anchors { left: parent.left; right: parent.right; top: parent.top } height: 1; color: Qt.alpha(Theme.ice, 0.06) }
                Text {
                    anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
                    text: win.message !== "" ? win.message
                         : win.selection.length > 0 ? backend.tr("{n} selected").replace("{n}", win.selection.length)
                                                      + (win.selection.length === 1 && !win.selection[0].dir ? " · " + win.selection[0].sizeText : "")
                         : backend.tr("{n} items").replace("{n}", win.shown.length)
                    color: win.message !== "" ? Theme.cyan : Theme.muted
                    font.pixelSize: 12; font.family: Theme.family
                }
                Row {
                    visible: win.progress >= 0
                    anchors { right: freeLabel.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
                    spacing: 8
                    Text { text: win.progressText; color: Theme.muted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    Rectangle {
                        width: 140; height: 6; radius: 3; color: Theme.control
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: parent.width * Math.max(0.02, win.progress); height: parent.height; radius: 3; color: Theme.cyan }
                    }
                }
                Text {
                    id: freeLabel
                    anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    text: win.freeText ? backend.tr("{size} free").replace("{size}", win.freeText) : ""
                    color: Theme.muted; font.pixelSize: 12; font.family: Theme.family
                }
            }
        }
    }

    // ---- the right-click menu ----------------------------------------------------------
    OMenu {
        id: contextMenu
        readonly property var one: win.selection.length === 1 ? win.selection[0] : null
        readonly property bool any: win.selection.length > 0
        OItem { text: backend.tr("Open"); visible: contextMenu.one !== null && !win.inTrash; onTriggered: win.open(contextMenu.one) }
        OItem { text: backend.tr("Open with…"); visible: contextMenu.one !== null && !contextMenu.one.dir && !win.inTrash; onTriggered: { openWith.file = contextMenu.one.path; win.call("appsFor", "appsFor", [contextMenu.one.path]) } }
        OItem { text: backend.tr("Open a terminal here"); visible: !contextMenu.any && !win.inTrash || (contextMenu.one !== null && contextMenu.one.dir); onTriggered: win.call("terminal", "terminal", [contextMenu.one ? contextMenu.one.path : win.path]) }
        OSep { visible: !win.inTrash }
        OItem { text: backend.tr("Cut"); visible: contextMenu.any && !win.inTrash; onTriggered: win.copy(true) }
        OItem { text: backend.tr("Copy"); visible: contextMenu.any && !win.inTrash; onTriggered: win.copy(false) }
        OItem { text: backend.tr("Paste"); visible: !win.inTrash && win.writable; onTriggered: win.paste() }
        OItem { text: backend.tr("Rename"); visible: contextMenu.one !== null && !win.inTrash; onTriggered: win.startRename() }
        OItem { text: backend.tr("Unpack here"); visible: contextMenu.one !== null && contextMenu.one.archive && !win.inTrash; onTriggered: { win.progress = 0; win.progressText = backend.tr("Unpacking…"); win.call("extract", "extract", [contextMenu.one.path]) } }
        OItem { text: backend.tr("Pack as .zip"); visible: contextMenu.any && !win.inTrash; onTriggered: { win.progress = 0; win.progressText = backend.tr("Packing…"); win.call("compress", "compress", [win.selectedPaths]) } }
        OItem { text: backend.tr("New folder"); visible: !contextMenu.any && !win.inTrash && win.writable; onTriggered: win.newFolder() }
        OSep { visible: contextMenu.any }
        OItem { text: backend.tr("Restore"); visible: contextMenu.any && win.inTrash; onTriggered: win.call("restore", "restore", [win.selection.map(e => e.trashName)]) }
        OItem { text: win.inTrash ? backend.tr("Delete for good") : backend.tr("Move to the trash"); visible: contextMenu.any; onTriggered: win.toTrash() }
        OItem { text: backend.tr("Properties"); visible: contextMenu.one !== null && !win.inTrash || !contextMenu.any && !win.inTrash; onTriggered: { props.info = null; props.open(); win.call("properties", "properties", [contextMenu.one ? contextMenu.one.path : win.path]) } }
    }

    // ---- dialogs -------------------------------------------------------------------------
    component Sheet: Popup {
        id: sheet
        anchors.centerIn: Overlay.overlay
        modal: true
        padding: 20
        background: Rectangle { radius: 14; color: Theme.raised; border.width: 1; border.color: Qt.alpha(Theme.ice, 0.10) }
        Overlay.modal: Rectangle { color: Qt.alpha("black", 0.4) }
    }

    Sheet {
        id: confirmDelete
        width: 420
        contentItem: Column {
            spacing: 16
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.ice; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.family
                   text: backend.tr("Delete {n} for good?").replace("{n}", win.selection.length === 1 ? "“" + win.selection[0].name + "”" : win.selection.length) }
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: 13; font.family: Theme.family; text: backend.tr("This cannot be undone.") }
            Row {
                anchors.right: parent.right
                spacing: 8
                OButton { text: backend.tr("Cancel"); onClicked: confirmDelete.close() }
                OButton {
                    text: backend.tr("Delete"); primary: true
                    onClicked: {
                        if (win.inTrash) win.call("emptyTrash", "emptyTrash", [win.selection.map(e => e.trashName)])
                        else win.call("delete", "delete", [win.selectedPaths])
                        confirmDelete.close()
                    }
                }
            }
        }
    }

    Sheet {
        id: confirmEmpty
        width: 420
        contentItem: Column {
            spacing: 16
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.ice; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.family; text: backend.tr("Empty the trash?") }
            Text { width: parent.width; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: 13; font.family: Theme.family; text: backend.tr("Everything in it is deleted for good. This cannot be undone.") }
            Row {
                anchors.right: parent.right
                spacing: 8
                OButton { text: backend.tr("Cancel"); onClicked: confirmEmpty.close() }
                OButton { text: backend.tr("Empty the trash"); primary: true; onClicked: { win.call("emptyTrash", "emptyTrash", []); confirmEmpty.close() } }
            }
        }
    }

    Sheet {
        id: openWith
        width: 380
        property string file: ""
        property var apps: []
        contentItem: Column {
            spacing: 10
            Text { color: Theme.ice; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.family; text: backend.tr("Open with") }
            Text { visible: openWith.apps.length === 0; width: parent.width; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: 13; font.family: Theme.family
                   text: backend.tr("No installed program says it opens this kind of file. The Store can find one.") }
            ListView {
                width: parent.width
                height: Math.min(320, contentHeight)
                clip: true
                model: openWith.apps
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width; height: 40; radius: 8
                    color: appMouse.containsMouse ? Qt.alpha(Theme.ice, 0.07) : "transparent"
                    Image { id: appIcon; anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter } width: 24; height: 24; sourceSize: Qt.size(48, 48); source: "image://icon/" + modelData.icon + "|application-x-executable" }
                    Text { anchors { left: appIcon.right; leftMargin: 10; verticalCenter: parent.verticalCenter } text: modelData.name + (modelData["default"] ? "  ·  " + backend.tr("default") : ""); color: Theme.ice; font.pixelSize: 13; font.family: Theme.family }
                    MouseArea { id: appMouse; anchors.fill: parent; hoverEnabled: true; onClicked: { win.call("openWith", "openWith", [openWith.file, modelData.id, rememberBox.checked]); openWith.close() } }
                }
            }
            CheckBox {
                id: rememberBox
                visible: openWith.apps.length > 0
                text: backend.tr("Always open this kind of file with it")
                contentItem: Text { leftPadding: 28; text: rememberBox.text; color: Theme.ice; font.pixelSize: 12; font.family: Theme.family; verticalAlignment: Text.AlignVCenter }
            }
        }
    }

    Sheet {
        id: props
        width: 400
        property var info: null
        contentItem: Column {
            spacing: 8
            Row {
                spacing: 14
                Image { width: 48; height: 48; sourceSize: Qt.size(96, 96); source: props.info ? win.iconUrl(props.info) : "" }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { width: 300; elide: Text.ElideMiddle; color: Theme.ice; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.family; text: props.info ? props.info.name : backend.tr("Counting…") }
                    Text { color: Theme.muted; font.pixelSize: 12; font.family: Theme.family; text: props.info ? props.info.mime : "" }
                }
            }
            Repeater {
                model: props.info ? [
                    [backend.tr("Where"), props.info.path],
                    [backend.tr("Size"), props.info.totalText + (props.info.dir ? " · " + backend.tr("{n} items").replace("{n}", props.info.items) : "")],
                    [backend.tr("Changed"), backend.dateText(props.info.modified)],
                    [backend.tr("Owner"), props.info.owner + " · " + props.info.mode],
                ].concat(props.info.target ? [[backend.tr("Points to"), props.info.target]] : []) : []
                Row {
                    required property var modelData
                    spacing: 10
                    Text { width: 90; color: Theme.muted; font.pixelSize: 12; font.family: Theme.family; text: modelData[0] }
                    Text { width: 260; wrapMode: Text.WrapAnywhere; color: Theme.ice; font.pixelSize: 12; font.family: Theme.family; text: modelData[1] }
                }
            }
            CheckBox {
                id: execBox
                visible: props.info !== null && !props.info.dir
                checked: props.info !== null && props.info.executable
                text: backend.tr("May run as a program")
                contentItem: Text { leftPadding: 28; text: execBox.text; color: Theme.ice; font.pixelSize: 12; font.family: Theme.family; verticalAlignment: Text.AlignVCenter }
                onToggled: win.call("executable", "executable", [props.info.path, checked])
            }
            OButton { anchors.right: parent.right; text: backend.tr("Close"); onClicked: props.close() }
        }
    }
}
