/*
    SPDX-License-Identifier: MIT
*/
#include "ozishadow.h"

#include <QLinearGradient>
#include <QPainter>

#include <algorithm>
#include <cmath>

namespace Ozi
{

namespace
{

// Widths of n box blurs that together come close to a Gaussian of the given sigma.
void boxesForGauss(qreal sigma, int n, int *sizes)
{
    const qreal ideal = std::sqrt((12 * sigma * sigma / n) + 1);
    int lower = int(std::floor(ideal));
    if (lower % 2 == 0) {
        --lower;
    }
    const int upper = lower + 2;
    const qreal m = (12 * sigma * sigma - n * lower * lower - 4 * n * lower - 3 * n) / (-4 * lower - 4);
    const int count = int(std::round(m));
    for (int i = 0; i < n; ++i) {
        sizes[i] = i < count ? lower : upper;
    }
}

inline quint32 pack(int a, int r, int g, int b)
{
    return (quint32(a) << 24) | (quint32(r) << 16) | (quint32(g) << 8) | quint32(b);
}

// One pass along rows (step 1) or columns (step = row length); outside the image is transparent.
void boxBlurPass(const quint32 *src, quint32 *dst, int lines, int length, int lineStride, int step, int radius)
{
    const int window = 2 * radius + 1;
    for (int line = 0; line < lines; ++line) {
        const quint32 *s = src + line * lineStride;
        quint32 *d = dst + line * lineStride;
        int sa = 0, sr = 0, sg = 0, sb = 0;
        for (int i = 0; i <= radius && i < length; ++i) {
            const quint32 p = s[i * step];
            sa += p >> 24;
            sr += (p >> 16) & 0xff;
            sg += (p >> 8) & 0xff;
            sb += p & 0xff;
        }
        for (int x = 0; x < length; ++x) {
            d[x * step] = pack(sa / window, sr / window, sg / window, sb / window);
            const int out = x - radius;
            if (out >= 0) {
                const quint32 p = s[out * step];
                sa -= p >> 24;
                sr -= (p >> 16) & 0xff;
                sg -= (p >> 8) & 0xff;
                sb -= p & 0xff;
            }
            const int in = x + radius + 1;
            if (in < length) {
                const quint32 p = s[in * step];
                sa += p >> 24;
                sr += (p >> 16) & 0xff;
                sg += (p >> 8) & 0xff;
                sb += p & 0xff;
            }
        }
    }
}

} // namespace

void gaussianBlur(QImage &image, qreal sigma)
{
    if (sigma < 0.5 || image.isNull()) {
        return;
    }
    if (image.format() != QImage::Format_ARGB32_Premultiplied) {
        image = image.convertToFormat(QImage::Format_ARGB32_Premultiplied);
    }
    const int w = image.width();
    const int h = image.height();
    // Rows of a QImage are padded to 4 bytes, which a 32-bit format already is.
    const int stride = image.bytesPerLine() / 4;
    QImage scratch(image.size(), QImage::Format_ARGB32_Premultiplied);
    auto *a = reinterpret_cast<quint32 *>(image.bits());
    auto *b = reinterpret_cast<quint32 *>(scratch.bits());
    int sizes[3];
    boxesForGauss(sigma, 3, sizes);
    for (int i = 0; i < 3; ++i) {
        const int radius = (sizes[i] - 1) / 2;
        if (radius < 1) {
            continue;
        }
        boxBlurPass(a, b, h, w, stride, 1, radius); // rows: image -> scratch
        boxBlurPass(b, a, w, h, 1, stride, radius); // columns: scratch -> image
    }
}

QImage renderShadow(const ShadowParams &params, QMarginsF *padding)
{
    const qreal radius = std::max<qreal>(0, params.radius);
    const int box = int(std::ceil(2 * radius)) + 4;
    const qreal sigma = std::max<qreal>(1, params.blur / 2.4);
    const bool glow = params.glow1.isValid() && params.glow1.alpha() > 0;
    const qreal glowSigma = std::max<qreal>(1, params.glowBlur / 2.4);
    const int spread = int(std::ceil(3 * std::max(sigma, glow ? glowSigma : 0.0)));
    const int pad = spread + int(std::ceil(std::abs(params.offsetY)));
    const int size = box + 2 * pad;

    QImage image(size, size, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::transparent);
    const QRectF boxRect(pad, pad, box, box);

    if (params.color.isValid() && params.color.alpha() > 0) {
        QPainter painter(&image);
        painter.setRenderHint(QPainter::Antialiasing);
        painter.setPen(Qt::NoPen);
        painter.setBrush(params.color);
        painter.drawRoundedRect(boxRect.translated(0, params.offsetY), radius, radius);
        painter.end();
        gaussianBlur(image, sigma);
    }

    if (glow) {
        QImage halo(image.size(), QImage::Format_ARGB32_Premultiplied);
        halo.fill(Qt::transparent);
        QPainter painter(&halo);
        painter.setRenderHint(QPainter::Antialiasing);
        QLinearGradient gradient(boxRect.topLeft(), boxRect.bottomRight());
        gradient.setColorAt(0, params.glow1);
        gradient.setColorAt(1, params.glow2.isValid() ? params.glow2 : params.glow1);
        painter.setPen(Qt::NoPen);
        painter.setBrush(gradient);
        painter.drawRoundedRect(boxRect, radius, radius);
        painter.end();
        gaussianBlur(halo, glowSigma);
        QPainter over(&image);
        over.drawImage(0, 0, halo);
    }

    QPainter cut(&image);
    cut.setRenderHint(QPainter::Antialiasing);
    cut.setCompositionMode(QPainter::CompositionMode_DestinationOut);
    cut.setPen(Qt::NoPen);
    cut.setBrush(Qt::black);
    cut.drawRoundedRect(boxRect, radius, radius);
    cut.end();

    if (padding) {
        *padding = QMarginsF(pad, pad, pad, pad);
    }
    return image;
}

}
