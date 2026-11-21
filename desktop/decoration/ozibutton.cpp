/*
    SPDX-License-Identifier: MIT
*/
#include "ozibutton.h"
#include "ozidecoration.h"

#include <KDecoration3/DecoratedWindow>
#include <KDecoration3/DecorationSettings>

#include <QFont>
#include <QIcon>
#include <QPainter>
#include <QPainterPath>
#include <QPolygonF>
#include <QVariantAnimation>

#include <algorithm>

namespace Ozi
{

using KDecoration3::DecoratedWindow;
using KDecoration3::DecorationButtonType;

namespace
{

QColor mix(const QColor &a, const QColor &b, qreal t)
{
    t = std::clamp<qreal>(t, 0, 1);
    return QColor::fromRgbF(a.redF() + (b.redF() - a.redF()) * t,
                            a.greenF() + (b.greenF() - a.greenF()) * t,
                            a.blueF() + (b.blueF() - a.blueF()) * t,
                            a.alphaF() + (b.alphaF() - a.alphaF()) * t);
}

}

Button::Button(DecorationButtonType type, Decoration *decoration, QObject *parent)
    : KDecoration3::DecorationButton(type, decoration, parent)
    , m_hover(new QVariantAnimation(this))
{
    m_hover->setEasingCurve(QEasingCurve::OutCubic);
    connect(m_hover, &QVariantAnimation::valueChanged, this, [this](const QVariant &value) {
        m_hoverProgress = value.toReal();
        update();
    });
    connect(this, &KDecoration3::DecorationButton::hoveredChanged, this, [this](bool hovered) {
        const int duration = ozi() ? ozi()->animationDuration(140) : 0;
        if (duration <= 0) {
            m_hover->stop();
            m_hoverProgress = hovered ? 1 : 0;
            update();
            return;
        }
        m_hover->stop();
        m_hover->setStartValue(m_hoverProgress);
        m_hover->setEndValue(hovered ? 1.0 : 0.0);
        m_hover->setDuration(duration);
        m_hover->start();
    });
    connect(this, &KDecoration3::DecorationButton::pressedChanged, this, [this]() {
        update();
    });
    if (!decoration) {
        return;
    }
    DecoratedWindow *window = decoration->window();
    connect(window, &DecoratedWindow::activeChanged, this, [this]() {
        update();
    });
    // Buttons that do nothing for this window are left out.
    switch (type) {
    case DecorationButtonType::Minimize:
        setVisible(window->isMinimizeable());
        connect(window, &DecoratedWindow::minimizeableChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::Maximize:
        setVisible(window->isMaximizeable());
        connect(window, &DecoratedWindow::maximizeableChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::Close:
        setVisible(window->isCloseable());
        connect(window, &DecoratedWindow::closeableChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::ContextHelp:
        setVisible(window->providesContextHelp());
        connect(window, &DecoratedWindow::providesContextHelpChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::Shade:
        setVisible(window->isShadeable());
        connect(window, &DecoratedWindow::shadeableChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::ApplicationMenu:
        setVisible(window->hasApplicationMenu());
        connect(window, &DecoratedWindow::hasApplicationMenuChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    case DecorationButtonType::OnAllDesktops:
        setVisible(decoration->settings()->isOnAllDesktopsAvailable());
        connect(decoration->settings().get(), &KDecoration3::DecorationSettings::onAllDesktopsAvailableChanged, this, &KDecoration3::DecorationButton::setVisible);
        break;
    default:
        break;
    }
}

Button::Button(QObject *parent, const QVariantList &args)
    : Button(args.value(0).value<DecorationButtonType>(), qobject_cast<Decoration *>(args.value(1).value<QObject *>()), parent)
{
}

KDecoration3::DecorationButton *Button::create(DecorationButtonType type, KDecoration3::Decoration *decoration, QObject *parent)
{
    auto *ours = qobject_cast<Decoration *>(decoration);
    if (!ours) {
        return nullptr;
    }
    switch (type) {
    case DecorationButtonType::Close:
    case DecorationButtonType::Maximize:
    case DecorationButtonType::Minimize:
    case DecorationButtonType::OnAllDesktops:
    case DecorationButtonType::Shade:
    case DecorationButtonType::KeepAbove:
    case DecorationButtonType::KeepBelow:
    case DecorationButtonType::ContextHelp:
    case DecorationButtonType::Menu:
    case DecorationButtonType::ApplicationMenu:
    case DecorationButtonType::Spacer:
    case DecorationButtonType::ExcludeFromCapture:
        return new Button(type, ours, parent);
    default:
        return nullptr;
    }
}

Decoration *Button::ozi() const
{
    return qobject_cast<Decoration *>(decoration());
}

// The colour of a close, minimise or maximise light.
QColor Button::lightColor() const
{
    const Decoration *d = ozi();
    const QString style = d ? d->config().buttonStyle : QString();
    const QColor accent = d ? d->accent() : QColor(0, 229, 255);
    const QColor red(255, 95, 87);
    if (style == QLatin1String("mono")) {
        QColor quiet = d ? d->foregroundColor() : QColor(Qt::white);
        quiet.setAlphaF(0.55);
        return type() == DecorationButtonType::Close ? mix(quiet, red, m_hoverProgress) : mix(quiet, accent, m_hoverProgress);
    }
    if (style == QLatin1String("accent")) {
        return type() == DecorationButtonType::Close ? mix(accent, red, m_hoverProgress) : accent;
    }
    switch (type()) {
    case DecorationButtonType::Close:
        return red;
    case DecorationButtonType::Minimize:
        return QColor(254, 188, 46);
    default:
        return accent;
    }
}

void Button::paint(QPainter *painter, const QRectF &repaintArea)
{
    Q_UNUSED(repaintArea)
    const Decoration *d = ozi();
    if (!d || !isVisible() || type() == DecorationButtonType::Spacer) {
        return;
    }
    const QRectF box = geometry();
    const qreal diameter = d->buttonDiameter();
    const QRectF circle(box.center().x() - diameter / 2, box.center().y() - diameter / 2, diameter, diameter);
    const bool active = d->window()->isActive();
    const qreal hover = std::max<qreal>(m_hoverProgress, isPressed() ? 1.0 : 0.0);
    const QColor fg = d->foregroundColor();

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    painter->setPen(Qt::NoPen);

    switch (type()) {
    case DecorationButtonType::Close:
    case DecorationButtonType::Minimize:
    case DecorationButtonType::Maximize: {
        const QColor light = lightColor();
        QColor quiet = fg;
        quiet.setAlphaF(d->isLight() ? 0.18 : 0.2);
        // Lit on the active window; on the others only while the pointer is over it.
        QColor fill = mix(quiet, light, std::max(d->activeProgress(), hover));
        if (isPressed()) {
            fill = fill.darker(125);
        }
        painter->setBrush(fill);
        painter->drawEllipse(circle);
        if (hover > 0.01) {
            QColor ink(0, 0, 0);
            ink.setAlphaF(0.6 * hover);
            paintSign(painter, circle, ink);
        }
        break;
    }
    case DecorationButtonType::Menu: {
        const qreal size = std::max<qreal>(16, diameter + 2);
        const QRectF iconRect(box.center().x() - size / 2, box.center().y() - size / 2, size, size);
        d->window()->icon().paint(painter, iconRect.toAlignedRect());
        break;
    }
    default: {
        QColor disc = fg;
        disc.setAlphaF(0.14 * std::max<qreal>(hover, isChecked() ? 0.8 : 0.0));
        if (disc.alpha() > 0) {
            painter->setBrush(disc);
            painter->drawEllipse(circle.adjusted(-3, -3, 3, 3));
        }
        QColor ink = fg;
        ink.setAlphaF(active ? 0.8 : 0.45);
        paintSign(painter, circle, ink);
        break;
    }
    }
    painter->restore();
}

void Button::paintSign(QPainter *painter, const QRectF &circle, const QColor &ink) const
{
    const QPointF c = circle.center();
    const qreal k = circle.width() * 0.22;
    QPen pen(ink, std::max<qreal>(1.2, circle.width() / 9.0), Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
    painter->setPen(pen);
    painter->setBrush(Qt::NoBrush);

    switch (type()) {
    case DecorationButtonType::Close:
        painter->drawLine(QPointF(c.x() - k, c.y() - k), QPointF(c.x() + k, c.y() + k));
        painter->drawLine(QPointF(c.x() - k, c.y() + k), QPointF(c.x() + k, c.y() - k));
        break;
    case DecorationButtonType::Minimize:
        painter->drawLine(QPointF(c.x() - k * 1.1, c.y()), QPointF(c.x() + k * 1.1, c.y()));
        break;
    case DecorationButtonType::Maximize: {
        // Two corners: pointing out to grow, pointing in when the window fills the screen.
        painter->setPen(Qt::NoPen);
        painter->setBrush(ink);
        const qreal a = k * 1.2;
        const qreal b = k * 0.12;
        QPolygonF one, two;
        if (isChecked()) {
            one << QPointF(c.x() + b, c.y() - b) << QPointF(c.x() + a, c.y() - b) << QPointF(c.x() + b, c.y() - a);
            two << QPointF(c.x() - b, c.y() + b) << QPointF(c.x() - a, c.y() + b) << QPointF(c.x() - b, c.y() + a);
        } else {
            one << QPointF(c.x() + a, c.y() - a) << QPointF(c.x() - b, c.y() - a) << QPointF(c.x() + a, c.y() + b);
            two << QPointF(c.x() - a, c.y() + a) << QPointF(c.x() + b, c.y() + a) << QPointF(c.x() - a, c.y() - b);
        }
        painter->drawPolygon(one);
        painter->drawPolygon(two);
        break;
    }
    case DecorationButtonType::OnAllDesktops:
        if (isChecked()) {
            painter->setBrush(ink);
        }
        painter->drawEllipse(c, k * 0.8, k * 0.8);
        break;
    case DecorationButtonType::KeepAbove:
    case DecorationButtonType::KeepBelow:
    case DecorationButtonType::Shade: {
        const bool up = type() == DecorationButtonType::KeepAbove || (type() == DecorationButtonType::Shade && !isChecked());
        const qreal dy = up ? -k * 0.5 : k * 0.5;
        QPainterPath chevron;
        chevron.moveTo(c.x() - k, c.y() - dy);
        chevron.lineTo(c.x(), c.y() + dy);
        chevron.lineTo(c.x() + k, c.y() - dy);
        painter->drawPath(chevron);
        if (type() != DecorationButtonType::Shade && isChecked()) {
            painter->drawLine(QPointF(c.x() - k, c.y() + (up ? k : -k)), QPointF(c.x() + k, c.y() + (up ? k : -k)));
        }
        break;
    }
    case DecorationButtonType::ApplicationMenu:
        for (int i = -1; i <= 1; ++i) {
            painter->drawLine(QPointF(c.x() - k, c.y() + i * k * 0.8), QPointF(c.x() + k, c.y() + i * k * 0.8));
        }
        break;
    case DecorationButtonType::ContextHelp: {
        QFont font = painter->font();
        font.setPixelSize(int(circle.height() * 0.9));
        font.setBold(true);
        painter->setFont(font);
        painter->drawText(circle, Qt::AlignCenter, QStringLiteral("?"));
        break;
    }
    case DecorationButtonType::ExcludeFromCapture:
        painter->drawEllipse(c, k * 1.2, k * 0.7);
        if (isChecked()) {
            painter->drawLine(QPointF(c.x() - k * 1.2, c.y() + k * 0.9), QPointF(c.x() + k * 1.2, c.y() - k * 0.9));
        } else {
            painter->setBrush(ink);
            painter->drawEllipse(c, k * 0.3, k * 0.3);
        }
        break;
    default:
        break;
    }
}

}
