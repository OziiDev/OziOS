pragma Singleton
import QtQuick

// Stand-in for Kirigami.Units, with Plasma's usual values.
QtObject {
    property int gridUnit: 18
    property int smallSpacing: 4
    property int mediumSpacing: 6
    property int largeSpacing: 8
    property int veryShortDuration: 50
    property int shortDuration: 100
    property int longDuration: 200
    property int veryLongDuration: 400
    property real cornerRadius: 5
    property QtObject iconSizes: QtObject {
        property int small: 16
        property int smallMedium: 22
        property int medium: 32
        property int large: 48
        property int huge: 64
        property int enormous: 128
    }
}
