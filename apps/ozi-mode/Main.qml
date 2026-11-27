import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import OziUi

// Öğretmen: the board's two modes. Kısıtlı is how every board starts;
// the teacher's password opens Yetkili until the next start.
ApplicationWindow {
    id: window
    width: 720
    height: 640
    minimumWidth: 560
    minimumHeight: 520
    visible: true
    title: backend.tr("Teacher mode")
    color: Theme.ink

    property var st: ({ mode: "kisitli", education: true, freeze: { enabled: false, saved: 0 } })
    readonly property bool authorised: st.mode === "yetkili"
    property bool busy: false
    property string message: ""
    property bool good: false

    Component.onCompleted: backend.call("status", "status", "[]")

    function say(text, ok) {
        message = text
        good = ok
    }

    Connections {
        target: backend
        function onDone(task, json) {
            window.busy = false
            window.st = JSON.parse(json)
            if (task === "unlock") {
                password.text = ""
                window.say(backend.tr("Authorised mode is on until the next start."), true)
            } else if (task === "lock") {
                window.say(backend.tr("The board is restricted again."), true)
            } else if (task === "password") {
                newPassword.text = ""
                window.say(backend.tr("The teacher password is changed."), true)
            } else if (task === "freeze") {
                window.say(window.st.freeze.enabled ? backend.tr("Frozen: the board goes back to this state at every start.")
                                                     : backend.tr("Freezing is off."), true)
            }
        }
        function onFailed(task, text) {
            window.busy = false
            window.say(text, false)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 16

        RowLayout {
            spacing: 16
            Rectangle {
                width: 64
                height: 64
                radius: 32
                color: window.authorised ? Theme.good : Theme.caution
                Text {
                    anchors.centerIn: parent
                    text: window.authorised ? "✓" : "🔒"
                    font.pixelSize: 28
                    color: Theme.ink
                }
            }
            ColumnLayout {
                spacing: 2
                Text {
                    text: window.authorised ? backend.tr("Authorised mode") : backend.tr("Restricted mode")
                    color: Theme.ice
                    font.family: Theme.family
                    font.pixelSize: 28
                    font.bold: true
                }
                Text {
                    Layout.preferredWidth: window.width - 160
                    wrapMode: Text.WordWrap
                    text: window.authorised
                          ? backend.tr("Everything is open: terminal, settings, the store and admin rights.")
                          : backend.tr("Lessons work as usual. The terminal, settings, the store and admin rights are closed.")
                    color: Theme.muted
                    font.family: Theme.family
                    font.pixelSize: 15
                }
            }
        }

        Text {
            visible: !window.st.education
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: backend.tr("Modes are for the Education edition; this computer is always authorised.")
            color: Theme.caution
            font.family: Theme.family
            font.pixelSize: 15
        }

        // Restricted: the password.
        Card {
            Layout.fillWidth: true
            implicitHeight: 150
            visible: !window.authorised && window.st.education
            ColumnLayout {
                anchors.fill: parent
                spacing: 12
                Text {
                    text: backend.tr("Teacher password")
                    color: Theme.ice
                    font.family: Theme.family
                    font.pixelSize: 17
                }
                RowLayout {
                    spacing: 12
                    TextField {
                        id: password
                        Layout.fillWidth: true
                        implicitHeight: 48
                        echoMode: TextInput.Password
                        font.pixelSize: 18
                        color: Theme.ice
                        placeholderText: "••••••••"
                        placeholderTextColor: Theme.far
                        background: Rectangle { radius: 6; color: Theme.control; border.color: password.activeFocus ? Theme.cyan : Theme.far }
                        onAccepted: unlock.clicked()
                    }
                    OButton {
                        id: unlock
                        primary: true
                        implicitHeight: 48
                        text: backend.tr("Switch to authorised")
                        enabled: !window.busy && password.text.length > 0
                        onClicked: {
                            window.busy = true
                            window.say("", true)
                            backend.call("unlock", "unlock", JSON.stringify([password.text]))
                        }
                    }
                }
            }
        }

        // Authorised: back to restricted, freezing, the password.
        Card {
            Layout.fillWidth: true
            implicitHeight: 230
            visible: window.authorised && window.st.education
            ColumnLayout {
                anchors.fill: parent
                spacing: 12
                RowLayout {
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: backend.tr("Freeze the board")
                            color: Theme.ice
                            font.family: Theme.family
                            font.pixelSize: 17
                        }
                        Text {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: backend.tr("At every start the desktop and files go back to the saved state. Lesson notes are kept.")
                            color: Theme.muted
                            font.family: Theme.family
                            font.pixelSize: 14
                        }
                    }
                    OSwitch {
                        checked: !!(window.st.freeze && window.st.freeze.enabled)
                        enabled: !window.busy
                        onToggled: {
                            window.busy = true
                            backend.call("freeze", "freeze", JSON.stringify([checked ? "on" : "off"]))
                        }
                    }
                }
                OButton {
                    text: backend.tr("Save this state as the frozen one")
                    enabled: !window.busy
                    onClicked: {
                        window.busy = true
                        backend.call("freeze", "freeze", JSON.stringify(["save"]))
                    }
                }
                RowLayout {
                    spacing: 12
                    TextField {
                        id: newPassword
                        Layout.fillWidth: true
                        implicitHeight: 40
                        echoMode: TextInput.Password
                        color: Theme.ice
                        placeholderText: backend.tr("New teacher password")
                        placeholderTextColor: Theme.far
                        background: Rectangle { radius: 6; color: Theme.control; border.color: newPassword.activeFocus ? Theme.cyan : Theme.far }
                    }
                    OButton {
                        text: backend.tr("Change")
                        enabled: !window.busy && newPassword.text.length >= 4
                        onClicked: {
                            window.busy = true
                            backend.call("password", "password", JSON.stringify([newPassword.text]))
                        }
                    }
                }
            }
        }

        OButton {
            visible: window.authorised && window.st.education
            primary: true
            implicitHeight: 52
            font.pixelSize: 17
            Layout.fillWidth: true
            text: backend.tr("Back to restricted mode")
            enabled: !window.busy
            onClicked: {
                window.busy = true
                backend.call("lock", "lock", "[]")
            }
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: window.message
            visible: text !== ""
            color: window.good ? Theme.good : Theme.danger
            font.family: Theme.family
            font.pixelSize: 15
        }

        Item { Layout.fillHeight: true }
    }
}
