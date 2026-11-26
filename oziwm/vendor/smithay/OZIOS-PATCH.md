# Smithay 0.7.0, patched for OziOS

Copied from crates.io (smithay 0.7.0, MIT, see LICENSE.txt) without the
benches and examples. Three changes:

`src/wayland/shell/wlr_layer/handlers.rs`, the layer surface pre-commit hook:
it returns early when the `zwlr_layer_surface_v1` object is no longer alive.

Why: when a client destroys a layer surface, Smithay resets the surface's
layer state (size 0, no anchors) but keeps the pre-commit hook on the
`wl_surface`. Qt (layer-shell-qt) hides a window by destroying the layer
surface and then committing the `wl_surface` once more; the hook then saw
"width 0 without left and right anchors" and killed the client with a
protocol error. In OziOS that ended ozi-shell every time the launcher or the
quick panel closed.

`src/wayland/seat/touch.rs`: `TouchHandle::listens(surface)`, whether the
surface's client has a `wl_touch`.

Why: on a touch screen oziwm sends real touches to programs that listen for
them (scrolling and pinching in Firefox, Qt, GTK) and moves the pointer for the
others, so a finger works everywhere. Smithay keeps that list private.

`src/wayland/text_input/mod.rs`, `text_input_handle.rs` and `src/wayland/seat/keyboard.rs`:
`set_enter_without_ime(true)` makes Smithay send text-input `enter`/`leave` with
the keyboard focus, and keeps track of enabled text inputs, even when no
input-method client is connected.

Why: OziOS's on-screen keyboard is part of the shell and types through the
compositor, not through the input-method protocol. Without `enter` a program
never enables its text input, so oziwm could not tell that a text field was
touched. oziwm turns it on only on touch screens, in the Education edition, or
when the user asks for the keyboard.
