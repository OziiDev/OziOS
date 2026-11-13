import QtQuick 2.0
import calamares.slideshow 1.0

// Shown while the system is being installed.
Presentation {
    id: presentation

    Timer {
        interval: 9000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#080B10"
            Column {
                anchors.centerIn: parent
                width: parent.width * 0.7
                spacing: 18
                Text { text: "OziOS"; color: "#00E5FF"; font.pixelSize: 34; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    width: parent.width
                    text: "A desktop for games and everyday work, built on Arch packages and KDE Plasma 6."
                    color: "#F4FCFF"; font.pixelSize: 18; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#080B10"
            Column {
                anchors.centerIn: parent
                width: parent.width * 0.7
                spacing: 18
                Text { text: "Software, checked first"; color: "#00E5FF"; font.pixelSize: 34; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    width: parent.width
                    text: "Packages are reviewed before they go on your system. Debian and Ubuntu packages run in their own boxes, with only the permissions you give them."
                    color: "#F4FCFF"; font.pixelSize: 18; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#080B10"
            Column {
                anchors.centerIn: parent
                width: parent.width * 0.7
                spacing: 18
                Text { text: "Its own kernel"; color: "#00E5FF"; font.pixelSize: 34; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    width: parent.width
                    text: "OziOS ships its own build of the Linux kernel, tuned for desktop and gaming use."
                    color: "#F4FCFF"; font.pixelSize: 18; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#080B10"
            Column {
                anchors.centerIn: parent
                width: parent.width * 0.7
                spacing: 18
                Text { text: "Windows programs"; color: "#00E5FF"; font.pixelSize: 34; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    width: parent.width
                    text: "With a Windows ISO of your own, OziOS can open .exe files in a window next to your other programs. It is set up separately, after the install."
                    color: "#F4FCFF"; font.pixelSize: 18; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
}
