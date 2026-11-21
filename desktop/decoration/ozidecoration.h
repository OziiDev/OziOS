/*
    OziOS window frames.

    The title bar has the window's own background, a centred title and round buttons.
    The frame has no visible border of its own: KWin rounds the whole window
    (the program's content included) and draws an outline around it, in the accent
    colour when the window is active. The active window also gets a soft glow in
    the theme's two colours. Settings: ~/.config/ozidecorationrc, [Decoration].

    SPDX-License-Identifier: MIT
*/
#pragma once

#include <KDecoration3/Decoration>
#include <KDecoration3/DecorationButtonGroup>
#include <KDecoration3/DecorationShadow>

#include <QColor>
#include <QVariant>

#include <memory>

class QVariantAnimation;

namespace Ozi
{

struct Config {
    qreal cornerRadius = 10;
    qreal outlineWidth = 2; // active window; 0: none
    bool inactiveOutline = true; // a faint line around the other windows
    bool glow = true;
    qreal shadowSize = 30;
    int shadowStrength = 120; // 0..255
    bool titleBar = true;
    bool centerTitle = true;
    QString buttonStyle; // "traffic" (default), "accent", "mono"
    QColor accent; // invalid: the colour scheme's accent
    QColor accent2; // invalid: worked out from the accent
    qreal animationFactor = 1.0; // the desktop's animation speed; 0 turns animations off

    static Config load();
};

class Decoration : public KDecoration3::Decoration
{
    Q_OBJECT

public:
    explicit Decoration(QObject *parent = nullptr, const QVariantList &args = QVariantList());
    ~Decoration() override;

    bool init() override;
    void paint(QPainter *painter, const QRectF &repaintArea) override;

    // For the buttons.
    const Config &config() const
    {
        return m_config;
    }
    QColor accent() const;
    QColor accent2() const;
    QColor titleBarColor() const;
    QColor foregroundColor() const;
    bool isLight() const;
    bool isMaximized() const;
    qreal titleBarHeight() const;
    qreal buttonDiameter() const;
    int animationDuration(int milliseconds) const;
    qreal activeProgress() const
    {
        return m_activeProgress;
    }

private:
    void reconfigure();
    void recalculate();
    void updateButtonsGeometry();
    void updateShadow();
    void updateOutline();
    void animateActive();
    qreal snap(qreal value) const;
    qreal cornerRadius() const;
    qreal sideBorder() const;
    qreal frameWidth() const;
    QRectF captionRect() const;

    Config m_config;
    KDecoration3::DecorationButtonGroup *m_leftButtons = nullptr;
    KDecoration3::DecorationButtonGroup *m_rightButtons = nullptr;
    QVariantAnimation *m_activeAnimation = nullptr;
    qreal m_activeProgress = 0; // 0: inactive, 1: active
    // What recalculate() asked for. KWin applies borders with the next frame, so
    // borders() and size() can still hold the old values while the layout is worked out.
    qreal m_titleHeight = 0;
    qreal m_side = 0;
};

}
