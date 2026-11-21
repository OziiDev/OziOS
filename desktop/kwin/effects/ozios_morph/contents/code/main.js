/*
    OziOS Morph: a window that changes place or size without being dragged flows
    from where it was to where it goes. Maximising and restoring, snapping to a side
    of the screen, the tiling layout making room for a new window, a program moving
    its own window: the frame glides there with a quick start and a soft landing.

    The program draws its new picture at once; the effect stretches it from the old
    frame to the new one. When a window is maximised or restored the old picture
    also fades out, as in KWin's own Maximize effect, which this one replaces.
    Dragging is never animated: the window stays under the pointer.

    SPDX-License-Identifier: MIT
*/
"use strict";

class OziMorph {
    constructor() {
        effect.configChanged.connect(this.loadConfig.bind(this));
        effect.animationEnded.connect(this.ended.bind(this));
        effects.windowAdded.connect(window => this.manage(window, false));
        for (const window of effects.stackingOrder) {
            this.manage(window, true);
        }
        this.loadConfig();
    }

    loadConfig() {
        this.duration = animationTime(effect.readConfig("Duration", 320) || 320);
    }

    manage(window, existing) {
        // A new window is still being placed while it opens; that is not a move.
        window.oziBorn = existing ? 0 : Date.now();
        window.oziResized = 0;
        window.windowFrameGeometryChanged.connect(this.moved.bind(this));
        window.windowMaximizedStateAboutToChange.connect(this.aboutToMaximize.bind(this));
        window.windowFinishUserMovedResized.connect(w => {
            if (w.resize) {
                w.oziResized = Date.now();
            }
        });
    }

    static wanted(window) {
        if (!window.visible || window.minimized || window.fullScreen || window.deleted) {
            return false;
        }
        if (window.windowClass == "plasmashell plasmashell" || window.windowClass == "plasmashell org.kde.plasmashell") {
            return false;
        }
        if (window.popupWindow || window.lockScreen || window.outline || !window.managed) {
            return false;
        }
        return window.normalWindow || window.dialog;
    }

    aboutToMaximize(window) {
        if (!OziMorph.wanted(window) || effects.hasActiveFullScreenEffect) {
            return;
        }
        // The old picture fades out while the new one grows into place.
        if (window.oziFade) {
            cancel(window.oziFade);
        }
        window.oziFade = animate({
            window: window,
            duration: this.duration,
            animations: [{ type: Effect.CrossFadePrevious, from: 0.0, to: 1.0, curve: QEasingCurve.OutCubic }]
        });
    }

    moved(window, oldGeometry) {
        if (!OziMorph.wanted(window) || effects.hasActiveFullScreenEffect) {
            return;
        }
        // Dragged or resized by hand: it follows the pointer.
        if (window.move || window.resize) {
            return;
        }
        const now = Date.now();
        if (now - window.oziBorn < 500 || now - window.oziResized < 300) {
            return;
        }
        const g = window.geometry;
        const dx = g.x - oldGeometry.x;
        const dy = g.y - oldGeometry.y;
        const dw = g.width - oldGeometry.width;
        const dh = g.height - oldGeometry.height;
        if (oldGeometry.width < 2 || oldGeometry.height < 2) {
            return;
        }
        if (Math.abs(dx) + Math.abs(dy) + Math.abs(dw) + Math.abs(dh) < 6) {
            return;
        }
        // A program growing a little where it is (a dialog unfolding, a bigger font) is left alone.
        if (Math.abs(dx) < 1 && Math.abs(dy) < 1 && Math.abs(dw) < 48 && Math.abs(dh) < 48) {
            return;
        }
        if (window.oziMorph) {
            cancel(window.oziMorph);
            delete window.oziMorph;
        }
        window.setData(Effect.WindowForceBlurRole, true);
        window.oziMorph = animate({
            window: window,
            duration: this.duration,
            animations: [{
                type: Effect.Size,
                from: { value1: oldGeometry.width, value2: oldGeometry.height },
                to: { value1: g.width, value2: g.height },
                curve: QEasingCurve.OutQuint
            }, {
                type: Effect.Translation,
                // Size scales around the centre of the new frame; this puts it back where it was.
                from: {
                    value1: oldGeometry.x - g.x - (g.width / 2 - oldGeometry.width / 2),
                    value2: oldGeometry.y - g.y - (g.height / 2 - oldGeometry.height / 2)
                },
                to: { value1: 0, value2: 0 },
                curve: QEasingCurve.OutQuint
            }]
        });
        if (window.oziFade) {
            // Both end on the same frame.
            retarget(window.oziFade, 1.0, this.duration);
        }
    }

    ended(window, animation) {
        if (animation === window.oziMorph) {
            delete window.oziMorph;
        }
        if (animation === window.oziFade) {
            delete window.oziFade;
        }
        if (!window.oziMorph && !window.oziFade) {
            window.setData(Effect.WindowForceBlurRole, null);
        }
    }
}

new OziMorph();
