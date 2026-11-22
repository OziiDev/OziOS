import QtQuick 2.0
import calamares.slideshow 1.0

// Shown while the system is being installed. The words follow the language of
// the session; Turkish and English are written out here because the installer
// has no translation catalogue for them.
Presentation {
    id: presentation

    readonly property bool turkish: Qt.locale().name.indexOf("tr") === 0
    function say(english, turkishText) { return turkish ? turkishText : english }

    // The slides are smaller than the area they are shown in; paint all of it.
    Rectangle {
        anchors.fill: parent
        color: "#080B10"
        z: -1
    }

    Timer {
        interval: 9000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        OziSlide {
            heading: "OziOS"
            words: presentation.say("A desktop for games and everyday work, built on Arch packages and KDE Plasma 6.",
                                    "Oyun ve günlük işler için, Arch paketleri ve KDE Plasma 6 üzerine kurulu bir masaüstü.")
        }
    }

    Slide {
        OziSlide {
            heading: presentation.say("Software, checked first", "Yazılım, önce denetlenir")
            words: presentation.say("Packages are reviewed before they go on your system. Debian and Ubuntu packages run in their own boxes, with only the permissions you give them.",
                                    "Paketler sisteminize girmeden önce incelenir. Debian ve Ubuntu paketleri kendi kutularında, yalnızca verdiğiniz izinlerle çalışır.")
        }
    }

    Slide {
        OziSlide {
            heading: presentation.say("Its own kernel", "Kendi çekirdeği")
            words: presentation.say("OziOS ships its own build of the Linux kernel, tuned for desktop and gaming use.",
                                    "OziOS, masaüstü ve oyun kullanımı için ayarlanmış kendi Linux çekirdeğiyle gelir.")
        }
    }
}
