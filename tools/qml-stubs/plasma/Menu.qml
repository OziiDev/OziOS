import QtQuick

// Stand-in for PlasmaExtras.Menu: remembers that it was opened and what it holds.
QtObject {
    enum Status { Closed, Opening, Open, Closing }
    enum PopupPlacement { FloatingPopup, TopPosedLeftAlignedPopup, TopPosedRightAlignedPopup, LeftPosedTopAlignedPopup,
                          LeftPosedBottomAlignedPopup, BottomPosedLeftAlignedPopup, BottomPosedRightAlignedPopup,
                          RightPosedTopAlignedPopup, RightPosedBottomAlignedPopup }

    default property list<QtObject> content
    property Item visualParent
    property int placement: 0
    property int status: 0
    property real minimumWidth: 0
    property int timesOpened: 0

    function openRelative() {
        timesOpened++
        status = 2
    }
    function open(x, y) { openRelative() }
    function close() { status = 0 }
}
