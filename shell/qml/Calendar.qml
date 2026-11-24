import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LS

// The bar's clock opens this: today, and a month to page through.
Window {
    id: cal
    property var shell
    readonly property var c: shell.c

    visible: false
    color: "transparent"
    width: Screen.width > 0 ? Screen.width : 1366
    height: Screen.height > 0 ? Screen.height : 768
    LS.Window.scope: "ozi-calendar"
    LS.Window.layer: LS.Window.LayerOverlay
    LS.Window.anchors: LS.Window.AnchorTop | LS.Window.AnchorBottom | LS.Window.AnchorLeft | LS.Window.AnchorRight
    LS.Window.exclusionZone: -1
    LS.Window.keyboardInteractivity: LS.Window.KeyboardInteractivityOnDemand

    readonly property var locale: Qt.locale("tr_TR")
    property date today: new Date()
    property int year: today.getFullYear()
    property int month: today.getMonth()

    function toggle() { visible ? close() : show() }
    function show() { today = new Date(); year = today.getFullYear(); month = today.getMonth(); visible = true; card.forceActiveFocus() }
    function close() { visible = false }
    function step(by) {
        let m = month + by, y = year
        while (m < 0) { m += 12; y-- }
        while (m > 11) { m -= 12; y++ }
        month = m; year = y
    }

    // Monday-first grid of 42 days around the month.
    readonly property var days: {
        const first = new Date(year, month, 1)
        const lead = (first.getDay() + 6) % 7
        const out = []
        for (let i = 0; i < 42; i++) {
            const d = new Date(year, month, 1 - lead + i)
            out.push({ day: d.getDate(), inMonth: d.getMonth() === month,
                       today: d.toDateString() === today.toDateString(), weekend: d.getDay() === 0 || d.getDay() === 6 })
        }
        return out
    }

    MouseArea { anchors.fill: parent; onClicked: cal.close() }

    Rectangle {
        id: card
        focus: true
        Keys.onEscapePressed: cal.close()
        Keys.onLeftPressed: cal.step(-1)
        Keys.onRightPressed: cal.step(1)
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: 42 }
        width: 300; height: column.height + 28
        radius: 16
        color: cal.c.raised
        border.width: 1
        border.color: Qt.alpha(cal.c.text, 0.08)
        MouseArea { anchors.fill: parent }

        Column {
            id: column
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 14 }
            spacing: 10

            Column {
                spacing: 2
                Text { text: cal.today.toLocaleDateString(cal.locale, "dddd"); color: cal.c.muted; font.pixelSize: 12 }
                Text { text: cal.today.toLocaleDateString(cal.locale, "d MMMM yyyy"); color: cal.c.text; font.pixelSize: 18; font.weight: Font.DemiBold }
            }

            Item {
                width: parent.width; height: 28
                Text {
                    anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                    text: new Date(cal.year, cal.month, 1).toLocaleDateString(cal.locale, "MMMM yyyy")
                    color: cal.c.text; font.pixelSize: 13; font.weight: Font.DemiBold
                }
                Row {
                    anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                    spacing: 2
                    Repeater {
                        model: [{ g: "chevron-left", by: -1 }, { g: "chevron-right", by: 1 }]
                        Rectangle {
                            required property var modelData
                            width: 28; height: 28; radius: 7
                            color: navMouse.containsMouse ? Qt.alpha(cal.c.text, 0.10) : "transparent"
                            Glyph { anchors.centerIn: parent; kind: parent.modelData.g; color: cal.c.text; size: 12 }
                            MouseArea { id: navMouse; anchors.fill: parent; hoverEnabled: true; onClicked: cal.step(parent.modelData.by) }
                        }
                    }
                }
            }

            Grid {
                columns: 7
                Repeater {
                    model: ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"]
                    Text { required property string modelData; width: 38; height: 22; text: modelData; color: cal.c.muted; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                }
                Repeater {
                    model: cal.days
                    Rectangle {
                        required property var modelData
                        width: 38; height: 32; radius: 8
                        color: modelData.today ? cal.c.accent : "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: parent.modelData.day
                            color: parent.modelData.today ? cal.c.onAccent
                                 : !parent.modelData.inMonth ? Qt.alpha(cal.c.muted, 0.5)
                                 : parent.modelData.weekend ? cal.c.muted : cal.c.text
                            font.pixelSize: 12; font.weight: parent.modelData.today ? Font.Bold : Font.Normal
                        }
                    }
                }
            }
        }
    }
}
