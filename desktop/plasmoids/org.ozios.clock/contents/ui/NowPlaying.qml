import QtQuick
import org.kde.plasma.private.mpris as Mpris

// What is playing, from Plasma's model of the media players on the session bus
// (MPRIS: browsers, music and video players). It is loaded apart from the clock,
// so if this private module goes away or changes, only the music goes with it.
Item {
    id: media

    readonly property var player: players.currentPlayer
    readonly property int status: player ? player.playbackStatus : Mpris.PlaybackStatus.Unknown
    readonly property bool playing: status === Mpris.PlaybackStatus.Playing
    readonly property bool paused: status === Mpris.PlaybackStatus.Paused
    readonly property string title: player ? (player.track || "") : ""
    readonly property string artist: player ? (player.artist || "") : ""
    readonly property string art: player ? (player.artUrl || "") : ""
    readonly property string identity: player ? (player.identity || "") : ""
    // Something to show: a track that plays or waits; a stopped player says nothing.
    readonly property bool active: (playing || paused) && title.length > 0
    readonly property bool canControl: !!player && player.canControl
    readonly property bool canNext: canControl && player.canGoNext
    readonly property bool canPrevious: canControl && player.canGoPrevious

    function toggle() {
        if (canControl) {
            player.PlayPause()
        }
    }
    function next() {
        if (canNext) {
            player.Next()
        }
    }
    function previous() {
        if (canPrevious) {
            player.Previous()
        }
    }

    // Its current player follows the one that last started playing.
    Mpris.Mpris2Model {
        id: players
    }
}
