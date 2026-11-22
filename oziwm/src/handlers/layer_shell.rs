//! wlr-layer-shell: the bar, dock, launcher, notifications and wallpaper of ozi-shell.

use smithay::{
    delegate_layer_shell,
    desktop::{layer_map_for_output, LayerSurface, PopupKind, WindowSurfaceType},
    output::Output,
    reexports::wayland_server::protocol::{wl_output::WlOutput, wl_surface::WlSurface},
    utils::SERIAL_COUNTER,
    wayland::{
        compositor::with_states,
        shell::{
            wlr_layer::{
                KeyboardInteractivity, Layer, LayerSurface as WlrLayerSurface, LayerSurfaceData,
                WlrLayerShellHandler, WlrLayerShellState,
            },
            xdg::PopupSurface,
        },
    },
};

use crate::OziWm;

impl WlrLayerShellHandler for OziWm {
    fn shell_state(&mut self) -> &mut WlrLayerShellState {
        &mut self.layer_shell_state
    }

    fn new_layer_surface(
        &mut self,
        surface: WlrLayerSurface,
        output: Option<WlOutput>,
        _layer: Layer,
        namespace: String,
    ) {
        let output = output
            .as_ref()
            .and_then(Output::from_resource)
            .or_else(|| self.space.outputs().next().cloned());
        let Some(output) = output else {
            tracing::warn!(%namespace, "layer surface without an output");
            return;
        };
        tracing::info!(%namespace, "layer surface");
        let mut map = layer_map_for_output(&output);
        if let Err(err) = map.map_layer(&LayerSurface::new(surface, namespace)) {
            tracing::warn!(?err, "could not map layer surface");
        }
    }

    fn new_popup(&mut self, _parent: WlrLayerSurface, popup: PopupSurface) {
        if let Err(err) = self.popups.track_popup(PopupKind::Xdg(popup)) {
            tracing::warn!(?err, "could not track layer popup");
        }
    }

    fn layer_destroyed(&mut self, surface: WlrLayerSurface) {
        let had_focus = self
            .seat
            .get_keyboard()
            .and_then(|k| k.current_focus())
            .is_some_and(|f| &f == surface.wl_surface());
        for output in self.space.outputs() {
            let mut map = layer_map_for_output(output);
            let layer = map
                .layers()
                .find(|l| l.layer_surface() == &surface)
                .cloned();
            if let Some(layer) = layer {
                map.unmap_layer(&layer);
            }
        }
        if had_focus {
            let next = self.space.elements().last().cloned();
            self.focus_window(next);
        }
    }
}

delegate_layer_shell!(OziWm);

impl OziWm {
    /// Configure new layer surfaces and keep every layer map arranged.
    /// Returns true when `surface` was a layer surface.
    pub fn handle_layer_commit(&mut self, surface: &WlSurface) -> bool {
        let Some(output) = self
            .space
            .outputs()
            .find(|o| {
                layer_map_for_output(o)
                    .layer_for_surface(surface, WindowSurfaceType::TOPLEVEL)
                    .is_some()
            })
            .cloned()
        else {
            return false;
        };
        let initial_configure_sent = with_states(surface, |states| {
            states
                .data_map
                .get::<LayerSurfaceData>()
                .and_then(|d| d.lock().ok().map(|d| d.initial_configure_sent))
                .unwrap_or(true)
        });
        let zone_before = layer_map_for_output(&output).non_exclusive_zone();
        let focus_now = {
            let mut map = layer_map_for_output(&output);
            map.arrange();
            let layer = map
                .layer_for_surface(surface, WindowSurfaceType::TOPLEVEL)
                .cloned();
            match layer {
                Some(layer) if !initial_configure_sent => {
                    layer.layer_surface().send_configure();
                    false
                }
                Some(layer) => {
                    layer.cached_state().keyboard_interactivity == KeyboardInteractivity::Exclusive
                        && matches!(layer.layer(), Layer::Top | Layer::Overlay)
                }
                None => false,
            }
        };
        // A launcher or lock screen asking for the keyboard gets it at once.
        if focus_now {
            self.focus_layer(surface);
        }
        // The bar or the dock took (or gave back) space: keep windows out of it.
        if layer_map_for_output(&output).non_exclusive_zone() != zone_before {
            self.fit_windows_into_work_area();
        }
        true
    }

    pub fn focus_layer(&mut self, surface: &WlSurface) {
        if self.lock.is_some() {
            return;
        }
        let Some(keyboard) = self.seat.get_keyboard() else {
            return;
        };
        if keyboard.current_focus().as_ref() == Some(surface) {
            return;
        }
        keyboard.set_focus(self, Some(surface.clone()), SERIAL_COUNTER.next_serial());
    }
}
