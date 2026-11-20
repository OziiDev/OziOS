import QtQuick

// Stand-in for Kirigami.Icon. Real icon themes are not available outside
// Plasma, so a program's icon is drawn as a coloured tile with its initial;
// the OziOS mark is the real logo.
Item {
    id: icon

    property var source
    property bool active: false
    property bool selected: false
    property bool roundToIconSize: true
    property color color: "transparent"

    implicitWidth: 32
    implicitHeight: 32

    readonly property string name: String(source || "")
    readonly property var known: ({
        "firefox": ["#ff9500", "#e0245e", "F"], "org.kde.dolphin": ["#2fa8ff", "#1c6fd1", "D"],
        "org.kde.konsole": ["#3a4652", "#151b22", ">"], "steam": ["#1b5fa8", "#0b1d38", "S"],
        "discord": ["#7b8cff", "#5865f2", "D"], "systemsettings": ["#7f8c99", "#4f5b66", "⚙"],
        "ozi-store": ["#00e5ff", "#0098b0", "O"], "libreoffice-writer": ["#3fa9f5", "#0e5c99", "W"],
        "gimp": ["#9a8a6c", "#5c4f3a", "G"], "vlc": ["#ff8800", "#cc5500", "V"],
        "thunderbird": ["#3a8ee6", "#1b3f8f", "T"], "kate": ["#5fb5ff", "#2c6fb5", "K"],
        "lock": ["#7f8c99", "#4f5b66", "🔒"], "system-log-out": ["#7f8c99", "#4f5b66", "⇥"],
        "system-reboot": ["#7f8c99", "#4f5b66", "↻"], "system-shutdown": ["#ff556e", "#b3243b", "⏻"]
    })
    function hash(text) {
        let h = 0
        for (let i = 0; i < text.length; i++)
            h = (h * 31 + text.charCodeAt(i)) % 360
        return h
    }
    readonly property var look: known[name] || [Qt.hsla(hash(name) / 360, 0.55, 0.55, 1), Qt.hsla(hash(name) / 360, 0.6, 0.35, 1),
                                                 name.length ? name.replace(/^.*[.-]/, "").charAt(0).toUpperCase() : "?"]

    Rectangle {
        anchors.fill: parent
        anchors.margins: Math.round(parent.width * 0.06)
        radius: width * 0.26
        visible: !logo.visible
        gradient: Gradient {
            GradientStop { position: 0; color: icon.look[0] }
            GradientStop { position: 1; color: icon.look[1] }
        }
        Text {
            anchors.centerIn: parent
            text: icon.look[2]
            color: "white"
            font.pixelSize: Math.max(6, parent.height * 0.48)
            font.bold: true
        }
    }
    Image {
        id: logo
        anchors.fill: parent
        source: icon.name === "ozios" ? Qt.resolvedUrl("../../../branding/logo.svg") : ""
        sourceSize.width: width
        sourceSize.height: height
        visible: status === Image.Ready
    }
}
