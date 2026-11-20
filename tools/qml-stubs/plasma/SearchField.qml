import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as K

// Stand-in for PlasmaExtras.SearchField.
QQC2.TextField {
    color: K.Theme.textColor
    placeholderTextColor: Qt.rgba(K.Theme.textColor.r, K.Theme.textColor.g, K.Theme.textColor.b, 0.5)
    leftPadding: 10
    background: Rectangle {
        radius: 6
        color: Qt.rgba(K.Theme.textColor.r, K.Theme.textColor.g, K.Theme.textColor.b, 0.07)
        border.width: 1
        border.color: Qt.rgba(K.Theme.highlightColor.r, K.Theme.highlightColor.g, K.Theme.highlightColor.b, 0.45)
    }
}
