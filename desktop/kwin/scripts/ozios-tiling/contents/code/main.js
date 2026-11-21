// OziOS tiling: the windows of a desktop fill the screen in a spiral of halves with
// gaps between them, as on a tiling desktop, while everything else stays as it is.
//
//   Meta+T   tile the windows of this desktop, or let them go again
//   Meta+F   let the active window float above the others, or tile it again
//
// Each new window takes half of the window in use. Dragging a window onto another
// swaps the two; resizing one moves the line between it and its neighbours. Dialogs,
// windows on every desktop and windows of a fixed size are never tiled. Tiling is
// off on every desktop until Meta+T, unless TileByDefault turns it on everywhere.
// ozios_morph animates the windows into their places.

const config = {};

function readSettings() {
    const number = (key, fallback) => {
        const value = Number(readConfig(key, fallback));
        return isFinite(value) && value >= 0 ? value : fallback;
    };
    config.gap = number("Gap", 10);
    config.outer = number("OuterGap", 12);
    config.byDefault = String(readConfig("TileByDefault", false)) === "true";
    config.textOn = String(readConfig("TextOn", "Tiling on"));
    config.textOff = String(readConfig("TextOff", "Tiling off"));
    config.debug = String(readConfig("Debug", false)) === "true";
}
readSettings();

// With Debug=true in [Script-ozios-tiling], what the script does goes to KWin's log.
function note(text) {
    if (config.debug)
        print("ozios-tiling: " + text);
}

function show(r) {
    return r ? [r.x, r.y, r.width, r.height].map(Math.round).join(",") : "-";
}

// --- the tree of one desktop on one screen ----------------------------------------
// A leaf holds a window; a node splits its rectangle between `a` and `b`, side by
// side when the rectangle is wider than tall, else one above the other; `ratio` is
// the share of `a`.

const spaces = new Map();       // "screen|desktop" -> {output, desktop, on, root}
const home = new Map();         // window id -> the key of the space it is tiled in
const floating = new Map();     // id -> window, for windows let float with Meta+F
const before = new Map();       // window id -> its frame from before it was tiled
const raised = new Set();       // ids of floating windows this script keeps above
const watched = new Set();      // ids of windows whose signals are connected
const placed = new Map();       // window id -> {geometry this script gave it, corrections}
const drags = new Map();        // window id -> "move" or "resize", while the user drags

function id(window) {
    return String(window.internalId);
}

function spaceFor(output, desktop) {
    const key = output.name + "|" + desktop.id;
    let space = spaces.get(key);
    if (!space) {
        space = {key: key, output: output, desktop: desktop, on: config.byDefault, root: null};
        spaces.set(key, space);
    }
    return space;
}

function leaves(node, out) {
    out = out || [];
    if (!node)
        return out;
    if (node.window) {
        out.push(node);
    } else {
        leaves(node.a, out);
        leaves(node.b, out);
    }
    return out;
}

function findLeaf(node, window) {
    return leaves(node).find(leaf => leaf.window === window) || null;
}

function replaceNode(space, old, replacement) {
    const parent = old.parent;
    if (!parent)
        space.root = replacement;
    else if (parent.a === old)
        parent.a = replacement;
    else
        parent.b = replacement;
    replacement.parent = parent;
}

// Put `window` into the space by splitting `target`'s leaf (or the last one) in two.
function insert(space, window, target) {
    const leaf = {window: window, parent: null};
    if (!space.root) {
        space.root = leaf;
        return leaf;
    }
    const all = leaves(space.root);
    const split = (target && all.find(l => l.window === target)) || all[all.length - 1];
    const node = {ratio: 0.5, a: null, b: null, parent: null};
    replaceNode(space, split, node);
    node.a = split;
    node.b = leaf;
    split.parent = node;
    leaf.parent = node;
    return leaf;
}

function remove(space, window) {
    const leaf = findLeaf(space.root, window);
    if (!leaf)
        return;
    if (!leaf.parent) {
        space.root = null;
        return;
    }
    const parent = leaf.parent;
    replaceNode(space, parent, parent.a === leaf ? parent.b : parent.a);
}

// --- geometry ------------------------------------------------------------------------

// The part of the screen the tiles share. A floating panel reserves only its own
// thickness, while its window reaches further, down to where the island is drawn;
// the tiles keep their gap from the island, not from the reserved strip.
function usable(space) {
    const r = workspace.clientArea(KWin.MaximizeArea, space.output, space.desktop);
    let top = r.y, left = r.x, right = r.x + r.width;
    for (const panel of workspace.windowList()) {
        if (!panel.dock || !panel.output || panel.output.name !== space.output.name)
            continue;
        const f = panel.frameGeometry;
        if (f.width >= f.height && f.y <= r.y && f.y + f.height > top && f.y + f.height < r.y + r.height / 3)
            top = f.y + f.height;
        else if (f.height > f.width && f.x <= r.x && f.x + f.width > left && f.x + f.width < r.x + r.width / 3)
            left = f.x + f.width;
        else if (f.height > f.width && f.x + f.width >= right && f.x < right && f.x > r.x + r.width * 2 / 3)
            right = f.x;
    }
    return {x: left, y: top, width: right - left, height: r.y + r.height - top};
}

function area(space) {
    const r = usable(space);
    // Every tile keeps half a gap on each side, so the outer edge needs the rest.
    const inset = config.outer - config.gap / 2;
    return {x: r.x + inset, y: r.y + inset, width: r.width - 2 * inset, height: r.height - 2 * inset};
}

function divide(node, rect) {
    node.rect = rect;
    if (node.window)
        return;
    node.horizontal = rect.width >= rect.height;
    const ratio = Math.min(0.9, Math.max(0.1, node.ratio));
    if (node.horizontal) {
        const w = Math.round(rect.width * ratio);
        divide(node.a, {x: rect.x, y: rect.y, width: w, height: rect.height});
        divide(node.b, {x: rect.x + w, y: rect.y, width: rect.width - w, height: rect.height});
    } else {
        const h = Math.round(rect.height * ratio);
        divide(node.a, {x: rect.x, y: rect.y, width: rect.width, height: h});
        divide(node.b, {x: rect.x, y: rect.y + h, width: rect.width, height: rect.height - h});
    }
}

function frameOf(leaf) {
    const half = config.gap / 2;
    const r = leaf.rect;
    const x = Math.round(r.x + half), y = Math.round(r.y + half);
    return {x: x, y: y, width: Math.round(r.x + r.width - half) - x, height: Math.round(r.y + r.height - half) - y};
}

function same(a, b) {
    return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1 && Math.abs(a.width - b.width) < 1 && Math.abs(a.height - b.height) < 1;
}

function copy(r) {
    return {x: r.x, y: r.y, width: r.width, height: r.height};
}

function maximized(window) {
    return Number(window.maximizeMode || 0) !== 0;
}

// Windows the user holds, or that cover the screen, are left where they are.
function held(window) {
    return window.move || window.resize || window.fullScreen || maximized(window);
}

function give(window, frame) {
    placed.set(id(window), {frame: frame, corrections: 0});
    if (!same(window.frameGeometry, frame)) {
        note("place " + window.caption + " " + show(window.frameGeometry) + " -> " + show(frame));
        window.frameGeometry = frame;
    }
}

function tile(space) {
    if (!space || !space.on || !space.root)
        return;
    divide(space.root, area(space));
    for (const leaf of leaves(space.root)) {
        if (!held(leaf.window))
            give(leaf.window, frameOf(leaf));
    }
}

// --- which windows, and where --------------------------------------------------------

const neverTiled = ["plasmashell", "org.kde.plasmashell", "krunner", "org.kde.krunner", "ksmserver-logout-greeter",
                    "org.kde.polkit-kde-authentication-agent-1", "kwin", "kwin_wayland", "xwaylandvideobridge"];

function tileable(window) {
    if (!window || window.deleted || !window.normalWindow || window.transient || window.dialog || window.specialWindow)
        return false;
    if (window.skipTaskbar || window.onAllDesktops || !window.resizeable || !window.moveable)
        return false;
    if (!window.output || !window.desktops || window.desktops.length !== 1)
        return false;
    if (neverTiled.indexOf(String(window.resourceClass).toLowerCase()) >= 0)
        return false;
    return String(window.caption) !== "Picture-in-Picture";
}

// The space a window belongs in now, or null if it should not be tiled.
function wanted(window) {
    if (!tileable(window) || window.minimized || floating.has(id(window)))
        return null;
    const space = spaceFor(window.output, window.desktops[0]);
    return space.on ? space : null;
}

// Move a window between spaces as its state says. A new tile splits `target`'s tile;
// left out, the window in use; null, the tile added last, which makes a spiral.
function refresh(window, target) {
    const key = id(window);
    const now = home.has(key) ? spaces.get(home.get(key)) : null;
    const next = wanted(window);
    if (now === next)
        return;
    if (now) {
        remove(now, window);
        home.delete(key);
        tile(now);
    }
    note((next ? "tile " : "release ") + window.caption + " at " + show(window.frameGeometry));
    if (next) {
        if (!before.has(key))
            before.set(key, copy(window.frameGeometry));
        if (maximized(window))
            window.setMaximize(false, false);
        const active = workspace.activeWindow;
        insert(next, window, target !== undefined ? target : (active !== window ? active : null));
        home.set(key, next.key);
        tile(next);
    }
}

function forget(window) {
    const key = id(window);
    const space = home.has(key) ? spaces.get(home.get(key)) : null;
    if (space) {
        remove(space, window);
        tile(space);
    }
    for (const map of [home, before, placed, drags, floating])
        map.delete(key);
    for (const set of [raised, watched])
        set.delete(key);
}

// --- what the user does ----------------------------------------------------------------

function currentSpace() {
    const output = workspace.activeScreen;
    const desktop = workspace.currentDesktopForScreen ? workspace.currentDesktopForScreen(output) : workspace.currentDesktop;
    return output && desktop ? spaceFor(output, desktop) : null;
}

function osd(text) {
    callDBus("org.kde.plasmashell", "/org/kde/osdService", "org.kde.osdService", "showText", "view-grid", text);
}

function toggle() {
    const space = currentSpace();
    if (!space)
        return;
    setTiling(space, !space.on);
    osd(space.on ? config.textOn : config.textOff);
}

function setTiling(space, on) {
    if (space.on === on)
        return;
    space.on = on;
    if (on) {
        takeAll(space);
    } else {
        for (const leaf of leaves(space.root)) {
            const key = id(leaf.window);
            home.delete(key);
            placed.delete(key);
            if (before.has(key) && !held(leaf.window))
                leaf.window.frameGeometry = before.get(key);
            before.delete(key);
        }
        space.root = null;
        // Floating means nothing without tiles; those windows stop staying on top.
        floating.forEach((window, key) => {
            if (!window.output || window.output.name !== space.output.name || !window.desktops.length
                || window.desktops[0].id !== space.desktop.id)
                return;
            floating.delete(key);
            if (raised.delete(key))
                window.keepAbove = false;
        });
    }
}

// Tile the open windows: the one in use first, the others spiralling in after it.
function takeAll(only) {
    for (const window of workspace.stackingOrder.slice().reverse()) {
        const space = wanted(window);
        if (space && (!only || space === only) && !home.has(id(window)))
            refresh(window, null);
    }
}

function toggleFloating() {
    const window = workspace.activeWindow;
    if (!tileable(window))
        return;
    const key = id(window);
    if (floating.has(key)) {
        floating.delete(key);
        if (raised.delete(key))
            window.keepAbove = false;
        refresh(window);
        return;
    }
    const space = spaceFor(window.output, window.desktops[0]);
    if (!space.on)
        return;
    floating.set(key, window);
    refresh(window);
    // Above the tiles, at the size it had before, in the middle of the screen.
    const r = workspace.clientArea(KWin.MaximizeArea, space.output, space.desktop);
    const size = before.get(key) || {width: r.width * 0.6, height: r.height * 0.6};
    const width = Math.min(size.width, r.width * 0.9), height = Math.min(size.height, r.height * 0.9);
    window.frameGeometry = {x: Math.round(r.x + (r.width - width) / 2), y: Math.round(r.y + (r.height - height) / 2),
                            width: Math.round(width), height: Math.round(height)};
    before.delete(key);
    if (!window.keepAbove) {
        window.keepAbove = true;
        raised.add(key);
    }
}

// The tile under the pointer, in the space the window was dropped in.
function tileAt(space, point) {
    return leaves(space.root).find(leaf => leaf.rect && point.x >= leaf.rect.x && point.x < leaf.rect.x + leaf.rect.width
                                           && point.y >= leaf.rect.y && point.y < leaf.rect.y + leaf.rect.height) || null;
}

// Move the line that `edge` of `leaf`'s tile lies on to `position`.
function moveLine(leaf, horizontal, end, position) {
    let child = leaf;
    for (let node = leaf.parent; node; child = node, node = node.parent) {
        if (node.horizontal !== horizontal || (end ? node.a !== child : node.b !== child))
            continue;
        const r = node.rect;
        const ratio = horizontal ? (position - r.x) / r.width : (position - r.y) / r.height;
        node.ratio = Math.min(0.9, Math.max(0.1, ratio));
        return;
    }
}

function finished(window) {
    const key = id(window);
    const kind = drags.get(key);
    drags.delete(key);
    const space = home.has(key) ? spaces.get(home.get(key)) : null;
    const leaf = space && findLeaf(space.root, window);
    if (!leaf || !leaf.rect) {
        refresh(window);
        return;
    }
    if (kind === "resize") {
        const g = window.frameGeometry, r = leaf.rect, half = config.gap / 2;
        if (Math.abs(g.x - half - r.x) > 2)
            moveLine(leaf, true, false, g.x - half);
        if (Math.abs(g.x + g.width + half - (r.x + r.width)) > 2)
            moveLine(leaf, true, true, g.x + g.width + half);
        if (Math.abs(g.y - half - r.y) > 2)
            moveLine(leaf, false, false, g.y - half);
        if (Math.abs(g.y + g.height + half - (r.y + r.height)) > 2)
            moveLine(leaf, false, true, g.y + g.height + half);
    } else {
        const other = tileAt(space, workspace.cursorPos);
        if (other && other !== leaf) {
            const mine = leaf.window;
            leaf.window = other.window;
            other.window = mine;
        }
    }
    tile(space);
}

// Put a window back when something other than the user moved it (an X11 program
// restoring its own size, say), but give up on one that keeps insisting.
function moved(window) {
    const key = id(window);
    const given = placed.get(key);
    if (!given || !home.has(key) || held(window) || same(window.frameGeometry, given.frame))
        return;
    if (++given.corrections > 4)
        return;
    note("again " + window.caption + " " + show(window.frameGeometry) + " -> " + show(given.frame));
    window.frameGeometry = given.frame;
}

function watch(window) {
    const key = id(window);
    if (watched.has(key))
        return;
    watched.add(key);
    // Not every kind of window has every signal.
    const on = (signal, slot) => {
        if (window[signal])
            window[signal].connect(slot);
    };
    const again = () => refresh(window);
    const back = () => {
        if (!held(window) && home.has(key))
            tile(spaces.get(home.get(key)));
    };
    on("minimizedChanged", again);
    on("desktopsChanged", again);
    on("outputChanged", again);
    on("maximizedChanged", back);
    on("fullScreenChanged", back);
    on("interactiveMoveResizeStarted", () => drags.set(key, window.resize ? "resize" : "move"));
    on("interactiveMoveResizeFinished", () => finished(window));
    on("frameGeometryChanged", () => moved(window));
}

function adopt(window) {
    watch(window);
    if (window.dock && window.frameGeometryChanged)
        window.frameGeometryChanged.connect(retileAll);   // a panel grew, moved or floats now
    refresh(window);
}

workspace.windowAdded.connect(adopt);
workspace.windowRemoved.connect(forget);
workspace.windowList().forEach(window => {
    watch(window);
    if (window.dock && window.frameGeometryChanged)
        window.frameGeometryChanged.connect(retileAll);
});

// The usable part of a screen changes with panels and screens; tile everything again.
function retileAll() {
    spaces.forEach(space => tile(space));
}
for (const signal of ["screensChanged", "virtualScreenGeometryChanged"]) {
    if (workspace[signal])
        workspace[signal].connect(retileAll);
}
// "Tile every desktop" switched in Look (or `ozi look tiling`): every desktop follows
// at once, the ones already seen and the ones that have windows but were never tiled.
options.configChanged.connect(() => {
    const was = config.byDefault;
    readSettings();
    if (config.byDefault !== was) {
        spaces.forEach(space => setTiling(space, config.byDefault));
        if (config.byDefault)
            takeAll(null);
    }
    retileAll();
});

registerShortcut("OziOS Tiling Toggle", "OziOS: Tile the windows of this desktop", "Meta+T", toggle);
registerShortcut("OziOS Tiling Float", "OziOS: Let the active window float", "Meta+F", toggleFloating);

// Tiling everywhere from the start: take the windows that are already open.
if (config.byDefault)
    takeAll(null);
