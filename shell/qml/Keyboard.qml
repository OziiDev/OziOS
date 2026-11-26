import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The on-screen keyboard: for smart boards and touch screens. It sits along
// the bottom and pushes the windows up while it is open, never takes the
// keyboard focus, and types through oziwm, so whatever the layout in use makes
// of a key is what the program gets. The keys come from that same layout
// (Shell.keyboard): Turkish Q on a Turkish system, Turkish F, German, US...
Window {
    id: kb
    property var shell
    readonly property var c: shell.c

    // Open by the bar's button or by itself when a text field is touched.
    property bool open: false
    property bool symbols: false
    property bool shift: false
    property bool caps: false
    property bool ctrl: false
    property real lastShiftTap: 0

    readonly property var board: Shell.keyboard
    readonly property var rows: board.rows || []
    readonly property int screenW: Screen.width > 0 ? Screen.width : 1366
    readonly property int screenH: Screen.height > 0 ? Screen.height : 768
    // Big enough for a finger, but not wider than an arm can reach on a
    // 65-inch board: about two thirds of a wide screen, all of a narrow one.
    readonly property int keyH: Math.max(44, Math.min(84, Math.round(Math.min(screenH * 0.066, screenW * 0.05))))
    readonly property int gap: Math.max(5, Math.round(keyH * 0.12))
    readonly property real unit: Math.min((width - 2 * pad - 13 * gap) / 14.5, keyH * 1.15)
    readonly property int pad: Math.round(gap * 1.6)
    readonly property bool upper: shift !== caps

    visible: false
    color: "transparent"
    width: screenW
    height: 5 * keyH + 4 * gap + 2 * pad
    LS.Window.scope: "ozi-keyboard"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: open ? height : 0
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityNone

    function show() { open = true; visible = true }
    function hide() { open = false; symbols = false; shift = false; ctrl = false }
    function toggle() { open ? hide() : show() }
    onOpenChanged: if (!open) closing.restart()
    Timer { id: closing; interval: kb.shell.ms(180); onTriggered: if (!kb.open) kb.visible = false }

    // Press keys through oziwm; Shift and Ctrl go with the next key only.
    function send(codes) {
        let keys = []
        if (ctrl) keys.push(29)
        keys = keys.concat(codes)
        Shell.pressKeys(keys)
        if (shift && !caps) shift = false
        ctrl = false
    }
    function typeKey(k) { send(upper ? [42, k.code] : [k.code]) }
    function tapShift() {
        const now = Date.now()
        if (now - lastShiftTap < 400) { caps = !caps; shift = false }
        else if (caps) caps = false
        else shift = !shift
        lastShiftTap = now
    }

    Connections {
        target: Shell
        function onKeyboardWanted(wanted) { wanted ? kb.show() : kb.hide() }
    }

    // The symbol page: everything the layout types with Shift or AltGr that is
    // not on the letter rows, laid out in rows of eleven.
    readonly property var symbolRows: {
        const list = board.symbols || []
        const out = []
        for (let i = 0; i < list.length && out.length < 3; i += 11) out.push(list.slice(i, i + 11))
        return out
    }

    Rectangle {
        id: panel
        width: parent.width
        height: parent.height
        y: kb.open ? 0 : height
        Behavior on y { NumberAnimation { duration: kb.shell.ms(180); easing.type: Easing.OutCubic } }
        color: Qt.alpha(kb.c.ink, 0.96)
        Rectangle { width: parent.width; height: 1; color: Qt.alpha(kb.c.text, 0.10) }

        Column {
            anchors.centerIn: parent
            spacing: kb.gap

            // Row 1: the digits (letters page) or the first symbols; Backspace.
            Row {
                spacing: kb.gap
                anchors.horizontalCenter: parent.horizontalCenter
                Repeater {
                    model: kb.rows.length > 0 ? kb.rows[0] : []
                    Key {
                        label: kb.symbols ? modelData.shift : modelData.label
                        onTapped: kb.symbols ? kb.send([42, modelData.code]) : kb.send([modelData.code])
                    }
                }
                Key { units: 1.6; glyph: "backspace"; special: true; repeats: true; onTapped: kb.send([14]) }
            }
            // Rows 2-4: letters, or the symbol page.
            Row {
                spacing: kb.gap
                anchors.horizontalCenter: parent.horizontalCenter
                Key { units: 1.4; text: "Tab"; special: true; onTapped: kb.send([15]) }
                Repeater {
                    model: kb.symbols ? (kb.symbolRows[0] || []) : (kb.rows[1] || [])
                    Key {
                        label: kb.symbols ? modelData.label : (kb.upper ? modelData.shift : modelData.label)
                        onTapped: kb.symbols ? kb.send(modelData.keys) : kb.typeKey(modelData)
                    }
                }
            }
            Row {
                spacing: kb.gap
                anchors.horizontalCenter: parent.horizontalCenter
                Repeater {
                    model: kb.symbols ? (kb.symbolRows[1] || []) : (kb.rows[2] || [])
                    Key {
                        label: kb.symbols ? modelData.label : (kb.upper ? modelData.shift : modelData.label)
                        onTapped: kb.symbols ? kb.send(modelData.keys) : kb.typeKey(modelData)
                    }
                }
                Key { units: 1.8; glyph: "enter"; special: true; accent: true; onTapped: kb.send([28]) }
            }
            Row {
                spacing: kb.gap
                anchors.horizontalCenter: parent.horizontalCenter
                Key {
                    units: 1.5; glyph: "shift"; special: true
                    visible: !kb.symbols
                    lit: kb.shift || kb.caps
                    underline: kb.caps
                    onTapped: kb.tapShift()
                }
                Repeater {
                    model: kb.symbols ? (kb.symbolRows[2] || []) : (kb.rows[3] || [])
                    Key {
                        label: kb.symbols ? modelData.label : (kb.upper ? modelData.shift : modelData.label)
                        onTapped: kb.symbols ? kb.send(modelData.keys) : kb.typeKey(modelData)
                    }
                }
                Key {
                    units: 1.5; glyph: "shift"; special: true
                    visible: !kb.symbols
                    lit: kb.shift || kb.caps
                    underline: kb.caps
                    onTapped: kb.tapShift()
                }
            }
            // Row 5: page switch, Ctrl, space, arrows, close.
            Row {
                spacing: kb.gap
                anchors.horizontalCenter: parent.horizontalCenter
                Key { units: 1.6; text: kb.symbols ? "abc" : "&123"; special: true; onTapped: kb.symbols = !kb.symbols }
                Key { units: 1.3; text: "Ctrl"; special: true; lit: kb.ctrl; onTapped: kb.ctrl = !kb.ctrl }
                Key { units: 6.2; text: kb.board.layout ? kb.board.layout.toUpperCase() : ""; dim: true; onTapped: kb.send([57]) }
                Key { units: 1.1; glyph: "chevron-left"; special: true; repeats: true; onTapped: kb.send([105]) }
                Key { units: 1.1; glyph: "chevron-right"; special: true; repeats: true; onTapped: kb.send([106]) }
                Key { units: 1.1; text: "Esc"; special: true; onTapped: kb.send([1]) }
                Key { units: 1.6; glyph: "keyboard-hide"; special: true; onTapped: kb.hide() }
            }
        }
    }

    component Key: Rectangle {
        id: key
        property string label: ""
        property alias text: caption.text
        property string glyph: ""
        property real units: 1
        property bool special: false
        property bool accent: false
        property bool lit: false
        property bool underline: false
        property bool dim: false
        property bool repeats: false
        signal tapped()

        width: Math.round(kb.unit * units + kb.gap * (units - 1))
        height: kb.keyH
        radius: Math.round(kb.keyH * 0.18)
        color: area.pressed ? Qt.alpha(kb.c.accent, 0.45)
             : accent ? Qt.alpha(kb.c.accent, 0.30)
             : lit ? Qt.alpha(kb.c.accent, 0.22)
             : special ? Qt.alpha(kb.c.text, 0.10) : Qt.alpha(kb.c.text, 0.16)
        border.width: 1
        border.color: lit || accent ? Qt.alpha(kb.c.accent, 0.7) : Qt.alpha(kb.c.text, 0.07)
        scale: area.pressed ? 0.94 : 1
        Behavior on scale { NumberAnimation { duration: 70 } }

        Text {
            id: caption
            anchors.centerIn: parent
            visible: !key.glyph
            text: key.label
            color: key.dim ? kb.c.muted : kb.c.text
            font.pixelSize: key.special || key.dim ? Math.round(kb.keyH * 0.28) : Math.round(kb.keyH * 0.42)
            font.weight: key.special ? Font.DemiBold : Font.Normal
        }
        Glyph {
            anchors.centerIn: parent
            visible: !!key.glyph
            kind: key.glyph || "dots"
            size: Math.round(kb.keyH * 0.40)
            color: kb.c.text
        }
        Rectangle {
            visible: key.underline
            anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: kb.keyH * 0.14 }
            width: parent.width * 0.3; height: 2; radius: 1; color: kb.c.accent
        }
        // Fingers: the key acts as it goes down, the way phone keyboards do.
        MouseArea {
            id: area
            anchors.fill: parent
            onPressed: { key.tapped(); if (key.repeats) repeat.start() }
            onReleased: repeat.stop()
            onCanceled: repeat.stop()
        }
        Timer {
            id: repeat
            interval: 420
            repeat: true
            onTriggered: { interval = 55; key.tapped() }
            onRunningChanged: if (!running) interval = 420
        }
    }
}
