/*
    The shadow (and the glow) KWin draws around a window: one small image,
    stretched along the edges.

    SPDX-License-Identifier: MIT
*/
#pragma once

#include <QColor>
#include <QImage>
#include <QMarginsF>

namespace Ozi
{

struct ShadowParams {
    qreal radius = 10; // the window's corner radius
    qreal blur = 28; // how far the shadow spreads
    qreal offsetY = 6; // light comes from above
    QColor color; // shadow colour; its alpha is the strength
    QColor glow1; // glow colours, top left and bottom right; invalid: no glow
    QColor glow2;
    qreal glowBlur = 14;
};

// The image is a rounded box with its shadow; the box itself is cut out, so nothing
// shows through a translucent window. padding receives where the box sits.
QImage renderShadow(const ShadowParams &params, QMarginsF *padding);

// Approximates a Gaussian blur with three box blurs; the image is premultiplied ARGB32.
void gaussianBlur(QImage &image, qreal sigma);

}
