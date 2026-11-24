//! Smaller protocols that games and everyday programs expect: locking the
//! pointer (first-person games), raw mouse movement, scaled video surfaces
//! (also needed by xwayland-satellite), window activation, and letting games
//! and remote desktops keep keyboard shortcuts for themselves.

use smithay::{
    delegate_fractional_scale, delegate_keyboard_shortcuts_inhibit, delegate_pointer_constraints,
    delegate_pointer_gestures, delegate_relative_pointer, delegate_single_pixel_buffer, delegate_viewporter,
    delegate_xdg_activation,
    input::pointer::PointerHandle,
    reexports::wayland_server::protocol::wl_surface::WlSurface,
    utils::{Logical, Point},
    wayland::{
        fractional_scale::FractionalScaleHandler,
        keyboard_shortcuts_inhibit::{KeyboardShortcutsInhibitHandler, KeyboardShortcutsInhibitState, KeyboardShortcutsInhibitor},
        pointer_constraints::{with_pointer_constraint, PointerConstraintsHandler},
        xdg_activation::{XdgActivationHandler, XdgActivationState, XdgActivationToken, XdgActivationTokenData},
    },
};

use crate::OziWm;

impl PointerConstraintsHandler for OziWm {
    fn new_constraint(&mut self, surface: &WlSurface, pointer: &PointerHandle<Self>) {
        // A game asks to lock or confine the pointer: it applies at once if the
        // pointer is over it, otherwise when the pointer enters.
        if pointer.current_focus().as_ref() == Some(surface) {
            with_pointer_constraint(surface, pointer, |constraint| {
                if let Some(constraint) = constraint {
                    constraint.activate();
                }
            });
        }
    }

    fn cursor_position_hint(&mut self, surface: &WlSurface, pointer: &PointerHandle<Self>, location: Point<f64, Logical>) {
        // Where the game wants the pointer to be when it lets go of it.
        let active = with_pointer_constraint(surface, pointer, |c| c.is_some_and(|c| c.is_active()));
        if !active {
            return;
        }
        if let Some(origin) = self.surface_origin(surface) {
            pointer.set_location(origin.to_f64() + location);
        }
    }
}
delegate_pointer_constraints!(OziWm);

delegate_relative_pointer!(OziWm);
delegate_viewporter!(OziWm);
delegate_single_pixel_buffer!(OziWm);
delegate_pointer_gestures!(OziWm);

impl FractionalScaleHandler for OziWm {}
delegate_fractional_scale!(OziWm);

impl XdgActivationHandler for OziWm {
    fn activation_state(&mut self) -> &mut XdgActivationState {
        &mut self.xdg_activation_state
    }

    fn request_activation(&mut self, token: XdgActivationToken, token_data: XdgActivationTokenData, surface: WlSurface) {
        // A program hands focus to another window (a link opening the browser,
        // a second instance raising the first). Tokens are honoured for a short while.
        if token_data.timestamp.elapsed().as_secs() < 10
            && let Some(window) = self.window_for_surface(&surface)
        {
            self.focus_window(Some(window));
        }
        self.xdg_activation_state.remove_token(&token);
    }
}
delegate_xdg_activation!(OziWm);

impl KeyboardShortcutsInhibitHandler for OziWm {
    fn keyboard_shortcuts_inhibit_state(&mut self) -> &mut KeyboardShortcutsInhibitState {
        &mut self.keyboard_shortcuts_inhibit_state
    }

    fn new_inhibitor(&mut self, inhibitor: KeyboardShortcutsInhibitor) {
        // Virtual machines and remote desktops get the keys; Super-tap and the
        // console switch still work (see input.rs).
        inhibitor.activate();
    }
}
delegate_keyboard_shortcuts_inhibit!(OziWm);
