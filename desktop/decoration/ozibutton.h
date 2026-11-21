/*
    Title bar buttons: round lights. Close, minimise and maximise show their colour
    on the active window and their sign when the pointer is over them; the other
    buttons are small monochrome signs.

    SPDX-License-Identifier: MIT
*/
#pragma once

#include <KDecoration3/DecorationButton>

#include <QVariant>

class QVariantAnimation;

namespace Ozi
{

class Decoration;

class Button : public KDecoration3::DecorationButton
{
    Q_OBJECT

public:
    explicit Button(KDecoration3::DecorationButtonType type, Decoration *decoration, QObject *parent = nullptr);
    // For the plugin factory (the window decoration settings page builds previews this way).
    explicit Button(QObject *parent, const QVariantList &args);

    static KDecoration3::DecorationButton *create(KDecoration3::DecorationButtonType type, KDecoration3::Decoration *decoration, QObject *parent);

    void paint(QPainter *painter, const QRectF &repaintArea) override;

private:
    Decoration *ozi() const;
    QColor lightColor() const;
    void paintSign(QPainter *painter, const QRectF &circle, const QColor &ink) const;

    QVariantAnimation *m_hover = nullptr;
    qreal m_hoverProgress = 0;
};

}
