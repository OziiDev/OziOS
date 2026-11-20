import QtQuick

// Stand-in for Plasma5Support.DataSource with the "executable" engine: the
// command is answered by the preview tool's fake shell (stubShell).
QtObject {
    id: source
    property string engine
    property var connectedSources: []
    property int interval: 0
    signal newData(string sourceName, var data)

    property var pending: []
    property Timer answer: Timer {
        interval: 10
        onTriggered: {
            const queue = source.pending
            source.pending = []
            for (const command of queue)
                source.newData(command, stubShell.run(command))
        }
    }
    function connectSource(command) {
        pending = pending.concat([command])
        answer.restart()
    }
    function disconnectSource(command) {}
}
