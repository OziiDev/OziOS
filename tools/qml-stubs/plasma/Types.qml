import QtQuick

// Stand-in for PlasmaCore.Types: the enums, in Plasma's order.
QtObject {
    enum FormFactor { Planar, MediaCenter, Horizontal, Vertical, Application }
    enum Location { Floating, Desktop, FullScreen, TopEdge, BottomEdge, LeftEdge, RightEdge }
    enum ItemStatus { UnknownStatus, PassiveStatus, ActiveStatus, NeedsAttentionStatus, RequiresAttentionStatus, AcceptingInputStatus, HiddenStatus }
    enum BackgroundHints { NoBackground, StandardBackground, TranslucentBackground = 2, ShadowBackground = 4, ConfigurableBackground = 8 }
}
