# Smithay 0.7.0, patched for OziOS

Copied from crates.io (smithay 0.7.0, MIT, see LICENSE.txt) without the
benches and examples. One change:

`src/wayland/shell/wlr_layer/handlers.rs`, the layer surface pre-commit hook:
it returns early when the `zwlr_layer_surface_v1` object is no longer alive.

Why: when a client destroys a layer surface, Smithay resets the surface's
layer state (size 0, no anchors) but keeps the pre-commit hook on the
`wl_surface`. Qt (layer-shell-qt) hides a window by destroying the layer
surface and then committing the `wl_surface` once more; the hook then saw
"width 0 without left and right anchors" and killed the client with a
protocol error. In OziOS that ended ozi-shell every time the launcher or the
quick panel closed.
