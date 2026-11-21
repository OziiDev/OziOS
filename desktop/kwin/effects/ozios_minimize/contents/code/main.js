/*
    OziOS Minimize: a minimised window glides into its icon in the dock, quickening
    as it goes; brought back, it comes out of the icon and settles softly.

    The dock tells KWin where each window's icon is (window.iconGeometry). Without
    one (no dock, or the window has no icon there) the window sinks towards the
    bottom of the screen instead. Same group as KWin's Squash and Magic Lamp, so
    only one of them runs.

    SPDX-License-Identifier: MIT
*/
"use strict";

class OziMinimize {
    constructor() {
        effect.configChanged.connect(this.loadConfig.bind(this));
        effect.animationEnded.connect(this.ended.bind(this));
        effects.windowAdded.connect(this.manage.bind(this));
        for (const window of effects.stackingOrder) {
            this.manage(window);
        }
        this.loadConfig();
    }

    loadConfig() {
        this.outTime = animationTime(effect.readConfig("MinimizeDuration", 300) || 300);
        this.inTime = animationTime(effect.readConfig("RestoreDuration", 340) || 340);
    }

    manage(window) {
        window.minimizedChanged.connect(() => {
            if (window.minimized) {
                this.minimized(window);
            } else {
                this.restored(window);
            }
        });
    }

    // Where the window goes: its dock icon, or a small spot low on the screen.
    static target(window) {
        const icon = window.iconGeometry;
        if (icon && icon.width > 0 && icon.height > 0) {
            return icon;
        }
        const g = window.geometry;
        const w = g.width * 0.3;
        const h = g.height * 0.3;
        return { x: g.x + (g.width - w) / 2, y: g.y + g.height + 120, width: w, height: h };
    }

    static motion(window, target) {
        const g = window.geometry;
        return {
            size: { value1: Math.max(1, target.width), value2: Math.max(1, target.height) },
            full: { value1: g.width, value2: g.height },
            away: {
                value1: target.x - g.x - (g.width - target.width) / 2,
                value2: target.y - g.y - (g.height - target.height) / 2
            },
            home: { value1: 0, value2: 0 }
        };
    }

    minimized(window) {
        if (effects.hasActiveFullScreenEffect) {
            return;
        }
        if (window.oziRestore) {
            if (redirect(window.oziRestore, Effect.Backward)) {
                return;
            }
            cancel(window.oziRestore);
            delete window.oziRestore;
        }
        if (window.oziMinimize) {
            cancel(window.oziMinimize);
        }
        const m = OziMinimize.motion(window, OziMinimize.target(window));
        window.setData(Effect.WindowForceBlurRole, true);
        window.oziMinimize = animate({
            window: window,
            duration: this.outTime,
            keepAlive: false,
            animations: [
                { type: Effect.Size, from: m.full, to: m.size, curve: QEasingCurve.InCubic },
                { type: Effect.Translation, from: m.home, to: m.away, curve: QEasingCurve.InCubic },
                { type: Effect.Opacity, from: 1.0, to: 0.0, curve: QEasingCurve.InQuad }
            ]
        });
    }

    restored(window) {
        if (effects.hasActiveFullScreenEffect) {
            return;
        }
        if (window.oziMinimize) {
            if (redirect(window.oziMinimize, Effect.Backward)) {
                return;
            }
            cancel(window.oziMinimize);
            delete window.oziMinimize;
        }
        if (window.oziRestore) {
            cancel(window.oziRestore);
        }
        const m = OziMinimize.motion(window, OziMinimize.target(window));
        window.setData(Effect.WindowForceBlurRole, true);
        window.oziRestore = animate({
            window: window,
            duration: this.inTime,
            keepAlive: false,
            animations: [
                // A spring (OutBack) overshoots by a tenth of the whole way, far too much
                // when the way starts at an icon.
                { type: Effect.Size, from: m.size, to: m.full, curve: QEasingCurve.OutQuint },
                { type: Effect.Translation, from: m.away, to: m.home, curve: QEasingCurve.OutQuint },
                { type: Effect.Opacity, from: 0.0, to: 1.0, curve: QEasingCurve.OutCubic }
            ]
        });
    }

    ended(window, animation) {
        if (animation === window.oziMinimize) {
            delete window.oziMinimize;
        }
        if (animation === window.oziRestore) {
            delete window.oziRestore;
        }
        window.setData(Effect.WindowForceBlurRole, null);
    }
}

new OziMinimize();
