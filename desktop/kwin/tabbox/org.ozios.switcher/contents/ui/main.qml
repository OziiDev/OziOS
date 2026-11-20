import QtQuick
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kwin as KWin
import org.kde.kirigami as Kirigami

// The OziOS window switcher (Alt+Tab): the open windows as live pictures in one
// row. The chosen one comes forward in the accent colour and the row glides to
// keep it in the middle. Built like KWin's own Thumbnail Grid (same model, same
// dialog), with the OziOS look and motion. The popup's frame is the Plasma style's.
KWin.TabBoxSwitcher {
    id: tabBox

    readonly property bool animations: Kirigami.Units.longDuration > 1

    Instantiator {
        active: tabBox.visible
        delegate: PlasmaCore.Dialog {
            location: PlasmaCore.Types.Floating
            visible: true
            flags: Qt.Popup | Qt.X11BypassWindowManagerHint
            x: tabBox.screenGeometry.x + tabBox.screenGeometry.width * 0.5 - content.width * 0.5
            y: tabBox.screenGeometry.y + tabBox.screenGeometry.height * 0.5 - content.height * 0.5

            mainItem: FocusScope {
                id: content
                focus: true

                readonly property real screenRatio: tabBox.screenGeometry.width / Math.max(1, tabBox.screenGeometry.height)
                readonly property int cardWidth: Kirigami.Units.gridUnit * 13
                readonly property int cardHeight: Math.round(cardWidth / screenRatio) + Kirigami.Units.gridUnit * 2.6
                width: Math.min(tabBox.screenGeometry.width * 0.9,
                                Math.max(cardWidth * 2, cards.count * (cardWidth + cards.spacing) + cards.spacing))
                height: cardHeight + Kirigami.Units.largeSpacing * 2

                ListView {
                    id: cards
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.largeSpacing
                    orientation: ListView.Horizontal
                    spacing: Kirigami.Units.largeSpacing * 2
                    model: tabBox.model
                    currentIndex: tabBox.currentIndex
                    focus: true
                    keyNavigationWraps: true
                    highlightRangeMode: ListView.ApplyRange
                    preferredHighlightBegin: width / 2 - content.cardWidth / 2
                    preferredHighlightEnd: width / 2 + content.cardWidth / 2
                    highlightMoveDuration: tabBox.animations ? 240 : 0
                    onCurrentIndexChanged: tabBox.currentIndex = currentIndex

                    delegate: MouseArea {
                        id: card
                        required property int index
                        required property var model
                        width: content.cardWidth
                        height: cards.height
                        hoverEnabled: true
                        onClicked: tabBox.model.activate(index)

                        Accessible.name: model.caption
                        Accessible.role: Accessible.ListItem

                        SwitcherCard {
                            anchors.fill: parent
                            current: card.ListView.isCurrentItem
                            hovered: card.containsMouse
                            caption: card.model.caption || ""
                            accent: Kirigami.Theme.highlightColor
                            textColor: Kirigami.Theme.textColor
                            font: Kirigami.Theme.defaultFont
                            animate: tabBox.animations
                            screenRatio: content.screenRatio

                            KWin.WindowThumbnail {
                                anchors.fill: parent
                                wId: card.model.windowId
                            }

                            badge: Kirigami.Icon {
                                anchors.fill: parent
                                source: card.model.icon
                            }
                        }
                    }
                }

                PlasmaComponents3.Label {
                    anchors.centerIn: parent
                    visible: cards.count === 0
                    text: Qt.locale().name.indexOf("tr") === 0 ? "Açık pencere yok" : "No open windows"
                    opacity: 0.7
                }

                Keys.onPressed: event => {
                    if (event.key === Qt.Key_Left) {
                        cards.decrementCurrentIndex()
                    } else if (event.key === Qt.Key_Right) {
                        cards.incrementCurrentIndex()
                    } else {
                        return
                    }
                    event.accepted = true
                }
            }

            onSceneGraphError: () => {
                // Left empty on purpose: without a handler Qt Quick may stop KWin after a graphics reset.
            }
        }
    }
}
