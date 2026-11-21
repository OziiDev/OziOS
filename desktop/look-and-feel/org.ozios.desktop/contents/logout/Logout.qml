import QtQuick
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.coreaddons as KCoreAddons
import org.kde.plasma.private.sessions

import "keys.js" as Shared

// The screen to lock, sleep, restart, shut down or log out. Plasma's logout greeter
// loads it from the look-and-feel package, sets the context it reads (sdtype, maysd,
// canLogout, spdMethods, softwareUpdatePending, ...) and acts on the signals below.
//
// The desktop dims to ink with a soft glow of the theme's two colours, the time and a
// goodbye come down from above, and the tiles rise in one after another. The arrows and
// Enter choose, Esc or a click beside the tiles goes back. When a program asked for one
// thing, a restart say, that tile is offered alone and counts down, then acts; any key
// stops the count.
Item {
    id: root
    width: screenGeometry.width
    height: screenGeometry.height

    signal logoutRequested()
    signal haltRequested()
    signal haltUpdateRequested()
    signal suspendRequested(int spdMethod)
    signal rebootRequested()
    signal rebootRequested2(int opt)
    signal rebootUpdateRequested()
    signal cancelRequested()
    signal lockScreenRequested()
    signal cancelSoftwareUpdateRequested()

    readonly property bool turkish: Qt.locale().name.indexOf("tr") === 0
    function tx(english, turkish) {
        return root.turkish ? turkish : english
    }

    readonly property color ink: "#080B10"
    readonly property color paper: "#F4FCFF"
    readonly property color accent: Kirigami.Theme.highlightColor
    // The accent's partner, as in the window frames' glow and the bar.
    readonly property color accent2: {
        const hue = Math.max(0, accent.hsvHue) * 360
        const d = ((270 - hue + 540) % 360) - 180
        const shift = Math.abs(d) < 20 ? 40 : Math.sign(d) * Math.min(Math.abs(d), 70)
        return Qt.hsva((((hue + shift) % 360) + 360) % 360 / 360, accent.hsvSaturation, accent.hsvValue, 1)
    }
    readonly property bool moving: Kirigami.Units.longDuration > 1

    property real timeout: 30
    property real remainingTime: timeout
    readonly property bool showAllOptions: sdtype === ShutdownType.ShutdownTypeDefault
    readonly property bool loggingOut: sdtype === ShutdownType.ShutdownTypeNone || sdtype === ShutdownType.ShutdownTypeLogout

    // What is offered, in order. A program that asked for one thing gets that alone.
    readonly property var choices: {
        const all = root.showAllOptions
        const list = []
        if (all)
            list.push({ key: "lock", glyph: "lock", title: tx("Lock", "Kilitle") })
        if (all && spdMethods.SuspendState)
            list.push({ key: "sleep", glyph: "sleep", title: tx("Sleep", "Uyku") })
        if (all && spdMethods.HibernateState)
            list.push({ key: "hibernate", glyph: "hibernate", title: tx("Hibernate", "Derin uyku") })
        if (maysd && (all || sdtype === ShutdownType.ShutdownTypeReboot)) {
            if (softwareUpdatePending)
                list.push({ key: "reboot-update", glyph: "restart", badge: true, title: tx("Update and restart", "Güncelle, yeniden başlat") })
            list.push({ key: "reboot", glyph: "restart", title: tx("Restart", "Yeniden başlat") })
        }
        if (maysd && (all || sdtype === ShutdownType.ShutdownTypeHalt)) {
            if (softwareUpdatePending)
                list.push({ key: "halt-update", glyph: "power", badge: true, title: tx("Update and shut down", "Güncelle ve kapat") })
            list.push({ key: "halt", glyph: "power", title: tx("Shut down", "Kapat") })
        }
        if (canLogout && (all || root.loggingOut))
            list.push({ key: "logout", glyph: "logout", title: tx("Log out", "Oturumu kapat") })
        return list
    }

    // What was asked for, and what the countdown does: shutting down when nothing was.
    readonly property string asked: {
        if (sdtype === ShutdownType.ShutdownTypeReboot)
            return softwareUpdatePending ? "reboot-update" : "reboot"
        if (root.loggingOut)
            return "logout"
        return softwareUpdatePending ? "halt-update" : "halt"
    }
    property int current: Math.max(0, choices.findIndex(choice => choice.key === root.asked))

    function act(key) {
        Shared.keyPressed()
        switch (key) {
        case "lock": root.lockScreenRequested(); break
        case "sleep": root.suspendRequested(2); break
        case "hibernate": root.suspendRequested(4); break
        case "reboot": root.rebootRequested(); break
        case "reboot-update": root.rebootUpdateRequested(); break
        case "halt": root.haltRequested(); break
        case "halt-update": root.haltUpdateRequested(); break
        case "logout": root.logoutRequested(); break
        }
    }

    function move(step) {
        if (root.choices.length > 0)
            root.current = (root.current + step + root.choices.length) % root.choices.length
    }

    onRemainingTimeChanged: {
        if (remainingTime <= 0)
            act(root.asked)
    }

    KCoreAddons.KUser {
        id: kuser
    }

    // For a word about other people who are logged in.
    SessionsModel {
        id: others
        includeUnusedSessions: false
        includeOwnSession: false
    }

    QQC2.Action {
        onTriggered: root.cancelRequested()
        shortcut: "Escape"
    }

    Timer {
        id: countDown
        running: !root.showAllOptions
        repeat: true
        interval: 1000
        onTriggered: root.remainingTime--
        Component.onCompleted: Shared.onKey(() => { countDown.running = false })
    }

    property date now: new Date()
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    focus: true
    Keys.onPressed: event => {
        Shared.keyPressed()
        switch (event.key) {
        case Qt.Key_Left:
        case Qt.Key_Up:
        case Qt.Key_Backtab:
            root.move(-1)
            event.accepted = true
            break
        case Qt.Key_Right:
        case Qt.Key_Down:
        case Qt.Key_Tab:
            root.move(1)
            event.accepted = true
            break
        case Qt.Key_Return:
        case Qt.Key_Enter:
        case Qt.Key_Space:
            if (root.choices.length > 0)
                root.act(root.choices[root.current].key)
            event.accepted = true
            break
        case Qt.Key_Escape:
            root.cancelRequested()
            event.accepted = true
            break
        }
    }

    // The dim, and the glow of the two colours in it.
    Rectangle {
        id: scrim
        anchors.fill: parent
        color: root.ink
        opacity: root.moving ? 0 : 0.86
        Component.onCompleted: opacity = 0.86
        Behavior on opacity { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
    }
    Canvas {
        id: glow
        anchors.fill: parent
        opacity: scrim.opacity / 0.86
        function rgba(c, alpha) {
            return "rgba(" + Math.round(c.r * 255) + "," + Math.round(c.g * 255) + "," + Math.round(c.b * 255) + "," + alpha + ")"
        }
        onPaint: {
            const c = getContext("2d")
            c.reset()
            const spots = [[0.36, 0.6, root.accent, 0.20], [0.66, 0.42, root.accent2, 0.16]]
            for (const [x, y, colour, alpha] of spots) {
                const r = Math.max(width, height) * 0.42
                const g = c.createRadialGradient(width * x, height * y, 0, width * x, height * y, r)
                g.addColorStop(0, rgba(colour, alpha))
                g.addColorStop(1, rgba(colour, 0))
                c.fillStyle = g
                c.fillRect(0, 0, width, height)
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }
    MouseArea {
        anchors.fill: parent
        onClicked: root.cancelRequested()
    }

    Column {
        id: content
        anchors.centerIn: parent
        spacing: Kirigami.Units.gridUnit * 2

        // The time, the day and a goodbye.
        Column {
            id: header
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Kirigami.Units.gridUnit * 0.3
            opacity: root.moving ? 0 : 1
            transform: Translate { id: drop; y: root.moving ? -Kirigami.Units.gridUnit : 0 }
            Component.onCompleted: {
                if (root.moving)
                    headerIn.start()
            }
            ParallelAnimation {
                id: headerIn
                NumberAnimation { target: header; property: "opacity"; to: 1; duration: 420; easing.type: Easing.OutCubic }
                NumberAnimation { target: drop; property: "y"; to: 0; duration: 520; easing.type: Easing.OutCubic }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Qt.formatTime(root.now, Qt.locale().timeFormat(Locale.ShortFormat))
                color: root.paper
                font.pixelSize: Math.round(Kirigami.Units.gridUnit * 4.4)
                font.weight: Font.Light
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.now.toLocaleDateString(Qt.locale(), "dddd, d MMMM")
                color: root.paper
                opacity: 0.72
                font.pixelSize: Math.round(Kirigami.Units.gridUnit * 1.05)
            }
            Item {
                width: 1
                height: Kirigami.Units.gridUnit * 0.8
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Kirigami.Units.gridUnit * 0.6

                Item {
                    id: avatar
                    width: Kirigami.Units.gridUnit * 2.2
                    height: width
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: root.accent }
                            GradientStop { position: 1; color: root.accent2 }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: greeting.person.charAt(0).toUpperCase()
                            color: root.ink
                            font.pixelSize: Math.round(parent.height * 0.48)
                            font.weight: Font.Bold
                        }
                    }
                    Kirigami.ShadowedImage {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: width / 2
                        source: kuser.faceIconUrl
                        visible: status === Image.Ready
                        fillMode: Image.PreserveAspectCrop
                    }
                }
                Text {
                    id: greeting
                    readonly property string person: kuser.fullName || kuser.loginName || "?"
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.tx("See you soon, %1", "Görüşmek üzere, %1").arg(person)
                    color: root.paper
                    font.pixelSize: Math.round(Kirigami.Units.gridUnit * 1.05)
                    font.weight: Font.Medium
                }
            }
        }

        Row {
            id: tiles
            objectName: "tiles"
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Kirigami.Units.gridUnit
            // narrow screens: smaller, not cut off
            scale: Math.min(1, (root.width - Kirigami.Units.gridUnit * 3) / Math.max(1, implicitWidth))

            Repeater {
                model: root.choices
                PowerTile {
                    objectName: "tile-" + modelData.key
                    glyph: modelData.glyph
                    title: modelData.title
                    badge: !!modelData.badge
                    order: index
                    current: index === root.current
                    accent: root.accent
                    accent2: root.accent2
                    progress: countDown.running && modelData.key === root.asked ? root.remainingTime / root.timeout : -1
                    onChosen: root.act(modelData.key)
                    onContainsMouseChanged: {
                        if (containsMouse)
                            root.current = index
                    }
                }
            }
        }

        // What is about to happen, and what to keep in mind.
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Kirigami.Units.smallSpacing
            width: Math.min(root.width - Kirigami.Units.gridUnit * 4, Kirigami.Units.gridUnit * 34)

            Repeater {
                model: {
                    const notes = []
                    if (countDown.running) {
                        const seconds = Math.max(0, Math.round(root.remainingTime))
                        switch (root.asked) {
                        case "reboot-update":
                            notes.push(tx("Installing updates and restarting in %1 s", "%1 saniye sonra güncellenip yeniden başlatılacak").arg(seconds))
                            break
                        case "reboot":
                            notes.push(tx("Restarting in %1 s", "%1 saniye sonra yeniden başlatılacak").arg(seconds))
                            break
                        case "logout":
                            notes.push(tx("Logging out in %1 s", "%1 saniye sonra oturum kapanacak").arg(seconds))
                            break
                        case "halt-update":
                            notes.push(tx("Installing updates and shutting down in %1 s", "%1 saniye sonra güncellenip kapanacak").arg(seconds))
                            break
                        default:
                            notes.push(tx("Shutting down in %1 s", "%1 saniye sonra kapanacak").arg(seconds))
                        }
                    }
                    if (others.count > 0 && !root.loggingOut)
                        notes.push(tx("%1 other people are logged in; shutting down or restarting may lose their work.",
                                      "%1 kişi daha oturum açmış; kapatmak ya da yeniden başlatmak onların işini kaybettirebilir.").arg(others.count))
                    if (rebootToFirmwareSetup)
                        notes.push(tx("On restart the computer opens its firmware settings.", "Yeniden başlarken bilgisayar donanım yazılımı ayarlarını açacak."))
                    if (rebootToBootLoaderMenu)
                        notes.push(tx("On restart the computer shows the boot menu.", "Yeniden başlarken bilgisayar önyükleme menüsünü gösterecek."))
                    if (rebootToBootLoaderEntry)
                        notes.push(tx("On restart the computer starts %1.", "Yeniden başlarken bilgisayar %1 ile açılacak.").arg(rebootToBootLoaderEntry))
                    return notes
                }
                Text {
                    objectName: "note"
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: modelData
                    color: root.paper
                    opacity: index === 0 && countDown.running ? 0.95 : 0.7
                    font.pixelSize: Math.round(Kirigami.Units.gridUnit * (index === 0 && countDown.running ? 0.95 : 0.8))
                }
            }
        }

        // Back to the desktop.
        MouseArea {
            id: cancel
            objectName: "cancel"
            anchors.horizontalCenter: parent.horizontalCenter
            width: cancelText.implicitWidth + Kirigami.Units.gridUnit * 2
            height: Kirigami.Units.gridUnit * 2
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.cancelRequested()
            Accessible.role: Accessible.Button
            Accessible.name: cancelText.text
            Rectangle {
                anchors.fill: parent
                radius: height / 2
                color: Qt.rgba(1, 1, 1, cancel.containsMouse ? 0.14 : 0.07)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.12)
                Behavior on color { ColorAnimation { duration: 150 } }
            }
            Text {
                id: cancelText
                anchors.centerIn: parent
                text: root.tx("Cancel", "Vazgeç") + "  ·  Esc"
                color: root.paper
                opacity: 0.85
                font.pixelSize: Math.round(Kirigami.Units.gridUnit * 0.78)
            }
        }
    }
}
