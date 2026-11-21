/*
    SPDX-License-Identifier: MIT
*/
#include "ozidecoration.h"
#include "ozibutton.h"
#include "ozishadow.h"

#include <KDecoration3/DecoratedWindow>
#include <KDecoration3/DecorationSettings>
#include <KDecoration3/ScaleHelpers>

#include <KConfigGroup>
#include <KPluginFactory>
#include <KSharedConfig>

#include <QFontMetricsF>
#include <QPainter>
#include <QPainterPath>
#include <QVariantAnimation>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <utility>

K_PLUGIN_FACTORY_WITH_JSON(OziDecorationFactory, "ozios.json", registerPlugin<Ozi::Decoration>(); registerPlugin<Ozi::Button>();)

namespace Ozi
{

using KDecoration3::ColorGroup;
using KDecoration3::ColorRole;

namespace
{

// Shadows are shared by every window that looks the same; a handful at most.
struct CachedShadow {
    QString key;
    std::shared_ptr<KDecoration3::DecorationShadow> shadow;
};
QList<CachedShadow> s_shadows;
int s_decorations = 0;

QColor mix(const QColor &a, const QColor &b, qreal t)
{
    t = std::clamp<qreal>(t, 0, 1);
    return QColor::fromRgbF(a.redF() + (b.redF() - a.redF()) * t,
                            a.greenF() + (b.greenF() - a.greenF()) * t,
                            a.blueF() + (b.blueF() - a.blueF()) * t,
                            a.alphaF() + (b.alphaF() - a.alphaF()) * t);
}

// "r,g,b", "r,g,b,a" (as in KDE colour schemes) or "#rrggbb".
QColor parseColor(const QString &text)
{
    const QString value = text.trimmed();
    if (value.isEmpty()) {
        return QColor();
    }
    if (value.contains(QLatin1Char(','))) {
        const QStringList parts = value.split(QLatin1Char(','));
        if (parts.size() < 3) {
            return QColor();
        }
        QColor color(parts.at(0).trimmed().toInt(), parts.at(1).trimmed().toInt(), parts.at(2).trimmed().toInt());
        if (parts.size() > 3) {
            color.setAlpha(parts.at(3).trimmed().toInt());
        }
        return color;
    }
    return QColor::fromString(value);
}

}

Config Config::load()
{
    Config c;
    KSharedConfig::Ptr rc = KSharedConfig::openConfig(QStringLiteral("ozidecorationrc"), KConfig::NoGlobals);
    rc->reparseConfiguration();
    const KConfigGroup group = rc->group(QStringLiteral("Decoration"));
    c.cornerRadius = std::clamp(group.readEntry("CornerRadius", 10.0), 0.0, 24.0);
    c.outlineWidth = std::clamp(group.readEntry("OutlineWidth", 2.0), 0.0, 6.0);
    c.inactiveOutline = group.readEntry("InactiveOutline", true);
    c.glow = group.readEntry("Glow", true);
    c.shadowSize = std::clamp(group.readEntry("ShadowSize", 30.0), 0.0, 80.0);
    c.shadowStrength = std::clamp(group.readEntry("ShadowStrength", 120), 0, 255);
    c.titleBar = group.readEntry("TitleBar", true);
    c.centerTitle = group.readEntry("TitleAlignment", QStringLiteral("center")) != QLatin1String("left");
    c.buttonStyle = group.readEntry("ButtonStyle", QStringLiteral("traffic"));
    c.accent = parseColor(group.readEntry("AccentColor", QString()));
    c.accent2 = parseColor(group.readEntry("Accent2Color", QString()));

    KSharedConfig::Ptr globals = KSharedConfig::openConfig(QStringLiteral("kdeglobals"));
    globals->reparseConfiguration();
    c.animationFactor = std::max(0.0, globals->group(QStringLiteral("KDE")).readEntry("AnimationDurationFactor", 1.0));
    if (!c.accent.isValid()) {
        // The OziOS colour schemes keep their accent here.
        c.accent = parseColor(globals->group(QStringLiteral("WM")).readEntry("activeBlend", QString()));
    }
    return c;
}

Decoration::Decoration(QObject *parent, const QVariantList &args)
    : KDecoration3::Decoration(parent, args)
{
    ++s_decorations;
}

Decoration::~Decoration()
{
    if (--s_decorations == 0) {
        s_shadows.clear();
    }
}

bool Decoration::init()
{
    m_config = Config::load();
    KDecoration3::DecoratedWindow *w = window();
    m_activeProgress = w->isActive() ? 1 : 0;

    m_activeAnimation = new QVariantAnimation(this);
    m_activeAnimation->setEasingCurve(QEasingCurve::OutCubic);
    connect(m_activeAnimation, &QVariantAnimation::valueChanged, this, [this](const QVariant &value) {
        m_activeProgress = value.toReal();
        updateOutline();
        update();
    });

    m_leftButtons = new KDecoration3::DecorationButtonGroup(KDecoration3::DecorationButtonGroup::Position::Left, this, &Button::create);
    m_rightButtons = new KDecoration3::DecorationButtonGroup(KDecoration3::DecorationButtonGroup::Position::Right, this, &Button::create);

    connect(w, &KDecoration3::DecoratedWindow::activeChanged, this, &Decoration::animateActive);
    connect(w, &KDecoration3::DecoratedWindow::captionChanged, this, [this]() {
        update(titleBar());
    });
    connect(w, &KDecoration3::DecoratedWindow::widthChanged, this, [this]() {
        setTitleBar(m_config.titleBar ? QRectF(0, 0, frameWidth(), m_titleHeight) : QRectF());
        updateButtonsGeometry();
    });
    connect(this, &KDecoration3::Decoration::currentStateChanged, this, [this]() {
        updateButtonsGeometry();
        update();
    });
    connect(w, &KDecoration3::DecoratedWindow::maximizedChanged, this, &Decoration::recalculate);
    connect(w, &KDecoration3::DecoratedWindow::shadedChanged, this, &Decoration::recalculate);
    connect(w, &KDecoration3::DecoratedWindow::nextScaleChanged, this, &Decoration::recalculate);
    connect(w, &KDecoration3::DecoratedWindow::paletteChanged, this, [this]() {
        updateOutline();
        updateShadow();
        update();
    });

    const auto s = settings();
    connect(s.get(), &KDecoration3::DecorationSettings::borderSizeChanged, this, &Decoration::recalculate);
    connect(s.get(), &KDecoration3::DecorationSettings::fontChanged, this, &Decoration::recalculate);
    connect(s.get(), &KDecoration3::DecorationSettings::spacingChanged, this, &Decoration::recalculate);
    connect(s.get(), &KDecoration3::DecorationSettings::reconfigured, this, &Decoration::reconfigure);
    connect(s.get(), &KDecoration3::DecorationSettings::decorationButtonsLeftChanged, this, &Decoration::updateButtonsGeometry, Qt::QueuedConnection);
    connect(s.get(), &KDecoration3::DecorationSettings::decorationButtonsRightChanged, this, &Decoration::updateButtonsGeometry, Qt::QueuedConnection);

    recalculate();
    return true;
}

void Decoration::reconfigure()
{
    m_config = Config::load();
    recalculate();
}

qreal Decoration::snap(qreal value) const
{
    return KDecoration3::snapToPixelGrid(value, window()->nextScale());
}

bool Decoration::isMaximized() const
{
    return window()->isMaximized();
}

qreal Decoration::cornerRadius() const
{
    return isMaximized() ? 0 : snap(m_config.cornerRadius);
}

qreal Decoration::sideBorder() const
{
    if (isMaximized()) {
        return 0;
    }
    qreal px = 0;
    switch (settings()->borderSize()) {
    case KDecoration3::BorderSize::None:
    case KDecoration3::BorderSize::NoSides:
        px = 0;
        break;
    case KDecoration3::BorderSize::Tiny:
        px = 1;
        break;
    case KDecoration3::BorderSize::Normal:
        px = 3;
        break;
    case KDecoration3::BorderSize::Large:
        px = 5;
        break;
    case KDecoration3::BorderSize::VeryLarge:
        px = 7;
        break;
    case KDecoration3::BorderSize::Huge:
        px = 10;
        break;
    case KDecoration3::BorderSize::VeryHuge:
        px = 14;
        break;
    case KDecoration3::BorderSize::Oversized:
        px = 20;
        break;
    }
    return snap(px);
}

qreal Decoration::frameWidth() const
{
    return window()->width() + 2 * m_side;
}

qreal Decoration::buttonDiameter() const
{
    return snap(std::max<qreal>(10, std::round(settings()->gridUnit() * 0.7)));
}

qreal Decoration::titleBarHeight() const
{
    if (!m_config.titleBar) {
        return 0;
    }
    const auto s = settings();
    const qreal padding = std::max(4, s->smallSpacing()) * 1.6;
    return snap(std::max(s->fontMetrics().height(), buttonDiameter()) + 2 * padding);
}

int Decoration::animationDuration(int milliseconds) const
{
    if (m_config.animationFactor <= 0) {
        return 0;
    }
    return int(milliseconds * m_config.animationFactor);
}

QColor Decoration::accent() const
{
    if (m_config.accent.isValid()) {
        return m_config.accent;
    }
    return window()->palette().color(QPalette::Active, QPalette::Highlight);
}

QColor Decoration::accent2() const
{
    if (m_config.accent2.isValid()) {
        return m_config.accent2;
    }
    // The accent's partner for the glow: up to 70 degrees toward violet, the short way
    // round, so cyan turns blue, orange pink and green blue; a violet turns magenta.
    // The desktop lights and the clock in the bar use the same rule.
    const QColor a = accent();
    const int hue = std::max(0, a.hsvHue());
    const int d = ((270 - hue + 540) % 360) - 180;
    const int shift = std::abs(d) < 20 ? 40 : (d > 0 ? 1 : -1) * std::min(std::abs(d), 70);
    return QColor::fromHsv(((hue + shift) % 360 + 360) % 360, a.hsvSaturation(), a.value());
}

QColor Decoration::titleBarColor() const
{
    const QColor active = window()->color(ColorGroup::Active, ColorRole::TitleBar);
    const QColor inactive = window()->color(ColorGroup::Inactive, ColorRole::TitleBar);
    if (!active.isValid()) {
        return window()->palette().color(QPalette::Window);
    }
    return mix(inactive.isValid() ? inactive : active, active, m_activeProgress);
}

QColor Decoration::foregroundColor() const
{
    const QColor active = window()->color(ColorGroup::Active, ColorRole::Foreground);
    const QColor inactive = window()->color(ColorGroup::Inactive, ColorRole::Foreground);
    if (!active.isValid()) {
        return window()->palette().color(QPalette::WindowText);
    }
    return mix(inactive.isValid() ? inactive : active, active, m_activeProgress);
}

bool Decoration::isLight() const
{
    return titleBarColor().lightnessF() > 0.6;
}

void Decoration::recalculate()
{
    const qreal side = sideBorder();
    m_side = side;
    m_titleHeight = m_config.titleBar ? titleBarHeight() : 0;
    const qreal top = m_config.titleBar ? m_titleHeight : side;
    setBorders(QMarginsF(side, top, side, side));

    if (isMaximized()) {
        setResizeOnlyBorders(QMarginsF());
    } else {
        // Without a visible border the window is still resized from just outside its edge.
        const qreal extra = std::max<qreal>(0, snap(5) - side);
        setResizeOnlyBorders(QMarginsF(extra, m_config.titleBar ? snap(2) : extra, extra, extra));
    }
    setTitleBar(m_config.titleBar ? QRectF(0, 0, frameWidth(), top) : QRectF());
    setBorderRadius(KDecoration3::BorderRadius(cornerRadius()));
    setOpaque(isMaximized());

    updateOutline();
    updateButtonsGeometry();
    updateShadow();
    update();
}

void Decoration::updateButtonsGeometry()
{
    if (!m_leftButtons || !m_rightButtons) {
        return;
    }
    const auto s = settings();
    const qreal height = m_titleHeight;
    const qreal hit = snap(buttonDiameter() + s->smallSpacing() * 1.5);
    const auto buttons = m_leftButtons->buttons() + m_rightButtons->buttons();
    for (KDecoration3::DecorationButton *button : buttons) {
        button->setGeometry(QRectF(0, 0, height > 0 ? hit : 0, height));
    }
    const qreal spacing = snap(s->smallSpacing() * 0.5);
    const qreal margin = snap(s->smallSpacing() * 2) + m_side;
    m_leftButtons->setSpacing(spacing);
    m_rightButtons->setSpacing(spacing);
    m_leftButtons->setPos(QPointF(margin, 0));
    m_rightButtons->setPos(QPointF(frameWidth() - m_rightButtons->geometry().width() - margin, 0));
    update();
}

void Decoration::animateActive()
{
    const qreal target = window()->isActive() ? 1.0 : 0.0;
    updateShadow();
    const int duration = animationDuration(180);
    m_activeAnimation->stop();
    if (duration <= 0) {
        m_activeProgress = target;
        updateOutline();
        update();
        return;
    }
    m_activeAnimation->setStartValue(m_activeProgress);
    m_activeAnimation->setEndValue(target);
    m_activeAnimation->setDuration(duration);
    m_activeAnimation->start();
}

void Decoration::updateOutline()
{
    if (isMaximized()) {
        setBorderOutline(KDecoration3::BorderOutline());
        return;
    }
    const qreal t = m_activeProgress;
    // KWin draws the outline opaque (it ignores the colour's alpha), so a faint line is
    // made by mixing the text colour into the title bar colour instead.
    QColor background = titleBarColor();
    background.setAlpha(255);
    QColor text = foregroundColor();
    text.setAlpha(255);
    const QColor quiet = mix(background, text, isLight() ? 0.28 : 0.2);
    const QColor loud = m_config.outlineWidth > 0 ? accent() : quiet;
    QColor color = mix(quiet, loud, t);
    color.setAlpha(255);
    const qreal from = m_config.inactiveOutline ? 1.0 : 0.0;
    const qreal to = m_config.outlineWidth > 0 ? m_config.outlineWidth : from;
    const qreal width = from + (to - from) * t;
    if (width <= 0.01) {
        setBorderOutline(KDecoration3::BorderOutline());
        return;
    }
    const qreal pixel = KDecoration3::pixelSize(window()->nextScale());
    setBorderOutline(KDecoration3::BorderOutline(std::max(pixel, snap(width)), color, KDecoration3::BorderRadius(cornerRadius())));
}

void Decoration::updateShadow()
{
    const bool active = window()->isActive();
    ShadowParams p;
    p.radius = cornerRadius();
    const qreal strength = m_config.shadowStrength / 255.0;
    p.blur = active ? m_config.shadowSize : m_config.shadowSize * 0.65;
    p.offsetY = std::round(p.blur * (active ? 0.22 : 0.16));
    QColor shade(0, 0, 0);
    shade.setAlphaF(std::clamp(strength * (active ? 1.0 : 0.6) * (isLight() ? 0.7 : 1.0), 0.0, 1.0));
    p.color = shade;
    if (active && m_config.glow && !isMaximized()) {
        const qreal alpha = isLight() ? 0.28 : 0.42;
        QColor one = accent();
        QColor two = accent2();
        one.setAlphaF(alpha);
        two.setAlphaF(alpha);
        p.glow1 = one;
        p.glow2 = two;
        p.glowBlur = std::max<qreal>(8, m_config.shadowSize * 0.55);
    }
    if (p.blur <= 0 && !p.glow1.isValid()) {
        setShadow(nullptr);
        return;
    }

    const QString key = QStringLiteral("%1|%2|%3|%4|%5|%6|%7")
                            .arg(p.radius)
                            .arg(p.blur)
                            .arg(p.offsetY)
                            .arg(p.color.rgba())
                            .arg(p.glow1.isValid() ? p.glow1.rgba() : 0)
                            .arg(p.glow2.isValid() ? p.glow2.rgba() : 0)
                            .arg(p.glowBlur);
    for (const CachedShadow &cached : std::as_const(s_shadows)) {
        if (cached.key == key) {
            setShadow(cached.shadow);
            return;
        }
    }
    QMarginsF padding;
    const QImage image = renderShadow(p, &padding);
    auto shadow = std::make_shared<KDecoration3::DecorationShadow>();
    shadow->setPadding(padding);
    shadow->setInnerShadowRect(QRectF(std::floor(image.width() / 2.0), std::floor(image.height() / 2.0), 1, 1));
    shadow->setShadow(image);
    if (s_shadows.size() >= 8) {
        s_shadows.removeFirst();
    }
    s_shadows.append({key, shadow});
    setShadow(shadow);
}

QRectF Decoration::captionRect() const
{
    const auto s = settings();
    const qreal gap = s->smallSpacing() * 2;
    const qreal height = m_titleHeight;
    const auto visible = [](const QList<KDecoration3::DecorationButton *> &buttons) {
        return std::any_of(buttons.cbegin(), buttons.cend(), [](const KDecoration3::DecorationButton *b) {
            return b->isVisible();
        });
    };
    const bool hasLeft = visible(m_leftButtons->buttons());
    const bool hasRight = visible(m_rightButtons->buttons());
    const qreal width = frameWidth();
    const qreal left = hasLeft ? m_leftButtons->geometry().right() + gap : gap + m_side;
    const qreal right = hasRight ? m_rightButtons->geometry().left() - gap : width - gap - m_side;
    const QRectF available(left, 0, std::max<qreal>(0, right - left), height);
    if (!m_config.centerTitle) {
        return available;
    }
    // Centred on the whole width when the title fits there without touching the buttons.
    QFont font = s->font();
    font.setWeight(QFont::DemiBold);
    const qreal textWidth = QFontMetricsF(font).horizontalAdvance(window()->caption());
    const QRectF full((width - textWidth) / 2, 0, textWidth, height);
    if (full.left() >= available.left() && full.right() <= available.right()) {
        return full;
    }
    return available;
}

void Decoration::paint(QPainter *painter, const QRectF &repaintArea)
{
    if (borderTop() <= 0 && borderLeft() <= 0 && borderBottom() <= 0) {
        return;
    }
    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    painter->setPen(Qt::NoPen);

    // The frame. KWin takes only the title bar and the borders from it; the program covers the rest.
    const qreal radius = cornerRadius();
    painter->setBrush(titleBarColor());
    painter->drawRoundedRect(rect(), radius, radius);

    if (m_config.titleBar && m_titleHeight > 0) {
        const QString caption = window()->caption();
        if (!caption.isEmpty()) {
            QFont font = settings()->font();
            font.setWeight(QFont::DemiBold);
            painter->setFont(font);
            QColor fg = foregroundColor();
            fg.setAlphaF(fg.alphaF() * (0.62 + 0.38 * m_activeProgress));
            painter->setPen(fg);
            const QRectF area = captionRect();
            const QString text = QFontMetricsF(font).elidedText(caption, Qt::ElideRight, area.width());
            const Qt::Alignment align = m_config.centerTitle ? Qt::AlignHCenter : Qt::AlignLeft;
            painter->drawText(area, align | Qt::AlignVCenter | Qt::TextSingleLine, text);
            painter->setPen(Qt::NoPen);
        }
        m_leftButtons->paint(painter, repaintArea);
        m_rightButtons->paint(painter, repaintArea);
    }
    painter->restore();
}

}

#include "ozidecoration.moc"
