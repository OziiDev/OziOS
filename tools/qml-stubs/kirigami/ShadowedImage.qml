import QtQuick

// Stand-in for Kirigami.ShadowedImage: an image with rounded corners. Only the
// properties OziOS sets; the corners are not rounded here.
Item {
    property alias source: image.source
    property alias asynchronous: image.asynchronous
    property alias fillMode: image.fillMode
    property alias mipmap: image.mipmap
    property alias sourceSize: image.sourceSize
    readonly property alias status: image.status
    property real radius: 0
    property color color: "transparent"

    Image {
        id: image
        anchors.fill: parent
    }
}
