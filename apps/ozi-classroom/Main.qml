import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

// Four small tools a teacher reaches for all day: pick a student, make groups,
// time an activity, and keep the class lists they depend on.
ApplicationWindow {
    id: window
    width: 1000
    height: 700
    minimumWidth: 760
    minimumHeight: 560
    visible: true
    title: backend.tr("Classroom")
    color: Theme.ink

    property var classes: []
    property string current: ""
    property var names: []
    property int left: 0
    property var groups: []
    property int groupCount: 4
    property string message: ""
    property bool messageGood: false
    property int tab: 0                      // 0 pick, 1 groups, 2 timer, 3 students
    property bool naming: false
    property bool confirmDelete: false
    readonly property bool hasClass: current !== ""
    readonly property var tabNames: [backend.tr("Pick"), backend.tr("Groups"), backend.tr("Timer"), backend.tr("Students")]

    Component.onCompleted: ask("classes", "classes", [])
    onNamesChanged: roster.text = names.join("\n")

    function ask(task, name, args) {
        backend.call(task, name, JSON.stringify(args))
    }

    function say(text, good) {
        message = text
        messageGood = good
    }

    function open(name) {
        current = name
        names = []
        groups = []
        left = 0
        picker.shown = ""
        confirmDelete = false
        if (name !== "")
            ask("load", "load", [name])
    }

    function take(r) {
        current = r.name
        names = r.names
        left = r.names.length - r.picked.length
    }

    function createClass(name) {
        name = name.trim()
        if (name === "")
            return
        say("", false)
        ask("created", "save", [name, ""])
    }

    // What the buttons and the Space key do; also how the app is driven from a script.
    function pickStudent() { picker.start() }
    function chooseTime(seconds) { clock.choose(seconds) }
    function toggleTimer() { clock.toggle() }
    function resetTimer() { clock.reset() }

    Connections {
        target: backend
        function onDone(task, json) {
            var r = JSON.parse(json)
            if (task === "classes" || task === "delete") {
                window.classes = r.classes
                if (window.classes.indexOf(window.current) < 0)
                    window.open(window.classes.length > 0 ? window.classes[0] : "")
            } else if (task === "load" || task === "reset") {
                window.take(r)
            } else if (task === "save") {
                window.take(r)
                window.say(backend.tr("Saved"), true)
            } else if (task === "created") {
                window.naming = false
                nameField.text = ""
                window.groups = []
                picker.shown = ""
                window.take(r)
                window.tab = 3
                window.ask("classes", "classes", [])
            } else if (task === "pick") {
                picker.result = r
            } else if (task === "groups") {
                window.groups = r.groups
            }
        }
        function onFailed(task, text) {
            if (task === "pick") {
                roll.stop()
                picker.rolling = false
            }
            window.say(text, false)
        }
    }

    // The student being picked: names roll past for a moment, then one stays.
    QtObject {
        id: picker
        property string shown: ""
        property bool rolling: false
        property var result: null
        property int ticks: 0

        function start() {
            if (rolling || window.names.length === 0)
                return
            rolling = true
            result = null
            ticks = 0
            window.say("", false)
            window.ask("pick", "pick", [window.current])
            roll.start()
        }
    }

    Timer {
        id: roll
        interval: 70
        repeat: true
        onTriggered: {
            picker.ticks += 1
            if (picker.result !== null && picker.ticks >= 12) {
                stop()
                picker.shown = picker.result.student
                window.left = picker.result.left
                picker.rolling = false
                return
            }
            picker.shown = window.names[Math.floor(Math.random() * window.names.length)]
        }
    }

    // The countdown. It works from the clock, not from counting ticks, so a
    // busy computer cannot make a minute last longer.
    QtObject {
        id: clock
        property int total: 300                 // seconds chosen
        property real remaining: 300000         // milliseconds left
        property real endsAt: 0
        property bool running: false
        property bool finished: false
        readonly property string label: {
            var s = Math.ceil(remaining / 1000)
            var m = Math.floor(s / 60)
            var r = s % 60
            return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r
        }

        function choose(seconds) {
            total = Math.max(60, Math.min(180 * 60, seconds))
            reset()
        }
        function reset() {
            tick.stop()
            running = false
            finished = false
            remaining = total * 1000
        }
        function toggle() {
            if (running) {
                remaining = Math.max(0, endsAt - Date.now())
                running = false
                tick.stop()
                return
            }
            if (finished)
                reset()
            endsAt = Date.now() + remaining
            running = true
            tick.start()
        }
    }

    Timer {
        id: tick
        interval: 200
        repeat: true
        onTriggered: {
            clock.remaining = Math.max(0, clock.endsAt - Date.now())
            if (clock.remaining === 0) {
                stop()
                clock.running = false
                clock.finished = true
                window.ask("ding", "ding", [])
            }
        }
    }

    Timer {
        id: forgetDelete
        interval: 4000
        onTriggered: window.confirmDelete = false
    }

    Shortcut {
        sequence: "Space"
        enabled: window.hasClass && !window.naming && (window.tab === 0 || window.tab === 2)
        onActivated: window.tab === 0 ? window.pickStudent() : window.toggleTimer()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Text {
                text: backend.tr("Classroom")
                color: Theme.ice
                font.family: Theme.family
                font.pixelSize: 28
            }
            Item { Layout.fillWidth: true }
            OButton {
                text: backend.tr("New class")
                visible: window.classes.length > 0 && !window.naming
                onClicked: {
                    window.naming = true
                    nameField.forceActiveFocus()
                }
            }
        }

        // The classes: one chip each.
        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: window.classes.length > 0
            Repeater {
                model: window.classes
                Rectangle {
                    id: chip
                    required property string modelData
                    readonly property bool active: modelData === window.current
                    width: chipLabel.implicitWidth + 28
                    height: 36
                    radius: 4
                    color: active ? Theme.control : "transparent"
                    border.width: 1
                    border.color: active ? Theme.cyan : (chipHover.hovered ? Theme.mid : Theme.far)
                    Text {
                        id: chipLabel
                        anchors.centerIn: parent
                        text: chip.modelData
                        color: chip.active ? Theme.cyan : Theme.ice
                        font.family: Theme.family
                        font.pixelSize: 15
                    }
                    HoverHandler { id: chipHover }
                    TapHandler { onTapped: window.open(chip.modelData) }
                }
            }
        }

        // Making a class: shown on the first start and after "New class".
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            visible: window.naming || window.classes.length === 0
            TextField {
                id: nameField
                Layout.preferredWidth: 300
                implicitHeight: 40
                placeholderText: backend.tr("Class name, for example 5-A")
                placeholderTextColor: Theme.muted
                color: Theme.ice
                selectionColor: Theme.mid
                font.family: Theme.family
                font.pixelSize: 16
                leftPadding: 12
                selectByMouse: true
                background: Rectangle {
                    radius: 4
                    color: Theme.control
                    border.width: 1
                    border.color: nameField.activeFocus ? Theme.cyan : Theme.far
                }
                onAccepted: window.createClass(text)
            }
            OButton {
                text: backend.tr("Create")
                primary: true
                implicitHeight: 40
                enabled: nameField.text.trim() !== ""
                onClicked: window.createClass(nameField.text)
            }
            OButton {
                text: backend.tr("Cancel")
                implicitHeight: 40
                visible: window.classes.length > 0
                onClicked: {
                    window.naming = false
                    nameField.text = ""
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: window.classes.length === 0
            wrapMode: Text.WordWrap
            text: backend.tr("Start with your first class. You can add the students next.")
            color: Theme.muted
            font.family: Theme.family
            font.pixelSize: 15
        }

        // The tabs.
        RowLayout {
            Layout.fillWidth: true
            visible: window.hasClass
            spacing: 4
            Repeater {
                model: window.tabNames
                Item {
                    id: tabItem
                    required property int index
                    required property string modelData
                    readonly property bool active: window.tab === index
                    Layout.preferredWidth: tabLabel.implicitWidth + 40
                    Layout.preferredHeight: 44
                    Text {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: tabItem.modelData
                        color: tabItem.active ? Theme.cyan : Theme.muted
                        font.family: Theme.family
                        font.pixelSize: 17
                    }
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 2
                        color: tabItem.active ? Theme.cyan : "transparent"
                    }
                    TapHandler { onTapped: window.tab = tabItem.index }
                }
            }
            Item { Layout.fillWidth: true }
        }

        StackLayout {
            visible: window.hasClass
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.tab

            // Pick a student.
            ColumnLayout {
                spacing: 16
                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    emphasis: true
                    Text {
                        anchors.fill: parent
                        visible: picker.shown === ""
                        text: window.names.length === 0 ? backend.tr("Add your students on the Students tab.")
                                                        : backend.tr("Press the button to pick a student.")
                        color: Theme.muted
                        font.family: Theme.family
                        font.pixelSize: 22
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    Text {
                        anchors.fill: parent
                        visible: picker.shown !== ""
                        text: picker.shown
                        color: picker.rolling ? Theme.mid : Theme.cyan
                        font.family: Theme.family
                        font.pixelSize: 120
                        fontSizeMode: Text.Fit
                        minimumPixelSize: 20
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    OButton {
                        text: backend.tr("Pick a student")
                        primary: true
                        implicitHeight: 52
                        leftPadding: 28
                        rightPadding: 28
                        font.pixelSize: 18
                        enabled: window.names.length > 0 && !picker.rolling
                        onClicked: window.pickStudent()
                    }
                    OButton {
                        text: backend.tr("New round")
                        implicitHeight: 52
                        enabled: window.names.length > 0 && !picker.rolling
                        onClicked: {
                            picker.shown = ""
                            window.ask("reset", "reset", [window.current])
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignRight
                        visible: window.names.length > 0
                        text: backend.tr("{n} left in this round").replace("{n}", window.left)
                        color: Theme.muted
                        font.family: Theme.family
                        font.pixelSize: 15
                    }
                }
            }

            // Groups.
            ColumnLayout {
                spacing: 16
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Text {
                        text: backend.tr("Number of groups")
                        color: Theme.ice
                        font.family: Theme.family
                        font.pixelSize: 16
                    }
                    OButton {
                        text: "−"
                        implicitWidth: 44
                        implicitHeight: 44
                        enabled: window.groupCount > 2
                        onClicked: window.groupCount -= 1
                    }
                    Text {
                        Layout.preferredWidth: 36
                        horizontalAlignment: Text.AlignHCenter
                        text: window.groupCount
                        color: Theme.cyan
                        font.family: Theme.family
                        font.pixelSize: 24
                    }
                    OButton {
                        text: "+"
                        implicitWidth: 44
                        implicitHeight: 44
                        enabled: window.groupCount < 12
                        onClicked: window.groupCount += 1
                    }
                    OButton {
                        text: backend.tr("Make groups")
                        primary: true
                        implicitHeight: 44
                        enabled: window.names.length > 1
                        onClicked: window.ask("groups", "groups", [window.current, window.groupCount])
                    }
                    Item { Layout.fillWidth: true }
                }
                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: width
                    contentHeight: groupFlow.implicitHeight
                    ScrollBar.vertical: ScrollBar {}
                    Flow {
                        id: groupFlow
                        width: parent.width
                        spacing: 12
                        Repeater {
                            model: window.groups
                            Card {
                                id: groupCard
                                required property var modelData
                                required property int index
                                readonly property var members: modelData
                                width: 230
                                height: 64 + members.length * 24
                                Column {
                                    anchors.fill: parent
                                    spacing: 4
                                    Text {
                                        text: backend.tr("Group {n}").replace("{n}", groupCard.index + 1)
                                        color: Theme.cyan
                                        font.family: Theme.family
                                        font.pixelSize: 18
                                    }
                                    Repeater {
                                        model: groupCard.members
                                        Text {
                                            required property string modelData
                                            text: modelData
                                            color: Theme.ice
                                            font.family: Theme.family
                                            font.pixelSize: 16
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Timer.
            ColumnLayout {
                spacing: 16
                Card {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    emphasis: true
                    Text {
                        id: clockText
                        property real pulse: 1
                        anchors.fill: parent
                        text: clock.finished ? backend.tr("Time is up") : clock.label
                        color: clock.finished ? Theme.caution : (clock.running ? Theme.cyan : Theme.ice)
                        opacity: clock.finished ? pulse : 1
                        font.family: Theme.mono
                        font.pixelSize: 220
                        fontSizeMode: Text.Fit
                        minimumPixelSize: 40
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        SequentialAnimation on pulse {
                            running: clock.finished
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.35; duration: 500 }
                            NumberAnimation { to: 1; duration: 500 }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: [1, 3, 5, 10, 15, 30]
                        OButton {
                            required property int modelData
                            text: backend.tr("{n} min").replace("{n}", modelData)
                            implicitHeight: 48
                            enabled: !clock.running
                            onClicked: window.chooseTime(modelData * 60)
                        }
                    }
                    OButton {
                        text: "−"
                        implicitWidth: 48
                        implicitHeight: 48
                        enabled: !clock.running && clock.total > 60
                        onClicked: window.chooseTime(clock.total - 60)
                    }
                    OButton {
                        text: "+"
                        implicitWidth: 48
                        implicitHeight: 48
                        enabled: !clock.running
                        onClicked: window.chooseTime(clock.total + 60)
                    }
                    Item { Layout.fillWidth: true }
                    OButton {
                        text: clock.running ? backend.tr("Pause") : backend.tr("Start")
                        primary: true
                        implicitHeight: 48
                        leftPadding: 28
                        rightPadding: 28
                        onClicked: window.toggleTimer()
                    }
                    OButton {
                        text: backend.tr("Reset")
                        implicitHeight: 48
                        onClicked: window.resetTimer()
                    }
                }
            }

            // Students.
            ColumnLayout {
                spacing: 12
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: backend.tr("One name per line. Lines that start with # are ignored.")
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 15
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 4
                    color: Theme.control
                    border.width: 1
                    border.color: roster.activeFocus ? Theme.cyan : Theme.far
                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 2
                        TextArea {
                            id: roster
                            color: Theme.ice
                            selectionColor: Theme.mid
                            font.family: Theme.family
                            font.pixelSize: 18
                            padding: 12
                            selectByMouse: true
                            background: null
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    OButton {
                        text: backend.tr("Save")
                        primary: true
                        implicitHeight: 44
                        onClicked: window.ask("save", "save", [window.current, roster.text])
                    }
                    OButton {
                        text: window.confirmDelete ? backend.tr("Really delete?") : backend.tr("Delete class")
                        implicitHeight: 44
                        onClicked: {
                            if (window.confirmDelete) {
                                window.confirmDelete = false
                                window.ask("delete", "delete", [window.current])
                            } else {
                                window.confirmDelete = true
                                forgetDelete.restart()
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignRight
                        text: backend.tr("{n} students").replace("{n}", window.names.length)
                        color: Theme.muted
                        font.family: Theme.family
                        font.pixelSize: 15
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
            visible: !window.hasClass
        }

        Text {
            Layout.fillWidth: true
            visible: text !== ""
            wrapMode: Text.WordWrap
            text: window.message
            color: window.messageGood ? Theme.good : Theme.caution
            font.family: Theme.family
            font.pixelSize: 14
        }
    }
}
