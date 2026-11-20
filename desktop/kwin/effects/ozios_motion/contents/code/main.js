/*
    OziOS Motion: windows arrive from depth and leave into it.

    Opening, a window rises a little, grows from 90% with a slight overshoot and
    fades in; closing, it sinks, shrinks and fades. Built on KWin's scripted
    effect API in the same way as KWin's own Scale effect, which it replaces
    (both are in the "toplevel-open-close-animation" group, so only one runs).
    Only transforms and opacity are animated, which the GPU does for free.

    SPDX-License-Identifier: MIT
*/
"use strict";

// Windows that other effects animate, or that must never move.
const skipped = {
    "ksmserver ksmserver": [],
    "ksmserver-logout-greeter ksmserver-logout-greeter": [],
    "ksplashqml ksplashqml": [],
    "spectacle org.kde.spectacle": ["region-editor"],
};

class OziMotion {
    constructor() {
        effect.configChanged.connect(this.loadConfig.bind(this));
        effect.animationEnded.connect(this.cleanup.bind(this));
        effects.windowAdded.connect(this.opened.bind(this));
        effects.windowClosed.connect(this.closed.bind(this));
        effects.windowDataChanged.connect(this.dataChanged.bind(this));
        this.loadConfig();
    }

    loadConfig() {
        this.openTime = animationTime(effect.readConfig("OpenDuration", 300) || 300);
        this.closeTime = animationTime(effect.readConfig("CloseDuration", 220) || 220);
        this.depth = effect.readConfig("Depth", 18);
    }

    static wanted(window) {
        // plasmashell owns panels and popups as well as a few real windows; only the
        // decorated ones (settings dialogs) are windows in the usual sense.
        if (window.windowClass == "plasmashell plasmashell" || window.windowClass == "plasmashell org.kde.plasmashell") {
            return window.hasDecoration;
        }
        const tags = skipped[window.windowClass];
        if (tags && (tags.length === 0 || tags.includes(window.tag))) {
            return false;
        }
        if (window.hasDecoration) {
            return true;
        }
        if (window.popupWindow || window.lockScreen || window.outline || !window.managed) {
            return false;
        }
        return window.normalWindow || window.dialog;
    }

    forceRoles(window) {
        window.setData(Effect.WindowForceBlurRole, true);
    }

    cleanup(window) {
        window.setData(Effect.WindowForceBlurRole, null);
    }

    opened(window) {
        if (effects.hasActiveFullScreenEffect || !OziMotion.wanted(window) || !window.visible) {
            return;
        }
        if (effect.isGrabbed(window, Effect.WindowAddedGrabRole)) {
            return;
        }
        // Dialogs are small and frequent: a shorter, flatter arrival.
        const dialog = window.dialog || window.modal;
        this.forceRoles(window);
        window.oziOpen = animate({
            window: window,
            duration: dialog ? this.openTime * 0.8 : this.openTime,
            animations: [
                { type: Effect.Scale, from: dialog ? 0.95 : 0.9, curve: QEasingCurve.OutBack },
                { type: Effect.Opacity, from: 0, curve: QEasingCurve.OutCubic },
                { type: Effect.Translation, from: { value1: 0, value2: dialog ? this.depth / 2 : this.depth },
                  to: { value1: 0, value2: 0 }, curve: QEasingCurve.OutCubic }
            ]
        });
    }

    closed(window) {
        if (effects.hasActiveFullScreenEffect || !OziMotion.wanted(window)) {
            return;
        }
        if (!window.visible || window.skipsCloseAnimation) {
            return;
        }
        if (effect.isGrabbed(window, Effect.WindowClosedGrabRole)) {
            return;
        }
        if (window.oziOpen) {
            cancel(window.oziOpen);
            delete window.oziOpen;
        }
        this.forceRoles(window);
        window.oziClose = animate({
            window: window,
            duration: this.closeTime,
            animations: [
                { type: Effect.Scale, to: 0.92, curve: QEasingCurve.InCubic },
                { type: Effect.Opacity, to: 0, curve: QEasingCurve.InQuad },
                { type: Effect.Translation, from: { value1: 0, value2: 0 },
                  to: { value1: 0, value2: this.depth * 0.6 }, curve: QEasingCurve.InCubic }
            ]
        });
    }

    // Another effect took the window over: stop ours.
    dataChanged(window, role) {
        if (role == Effect.WindowAddedGrabRole) {
            if (window.oziOpen && effect.isGrabbed(window, role)) {
                cancel(window.oziOpen);
                delete window.oziOpen;
                this.cleanup(window);
            }
        } else if (role == Effect.WindowClosedGrabRole) {
            if (window.oziClose && effect.isGrabbed(window, role)) {
                cancel(window.oziClose);
                delete window.oziClose;
                this.cleanup(window);
            }
        }
    }
}

new OziMotion();
