mod compositor;
mod layer_shell;
mod xdg_shell;

use std::os::unix::io::OwnedFd;

use smithay::{
    delegate_data_device, delegate_output, delegate_primary_selection, delegate_seat,
    delegate_dmabuf, delegate_xdg_decoration,
    backend::allocator::dmabuf::Dmabuf,
    reexports::wayland_protocols::xdg::decoration::zv1::server::zxdg_toplevel_decoration_v1::Mode as DecorationMode,
    input::{pointer::CursorImageStatus, Seat, SeatHandler, SeatState},
    reexports::wayland_server::{protocol::wl_surface::WlSurface, Resource},
    wayland::{
        dmabuf::{DmabufGlobal, DmabufHandler, DmabufState, ImportNotifier},
        output::OutputHandler,
        shell::xdg::{decoration::XdgDecorationHandler, ToplevelSurface},
        selection::{
            data_device::{
                set_data_device_focus, ClientDndGrabHandler, DataDeviceHandler, DataDeviceState,
                ServerDndGrabHandler,
            },
            primary_selection::{set_primary_focus, PrimarySelectionHandler, PrimarySelectionState},
            SelectionHandler,
        },
    },
};

use crate::OziWm;

impl SeatHandler for OziWm {
    type KeyboardFocus = WlSurface;
    type PointerFocus = WlSurface;
    type TouchFocus = WlSurface;

    fn seat_state(&mut self) -> &mut SeatState<OziWm> {
        &mut self.seat_state
    }

    fn cursor_image(&mut self, _seat: &Seat<Self>, image: CursorImageStatus) {
        // Nested, the host desktop draws the pointer; on real hardware tty.rs does.
        self.cursor_status = image;
        self.needs_redraw = true;
    }

    fn focus_changed(&mut self, seat: &Seat<Self>, focused: Option<&WlSurface>) {
        // Clipboard offers follow the keyboard, so only the focused client can read them.
        let dh = &self.display_handle;
        let client = focused.and_then(|s| dh.get_client(s.id()).ok());
        set_data_device_focus(dh, seat, client.clone());
        set_primary_focus(dh, seat, client);
    }
}

delegate_seat!(OziWm);

impl SelectionHandler for OziWm {
    type SelectionUserData = ();
}

impl DataDeviceHandler for OziWm {
    fn data_device_state(&self) -> &DataDeviceState {
        &self.data_device_state
    }
}

impl ClientDndGrabHandler for OziWm {}

impl ServerDndGrabHandler for OziWm {
    fn send(&mut self, _mime_type: String, _fd: OwnedFd, _seat: Seat<Self>) {}
}

delegate_data_device!(OziWm);

impl PrimarySelectionHandler for OziWm {
    fn primary_selection_state(&self) -> &PrimarySelectionState {
        &self.primary_selection_state
    }
}

delegate_primary_selection!(OziWm);

impl OutputHandler for OziWm {}

delegate_output!(OziWm);

/// OziOS draws the frames, so every client that asks gets server-side ones.
impl XdgDecorationHandler for OziWm {
    fn new_decoration(&mut self, toplevel: ToplevelSurface) {
        toplevel.with_pending_state(|s| s.decoration_mode = Some(DecorationMode::ServerSide));
        if toplevel.is_initial_configure_sent() {
            toplevel.send_pending_configure();
        }
    }

    fn request_mode(&mut self, toplevel: ToplevelSurface, _mode: DecorationMode) {
        self.new_decoration(toplevel);
    }

    fn unset_mode(&mut self, toplevel: ToplevelSurface) {
        self.new_decoration(toplevel);
    }
}

delegate_xdg_decoration!(OziWm);

impl DmabufHandler for OziWm {
    fn dmabuf_state(&mut self) -> &mut DmabufState {
        &mut self.dmabuf_state
    }

    fn dmabuf_imported(&mut self, _global: &DmabufGlobal, dmabuf: Dmabuf, notifier: ImportNotifier) {
        let imported = self.tty.as_mut().is_some_and(|tty| tty.import_dmabuf(&dmabuf));
        if imported {
            let _ = notifier.successful::<OziWm>();
        } else {
            notifier.failed();
        }
    }
}

delegate_dmabuf!(OziWm);
