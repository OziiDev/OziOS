import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import OziUi

ApplicationWindow {
    id: window
    width: 1040
    height: 680
    minimumWidth: 760
    minimumHeight: 520
    visible: true
    title: "Software"
    color: Theme.ink

    // ---- state -------------------------------------------------------
    property var review: null            // result of the last review
    property string reviewPath: ""
    property var wanted: ({})            // permissions chosen on the review screen
    property var apps: []
    property var repoResults: []
    property var aurResults: []
    property string busyTask: ""         // empty when idle
    property string logText: ""
    property string message: ""
    property bool messageIsError: false

    function run(task, name, args) {
        busyTask = task
        message = ""
        backend.call(task, name, JSON.stringify(args || []))
    }

    function appendLog(line) {
        logText += line + "\n"
    }

    function startReview(path) {
        reviewPath = backend.fileFromUrl(path)
        review = null
        logText = ""
        pages.currentIndex = 0
        run("review", "review", [reviewPath])
    }

    function setWanted(key, value) {
        var copy = JSON.parse(JSON.stringify(wanted))
        copy[key] = value
        wanted = copy
    }

    Connections {
        target: backend

        function onLog(task, line) {
            window.appendLog(line)
        }

        function onDone(task, json) {
            var result = JSON.parse(json)
            window.busyTask = ""
            if (task === "review") {
                window.review = result
                window.wanted = result.permissions
            } else if (task === "install") {
                window.message = backend.tr("Installed.")
                window.messageIsError = false
                window.run("apps", "apps", [])
            } else if (task === "apps") {
                window.apps = result
            } else if (task === "remove") {
                window.run("apps", "apps", [])
            } else if (task === "repoSearch") {
                window.repoResults = result
            } else if (task === "aurSearch") {
                window.aurResults = result
            } else if (task === "getRepo" || task === "getAur" || task === "update") {
                window.message = backend.tr("Done.")
                window.messageIsError = false
            } else if (task === "setPermissions") {
                window.run("apps", "apps", [])
            }
        }

        function onFailed(task, text) {
            window.busyTask = ""
            window.message = text
            window.messageIsError = true
        }
    }

    Component.onCompleted: {
        var file = backend.startFile()
        if (file !== "") startReview(file)
        else run("apps", "apps", [])
    }

    FileDialog {
        id: chooser
        title: backend.tr("Choose a package")
        nameFilters: [backend.tr("Packages (*.deb *.pkg.tar.zst *.pkg.tar.xz *.AppImage)"), backend.tr("All files (*)")]
        onAccepted: window.startReview(selectedFile.toString())
    }

    DropArea {
        anchors.fill: parent
        onDropped: function(drop) {
            if (drop.hasUrls) window.startReview(drop.urls[0].toString())
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---- sidebar --------------------------------------------------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 220
            color: Theme.raised

            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.far }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 4

                Text {
                    text: "Software"
                    color: Theme.cyan
                    font.family: Theme.family
                    font.pixelSize: 22
                    Layout.bottomMargin: 16
                }

                Repeater {
                    model: [backend.tr("Install a file"), backend.tr("Find software"), backend.tr("My apps"), backend.tr("Updates")]
                    delegate: ItemDelegate {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: 40
                        highlighted: pages.currentIndex === index
                        onClicked: {
                            pages.currentIndex = index
                            if (index === 2) window.run("apps", "apps", [])
                        }
                        contentItem: Text {
                            text: modelData
                            color: pages.currentIndex === index ? Theme.cyan : Theme.ice
                            font.family: Theme.family
                            font.pixelSize: 15
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            radius: 4
                            color: parent.hovered ? Theme.control : "transparent"
                            Rectangle {
                                visible: pages.currentIndex === index
                                width: 2; height: parent.height - 12; x: 0; y: 6
                                color: Theme.cyan
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 12
                    text: backend.tr("A review checks for known bad patterns. A package that passes can still be harmful.")
                }
            }
        }

        // ---- pages ----------------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: window.message === "" ? 0 : 44
                visible: window.message !== ""
                color: window.messageIsError ? Qt.rgba(1, 0.33, 0.43, 0.12) : Qt.rgba(0.24, 0.9, 0.63, 0.12)
                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 24
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: window.message
                    color: window.messageIsError ? Theme.danger : Theme.good
                    font.family: Theme.family
                    font.pixelSize: 14
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true

                // 0: install a file -------------------------------------
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Card {
                            visible: window.review === null
                            Layout.fillWidth: true
                            Layout.fillHeight: window.review === null
                            emphasis: true

                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 12
                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: window.busyTask === "review" ? backend.tr("Reading the package...") : backend.tr("Drop a package here")
                                    color: Theme.ice
                                    font.family: Theme.family
                                    font.pixelSize: 22
                                }
                                Text {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: backend.tr(".deb files run in their own box. Arch packages are reviewed first.")
                                    color: Theme.muted
                                    font.family: Theme.family
                                    font.pixelSize: 14
                                }
                                OButton {
                                    Layout.alignment: Qt.AlignHCenter
                                    text: backend.tr("Choose a file...")
                                    primary: true
                                    onClicked: chooser.open()
                                }
                            }
                        }

                        // the review
                        RowLayout {
                            visible: window.review !== null
                            Layout.fillWidth: true
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: window.review ? window.review.name + "  " + window.review.version : ""
                                    color: Theme.ice
                                    font.family: Theme.family
                                    font.pixelSize: 24
                                }
                                Text {
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    text: window.review ? window.review.description : ""
                                    color: Theme.muted
                                    font.family: Theme.family
                                    font.pixelSize: 14
                                }
                            }
                            Chip {
                                text: window.review ? (window.review.boxed ? backend.tr("Runs in a box") : backend.tr("Installs on the system")) : ""
                                tone: window.review && window.review.boxed ? Theme.good : Theme.caution
                            }
                            Chip {
                                text: !window.review ? "" : window.review.verdict === "danger" ? backend.tr("Dangerous")
                                    : window.review.verdict === "look" ? backend.tr("Look closely") : backend.tr("Nothing known-bad")
                                tone: window.review ? Theme.verdictColor(window.review.verdict) : Theme.muted
                            }
                        }

                        RowLayout {
                            visible: window.review !== null
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 16

                            Card {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.preferredWidth: 3
                                ListView {
                                    anchors.fill: parent
                                    clip: true
                                    spacing: 10
                                    model: window.review ? window.review.findings : []
                                    header: Text {
                                        height: count === 0 ? 40 : 0
                                        visible: count === 0
                                        text: backend.tr("Nothing known-bad was found.")
                                        color: Theme.good
                                        font.family: Theme.family
                                        font.pixelSize: 15
                                    }
                                    ScrollBar.vertical: ScrollBar {}
                                    delegate: ColumnLayout {
                                        required property var modelData
                                        width: ListView.view.width - 12
                                        spacing: 2
                                        RowLayout {
                                            spacing: 8
                                            Chip { text: modelData.severity; tone: Theme.severityColor(modelData.severity) }
                                            Text {
                                                Layout.fillWidth: true
                                                wrapMode: Text.WordWrap
                                                text: modelData.title
                                                color: Theme.ice
                                                font.family: Theme.family
                                                font.pixelSize: 15
                                            }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: modelData.detail !== ""
                                            wrapMode: Text.WordWrap
                                            text: modelData.detail
                                            color: Theme.muted
                                            font.family: Theme.family
                                            font.pixelSize: 13
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: modelData.evidence !== ""
                                            elide: Text.ElideRight
                                            text: modelData.where + ": " + modelData.evidence
                                            color: Theme.mid
                                            font.family: Theme.mono
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }

                            Card {
                                Layout.fillHeight: true
                                Layout.preferredWidth: 280
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 4
                                    Text {
                                        text: window.review && window.review.boxed ? backend.tr("What it may reach") : backend.tr("Full system rights")
                                        color: Theme.ice
                                        font.family: Theme.family
                                        font.pixelSize: 16
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        visible: window.review && !window.review.boxed
                                        text: backend.tr("This package is installed on the system itself. Its install scripts run as the administrator.")
                                        color: Theme.muted
                                        font.family: Theme.family
                                        font.pixelSize: 13
                                    }
                                    Repeater {
                                        model: window.review && window.review.boxed
                                            ? [["network", backend.tr("Internet")], ["gpu", backend.tr("Graphics acceleration")],
                                               ["sound", backend.tr("Sound and microphone")], ["camera", backend.tr("Camera")],
                                               ["devices", backend.tr("USB and other devices")]]
                                            : []
                                        delegate: OSwitch {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            text: modelData[1]
                                            checked: window.wanted[modelData[0]] === true
                                            onToggled: window.setWanted(modelData[0], checked)
                                        }
                                    }
                                    OSwitch {
                                        visible: window.review && window.review.boxed
                                        Layout.fillWidth: true
                                        text: backend.tr("Your whole home folder")
                                        checked: window.wanted.files === "home"
                                        onToggled: window.setWanted("files", checked ? "home" : "none")
                                    }
                                    Item { Layout.fillHeight: true }
                                }
                            }
                        }

                        ScrollView {
                            visible: window.logText !== ""
                            Layout.fillWidth: true
                            Layout.preferredHeight: 110
                            TextArea {
                                readOnly: true
                                text: window.logText
                                color: Theme.muted
                                font.family: Theme.mono
                                font.pixelSize: 12
                                background: Rectangle { color: Theme.raised; radius: 4 }
                            }
                        }

                        RowLayout {
                            visible: window.review !== null
                            Layout.fillWidth: true
                            OButton { text: backend.tr("Choose another"); onClicked: { window.review = null; window.logText = "" } }
                            Item { Layout.fillWidth: true }
                            BusyIndicator { running: window.busyTask === "install"; visible: running; implicitWidth: 28; implicitHeight: 28 }
                            OButton {
                                primary: true
                                enabled: window.review !== null && window.review.installable && window.busyTask === ""
                                text: window.busyTask === "install" ? backend.tr("Installing...") : backend.tr("Install")
                                onClicked: {
                                    window.logText = ""
                                    window.run("install", "install", [window.reviewPath, window.wanted, false])
                                }
                            }
                        }
                    }
                }

                // 1: find software --------------------------------------
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            TextField {
                                id: term
                                Layout.fillWidth: true
                                placeholderText: backend.tr("Search for software")
                                color: Theme.ice
                                placeholderTextColor: Theme.muted
                                font.family: Theme.family
                                font.pixelSize: 15
                                background: Rectangle { color: Theme.control; radius: 4; border.width: 1; border.color: term.activeFocus ? Theme.cyan : Theme.far }
                                onAccepted: search.clicked()
                            }
                            OButton {
                                id: search
                                text: backend.tr("Search")
                                primary: true
                                enabled: term.text.trim() !== "" && window.busyTask === ""
                                onClicked: {
                                    window.run("repoSearch", "searchRepos", [term.text])
                                    backend.call("aurSearch", "searchAur", JSON.stringify([term.text]))
                                }
                            }
                        }

                        TabBar {
                            id: sources
                            Layout.fillWidth: true
                            background: Rectangle { color: "transparent" }
                            Repeater {
                                model: [backend.tr("Repositories"), backend.tr("AUR (community recipes)")]
                                delegate: TabButton {
                                    required property string modelData
                                    text: modelData
                                    contentItem: Text {
                                        text: parent.text
                                        color: parent.checked ? Theme.cyan : Theme.muted
                                        font.family: Theme.family
                                        font.pixelSize: 14
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                    background: Rectangle {
                                        color: "transparent"
                                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; color: parent.parent.checked ? Theme.cyan : Theme.far }
                                    }
                                }
                            }
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: sources.currentIndex === 0 ? window.repoResults : window.aurResults
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Card {
                                required property var modelData
                                width: ListView.view.width - 12
                                height: 64
                                RowLayout {
                                    anchors.fill: parent
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Text {
                                            text: modelData.name + "  " + modelData.version
                                            color: Theme.ice
                                            font.family: Theme.family
                                            font.pixelSize: 15
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                            text: modelData.description
                                            color: Theme.muted
                                            font.family: Theme.family
                                            font.pixelSize: 13
                                        }
                                    }
                                    OButton {
                                        text: modelData.installed ? backend.tr("Installed") : backend.tr("Install")
                                        enabled: !modelData.installed && window.busyTask === ""
                                        onClicked: {
                                            window.logText = ""
                                            if (sources.currentIndex === 0) window.run("getRepo", "getRepo", [[modelData.name]])
                                            else window.run("getAur", "getAur", [[modelData.name], false])
                                        }
                                    }
                                }
                            }
                        }

                        ScrollView {
                            visible: window.logText !== "" && (window.busyTask === "getRepo" || window.busyTask === "getAur" || window.message !== "")
                            Layout.fillWidth: true
                            Layout.preferredHeight: 110
                            TextArea {
                                readOnly: true
                                text: window.logText
                                color: Theme.muted
                                font.family: Theme.mono
                                font.pixelSize: 12
                                background: Rectangle { color: Theme.raised; radius: 4 }
                            }
                        }
                    }
                }

                // 2: my apps --------------------------------------------
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        Text {
                            visible: window.apps.length === 0
                            text: backend.tr("No boxed apps yet. Install a .deb file to see it here.")
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 15
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 10
                            model: window.apps
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Card {
                                id: appCard
                                required property var modelData
                                width: ListView.view.width - 12
                                height: 150
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.name + "  " + modelData.version
                                            color: Theme.ice
                                            font.family: Theme.family
                                            font.pixelSize: 17
                                        }
                                        OButton { text: backend.tr("Open"); onClicked: window.run("run", "run", [modelData.id]) }
                                        OButton { text: backend.tr("Remove"); onClicked: window.run("remove", "remove", [modelData.id]) }
                                    }
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 16
                                        Repeater {
                                            model: [["network", backend.tr("Internet")], ["camera", backend.tr("Camera")], ["devices", backend.tr("Devices")], ["sound", backend.tr("Sound")]]
                                            delegate: OSwitch {
                                                required property var modelData
                                                property var appPermissions: appCard.modelData.permissions
                                                text: modelData[1]
                                                checked: appPermissions[modelData[0]] === true
                                                onToggled: {
                                                    var next = JSON.parse(JSON.stringify(appPermissions))
                                                    next[modelData[0]] = checked
                                                    window.run("setPermissions", "setPermissions", [appCard.modelData.id, next])
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // 3: updates --------------------------------------------
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16
                        Text {
                            text: backend.tr("System updates")
                            color: Theme.ice
                            font.family: Theme.family
                            font.pixelSize: 22
                        }
                        Text {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: backend.tr("A snapshot is taken first, so an update can be undone.")
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 14
                        }
                        OButton {
                            text: window.busyTask === "update" ? backend.tr("Updating...") : backend.tr("Update the system")
                            primary: true
                            enabled: window.busyTask === ""
                            onClicked: { window.logText = ""; window.run("update", "update", []) }
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            TextArea {
                                readOnly: true
                                text: window.logText
                                color: Theme.muted
                                font.family: Theme.mono
                                font.pixelSize: 12
                                background: Rectangle { color: Theme.raised; radius: 4 }
                            }
                        }
                    }
                }
            }
        }
    }
}
