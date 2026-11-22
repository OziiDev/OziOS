use smithay::{
    backend::renderer::utils::on_commit_buffer_handler,
    delegate_compositor, delegate_shm,
    reexports::wayland_server::{
        protocol::{wl_buffer, wl_surface::WlSurface},
        Client,
    },
    wayland::{
        buffer::BufferHandler,
        compositor::{get_parent, is_sync_subsurface, CompositorClientState, CompositorHandler, CompositorState},
        shm::{ShmHandler, ShmState},
    },
};

use crate::{grabs::resize_grab, state::ClientState, OziWm};

impl CompositorHandler for OziWm {
    fn compositor_state(&mut self) -> &mut CompositorState {
        &mut self.compositor_state
    }

    fn client_compositor_state<'a>(&self, client: &'a Client) -> &'a CompositorClientState {
        // Every client is inserted with ClientState in state.rs.
        &client
            .get_data::<ClientState>()
            .expect("client without ClientState")
            .compositor_state
    }

    fn commit(&mut self, surface: &WlSurface) {
        on_commit_buffer_handler::<Self>(surface);
        self.needs_redraw = true;

        if !is_sync_subsurface(surface) {
            let mut root = surface.clone();
            while let Some(parent) = get_parent(&root) {
                root = parent;
            }
            // Unmapped windows too: their size is only known after on_commit.
            let window = self.window_for_surface(&root).or_else(|| {
                self.unmapped
                    .iter()
                    .find(|w| w.toplevel().is_some_and(|t| t.wl_surface() == &root))
                    .cloned()
            });
            if let Some(window) = window {
                window.on_commit();
            }
        }

        if self.handle_layer_commit(surface) {
            return;
        }
        self.handle_xdg_commit(surface);
        resize_grab::handle_commit(&mut self.space, surface);
    }
}

impl BufferHandler for OziWm {
    fn buffer_destroyed(&mut self, _buffer: &wl_buffer::WlBuffer) {}
}

impl ShmHandler for OziWm {
    fn shm_state(&self) -> &ShmState {
        &self.shm_state
    }
}

delegate_compositor!(OziWm);
delegate_shm!(OziWm);
