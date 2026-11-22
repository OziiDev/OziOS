use std::{
    ffi::OsString,
    path::PathBuf,
    process::Command,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Instant,
};

use smithay::{
    desktop::{layer_map_for_output, PopupManager, Space, Window, WindowSurfaceType},
    input::{keyboard::Keycode, pointer::CursorImageStatus, Seat, SeatState},
    reexports::{
        calloop::{generic::Generic, EventLoop, Interest, LoopHandle, LoopSignal, Mode, PostAction},
        wayland_server::{
            backend::{ClientData, ClientId, DisconnectReason},
            protocol::wl_surface::WlSurface,
            Display, DisplayHandle,
        },
    },
    utils::{Logical, Point, Rectangle, SERIAL_COUNTER},
    wayland::{
        compositor::{CompositorClientState, CompositorState},
        dmabuf::DmabufState,
        output::OutputManagerState,
        selection::{data_device::DataDeviceState, primary_selection::PrimarySelectionState},
        shell::{
            wlr_layer::{Layer as WlrLayer, WlrLayerShellState},
            xdg::{decoration::XdgDecorationState, XdgShellState},
        },
        shm::ShmState,
        socket::ListeningSocketSource,
    },
};

use crate::{
    deco::{self, Hit},
    ipc, keyboard, placement,
    render::{self, Looks},
    theme::{self, Look},
};

/// Session-unique window number shown to the shell over IPC.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WindowId(pub u64);

static NEXT_WINDOW_ID: AtomicU64 = AtomicU64::new(1);

pub fn window_id(window: &Window) -> u64 {
    window
        .user_data()
        .get_or_insert_threadsafe(|| WindowId(NEXT_WINDOW_ID.fetch_add(1, Ordering::Relaxed)))
        .0
}

pub struct OziWm {
    pub start_time: Instant,
    pub socket_name: OsString,
    pub ipc_path: PathBuf,
    pub display_handle: DisplayHandle,
    pub loop_handle: LoopHandle<'static, OziWm>,
    pub loop_signal: LoopSignal,

    pub space: Space<Window>,
    /// Toplevels that exist but have not drawn anything yet; mapped on their first buffer.
    pub unmapped: Vec<Window>,
    pub popups: PopupManager,

    pub compositor_state: CompositorState,
    pub xdg_shell_state: XdgShellState,
    pub shm_state: ShmState,
    pub output_manager_state: OutputManagerState,
    pub seat_state: SeatState<OziWm>,
    pub data_device_state: DataDeviceState,
    pub primary_selection_state: PrimarySelectionState,
    pub xdg_decoration_state: XdgDecorationState,
    pub layer_shell_state: WlrLayerShellState,
    pub seat: Seat<Self>,

    /// Windows sent to the dock; they come back on focus.
    pub minimized: Vec<Window>,
    pub look: Look,
    pub looks: Looks,
    pub font: Option<ab_glyph::FontVec>,
    /// For telling a double click on a title bar from two single ones.
    pub last_title_click: Option<(u64, Instant)>,

    pub dmabuf_state: DmabufState,
    pub cursor_status: CursorImageStatus,
    /// Something changed since the last frame (real hardware only draws then).
    pub needs_redraw: bool,
    pub tty: Option<crate::tty::Tty>,
    /// The X display xwayland-satellite serves, for old X11 programs (Steam, games).
    pub x_display: Option<String>,
    pub session: Option<smithay::backend::session::libseat::LibSeatSession>,

    /// Keys whose press was eaten by a binding; their release is eaten too.
    pub suppressed_keys: Vec<Keycode>,
    /// Super went down and nothing else happened yet: releasing it opens the launcher.
    pub super_alone: bool,
    /// In a nested window the host desktop owns the Super key, so bindings use Alt.
    pub nested: bool,
    pub ipc_subscribers: Vec<ipc::Subscriber>,

    /// 0-based; see workspace.rs.
    pub active_ws: usize,
    /// Windows of the other workspaces and where they were.
    pub hidden: Vec<(Window, Point<i32, Logical>)>,
    pub tiling: [bool; crate::workspace::WORKSPACES],
    /// Window ids in the order they opened: the tiling order.
    pub tile_order: Vec<u64>,
    /// A workspace switch in progress: when, and which way (+1 right, -1 left).
    pub ws_switch: Option<(Instant, i32)>,

    /// Some while the screen is locked.
    pub lock: Option<crate::lock::Lock>,
    pub lock_answers: Option<crate::lock::LockAnswers>,
}

impl OziWm {
    pub fn new(
        event_loop: &mut EventLoop<'static, Self>,
        display: Display<Self>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let dh = display.handle();

        let compositor_state = CompositorState::new::<Self>(&dh);
        let xdg_shell_state = XdgShellState::new::<Self>(&dh);
        let shm_state = ShmState::new::<Self>(&dh, vec![]);
        let output_manager_state = OutputManagerState::new_with_xdg_output::<Self>(&dh);
        let data_device_state = DataDeviceState::new::<Self>(&dh);
        let primary_selection_state = PrimarySelectionState::new::<Self>(&dh);
        let xdg_decoration_state = XdgDecorationState::new::<Self>(&dh);
        let layer_shell_state = WlrLayerShellState::new::<Self>(&dh);

        let mut seat_state = SeatState::new();
        let mut seat: Seat<Self> = seat_state.new_wl_seat(&dh, "seat0");
        let xkb = keyboard::system_layout();
        tracing::info!(layout = %xkb.layout, variant = %xkb.variant, "keyboard");
        seat.add_keyboard(xkb.to_config(), 400, 30)?;
        seat.add_pointer();

        let socket_name = Self::init_wayland_listener(display, event_loop)?;
        let ipc_path = ipc::listen(event_loop.handle(), &socket_name)?;

        Ok(Self {
            start_time: Instant::now(),
            socket_name,
            ipc_path,
            display_handle: dh,
            loop_handle: event_loop.handle(),
            loop_signal: event_loop.get_signal(),
            space: Space::default(),
            unmapped: Vec::new(),
            popups: PopupManager::default(),
            compositor_state,
            xdg_shell_state,
            shm_state,
            output_manager_state,
            seat_state,
            data_device_state,
            primary_selection_state,
            xdg_decoration_state,
            layer_shell_state,
            seat,
            minimized: Vec::new(),
            look: theme::load(),
            looks: Looks::default(),
            font: crate::title::load_font(),
            last_title_click: None,
            dmabuf_state: DmabufState::new(),
            cursor_status: CursorImageStatus::default_named(),
            needs_redraw: true,
            tty: None,
            x_display: None,
            session: None,
            suppressed_keys: Vec::new(),
            super_alone: false,
            nested: true,
            ipc_subscribers: Vec::new(),
            active_ws: 0,
            hidden: Vec::new(),
            tiling: [false; crate::workspace::WORKSPACES],
            tile_order: Vec::new(),
            ws_switch: None,
            lock: None,
            lock_answers: None,
        })
    }

    fn init_wayland_listener(
        display: Display<Self>,
        event_loop: &mut EventLoop<'static, Self>,
    ) -> Result<OsString, Box<dyn std::error::Error>> {
        let listening_socket = ListeningSocketSource::new_auto()?;
        let socket_name = listening_socket.socket_name().to_os_string();
        let handle = event_loop.handle();

        handle.insert_source(listening_socket, |client_stream, _, state| {
            if let Err(err) = state
                .display_handle
                .insert_client(client_stream, Arc::new(ClientState::default()))
            {
                tracing::warn!(?err, "could not accept a client");
            }
        })?;

        handle.insert_source(
            Generic::new(display, Interest::READ, Mode::Level),
            |_, display, state| {
                // SAFETY: the display is never dropped while the event loop runs; this is the
                // pattern Smithay documents for dispatching clients from calloop.
                let display = unsafe { display.get_mut() };
                if let Err(err) = display.dispatch_clients(state) {
                    tracing::warn!(?err, "dispatching clients failed");
                }
                Ok(PostAction::Continue)
            },
        )?;

        Ok(socket_name)
    }

    /// Start a program in this session, like a launcher would.
    pub fn spawn(&self, argv: &[String]) {
        let Some((program, args)) = argv.split_first() else {
            return;
        };
        let mut command = Command::new(program);
        command.args(args);
        self.prepare_child(&mut command);
        match command.spawn() {
            Ok(_) => tracing::info!(?argv, "started"),
            Err(err) => tracing::warn!(?argv, %err, "could not start"),
        }
    }

    /// X11 programs: run xwayland-satellite on a free display, if it is installed.
    pub fn start_xwayland(&mut self) {
        let found = std::env::var_os("PATH")
            .map(|paths| std::env::split_paths(&paths).any(|d| d.join("xwayland-satellite").is_file()))
            .unwrap_or(false);
        if !found {
            tracing::info!("xwayland-satellite not installed: X11 programs will not open");
            return;
        }
        let Some(n) = (0..64).find(|n| {
            !std::path::Path::new(&format!("/tmp/.X11-unix/X{n}")).exists()
                && !std::path::Path::new(&format!("/tmp/.X{n}-lock")).exists()
        }) else {
            return;
        };
        let x_name = format!(":{n}");
        let mut command = Command::new("xwayland-satellite");
        command.arg(&x_name);
        self.prepare_child(&mut command);
        match command.spawn() {
            Ok(_) => {
                tracing::info!(x_display = %x_name, "X11 programs go through xwayland-satellite");
                self.x_display = Some(x_name);
            }
            Err(err) => tracing::warn!(%err, "xwayland-satellite did not start"),
        }
    }

    /// Start a command line through `sh -c` (for `-c` arguments).
    pub fn spawn_shell(&self, line: &str) {
        self.spawn(&["sh".into(), "-c".into(), line.into()]);
    }

    fn prepare_child(&self, command: &mut Command) {
        command
            .env("WAYLAND_DISPLAY", &self.socket_name)
            .env("OZIWM_SOCKET", &self.ipc_path)
            .env("XDG_SESSION_TYPE", "wayland")
            .env("QT_QPA_PLATFORM", "wayland")
            .env("GDK_BACKEND", "wayland,x11");
        // Nested, the host's X display must not leak in; on hardware ours goes out.
        match &self.x_display {
            Some(display) => command.env("DISPLAY", display),
            None => command.env_remove("DISPLAY"),
        };
    }

    /// The client surface under a point: overlay and top layers (bar, dock,
    /// launcher), then windows, then bottom layers and the wallpaper.
    pub fn surface_under(&self, pos: Point<f64, Logical>) -> Option<(WlSurface, Point<f64, Logical>)> {
        let output = self.space.outputs().find(|o| {
            self.space.output_geometry(o).is_some_and(|g| g.to_f64().contains(pos))
        })?;
        let output_geo = self.space.output_geometry(output)?;
        let map = layer_map_for_output(output);
        let in_layer = |layer: WlrLayer| {
            let surface = map.layer_under(layer, pos - output_geo.loc.to_f64())?;
            let layer_loc = map.layer_geometry(surface)?.loc + output_geo.loc;
            surface
                .surface_under(pos - layer_loc.to_f64(), WindowSurfaceType::ALL)
                .map(|(s, p)| (s, (p + layer_loc).to_f64()))
        };
        in_layer(WlrLayer::Overlay)
            .or_else(|| in_layer(WlrLayer::Top))
            .or_else(|| {
                self.space.element_under(pos).and_then(|(window, location)| {
                    window
                        .surface_under(pos - location.to_f64(), WindowSurfaceType::ALL)
                        .map(|(surface, point)| (surface, (point + location).to_f64()))
                })
            })
            .or_else(|| in_layer(WlrLayer::Bottom))
            .or_else(|| in_layer(WlrLayer::Background))
    }

    /// The layer surface (bar, launcher...) at a point on the top layers, if it takes the keyboard.
    pub fn focusable_layer_at(&self, pos: Point<f64, Logical>) -> Option<WlSurface> {
        let output = self.space.outputs().next()?;
        let output_geo = self.space.output_geometry(output)?;
        let map = layer_map_for_output(output);
        [WlrLayer::Overlay, WlrLayer::Top].into_iter().find_map(|layer| {
            map.layer_under(layer, pos - output_geo.loc.to_f64())
                .filter(|l| l.can_receive_keyboard_focus())
                .map(|l| l.wl_surface().clone())
        })
    }

    pub fn window_for_surface(&self, surface: &WlSurface) -> Option<Window> {
        self.space
            .elements()
            .find(|w| w.toplevel().is_some_and(|t| t.wl_surface() == surface))
            .cloned()
    }

    pub fn window_by_id(&self, id: u64) -> Option<Window> {
        self.space
            .elements()
            .chain(self.minimized.iter())
            .chain(self.hidden.iter().map(|(w, _)| w))
            .find(|w| window_id(w) == id)
            .cloned()
    }

    /// The frame part (title bar, button, edge) under the pointer, if no window
    /// content above it is in the way.
    pub fn frame_hit(&self, pos: Point<f64, Logical>) -> Option<(Window, Hit)> {
        for window in self.space.elements().rev() {
            let Some(frame) = render::frame_of(self, window) else {
                continue;
            };
            if let Some(hit) = frame.hit(pos.x, pos.y) {
                return Some((window.clone(), hit));
            }
            if frame.content.contains(pos.x, pos.y) {
                return None;
            }
        }
        None
    }

    pub fn reload_look(&mut self) {
        self.look = theme::load();
        for look in self.looks.values_mut() {
            look.forget_title();
        }
        self.needs_redraw = true;
        tracing::info!(theme = self.look.theme.id, "look reloaded");
    }

    pub fn minimize(&mut self, window: &Window) {
        if !self.space.elements().any(|w| w == window) {
            return;
        }
        let was_focused = self.focused_window().as_ref() == Some(window);
        if let Some(loc) = self.space.element_location(window) {
            window.user_data().insert_if_missing_threadsafe(MinimizedAt::default);
            if let Some(Ok(mut g)) = window.user_data().get::<MinimizedAt>().map(|r| r.0.lock()) {
                *g = Some(Rectangle::new(loc, window.geometry().size));
            }
        }
        self.space.unmap_elem(window);
        self.minimized.push(window.clone());
        ipc::emit_window(self, window, "window-changed");
        if was_focused {
            let next = self.space.elements().last().cloned();
            self.focus_window(next);
        }
    }

    pub fn toggle_maximize(&mut self, window: &Window) {
        use smithay::reexports::wayland_protocols::xdg::shell::server::xdg_toplevel::State;
        let Some(toplevel) = window.toplevel() else {
            return;
        };
        let maximized = toplevel.current_state().states.contains(State::Maximized);
        self.begin_morph(window);
        if maximized {
            let restore = window.user_data().get::<RestoreRect>().and_then(|r| r.0.lock().ok().and_then(|g| *g));
            toplevel.with_pending_state(|s| {
                s.states.unset(State::Maximized);
                s.size = restore.map(|r| r.size);
            });
            toplevel.send_pending_configure();
            if let Some(r) = restore {
                self.space.map_element(window.clone(), r.loc, true);
            }
        } else {
            let Some(loc) = self.space.element_location(window) else {
                return;
            };
            let rect = Rectangle::new(loc, window.geometry().size);
            window.user_data().insert_if_missing_threadsafe(RestoreRect::default);
            if let Some(r) = window.user_data().get::<RestoreRect>()
                && let Ok(mut g) = r.0.lock() {
                    *g = Some(rect);
                }
            let area = self.work_area();
            let title = if render::is_server_side(window) { deco::TITLE_HEIGHT } else { 0 };
            let gap = 8;
            let target = Rectangle::<i32, Logical>::new(
                (area.loc.x + gap, area.loc.y + gap + title).into(),
                (area.size.w - 2 * gap, area.size.h - 2 * gap - title).into(),
            );
            toplevel.with_pending_state(|s| {
                s.states.set(State::Maximized);
                s.size = Some(target.size);
            });
            toplevel.send_pending_configure();
            self.space.map_element(window.clone(), target.loc, true);
        }
        ipc::emit_window(self, window, "window-changed");
    }

    pub fn focused_window(&self) -> Option<Window> {
        let focus = self.seat.get_keyboard()?.current_focus()?;
        self.window_for_surface(&focus)
    }

    /// Raise a window, give it the keyboard and mark it active.
    pub fn focus_window(&mut self, window: Option<Window>) {
        if self.lock.is_some() {
            return;
        }
        let serial = SERIAL_COUNTER.next_serial();
        let Some(keyboard) = self.seat.get_keyboard() else {
            return;
        };
        // On another workspace: go there first.
        if let Some(window) = &window
            && self.hidden.iter().any(|(w, _)| w == window)
        {
            self.switch_workspace(crate::workspace::workspace_of(window));
        }
        if let Some(window) = &window
            && let Some(i) = self.minimized.iter().position(|w| w == window) {
                crate::workspace::set_workspace(window, self.active_ws);
                let window = self.minimized.remove(i);
                let loc = window.user_data().get::<MinimizedAt>()
                    .and_then(|r| r.0.lock().ok().and_then(|g| g.map(|r| r.loc)));
                self.space.map_element(window, loc.unwrap_or_default(), false);
            }
        match &window {
            Some(window) => {
                self.space.raise_element(window, true);
                let surface = window.toplevel().map(|t| t.wl_surface().clone());
                keyboard.set_focus(self, surface, serial);
            }
            None => {
                for w in self.space.elements() {
                    w.set_activated(false);
                }
                keyboard.set_focus(self, Option::<WlSurface>::None, serial);
            }
        }
        for w in self.space.elements() {
            if let Some(toplevel) = w.toplevel() {
                toplevel.send_pending_configure();
            }
        }
        ipc::emit_focus(self, window.as_ref().map(window_id));
    }

    /// Put a new window on screen at a free spot and focus it.
    pub fn map_new_window(&mut self, window: Window) {
        let title = if render::is_server_side(&window) { deco::TITLE_HEIGHT } else { 0 };
        let area = self.work_area();
        // Too big for the screen (minus bar and dock): ask the client to fit.
        let mut size = window.geometry().size;
        let room = smithay::utils::Size::<i32, Logical>::from((area.size.w - 24, area.size.h - title - 24));
        if size.w > room.w || size.h > room.h {
            size = (size.w.min(room.w).max(200), size.h.min(room.h).max(120)).into();
            if let Some(toplevel) = window.toplevel() {
                toplevel.with_pending_state(|s| s.size = Some(size));
                toplevel.send_pending_configure();
            }
        }
        let size = smithay::utils::Size::<i32, Logical>::from((size.w, size.h + title));
        let taken: Vec<(i32, i32)> = self
            .space
            .elements()
            .filter_map(|w| {
                let t = if render::is_server_side(w) { deco::TITLE_HEIGHT } else { 0 };
                self.space.element_location(w).map(|p| (p.x, p.y - t))
            })
            .collect();
        let (x, y) = placement::place(
            (area.loc.x, area.loc.y, area.size.w, area.size.h),
            (size.w, size.h),
            &taken,
        );
        self.space.map_element(window.clone(), (x, y + title), true);
        self.track_new_window(&window);
        ipc::emit_window(self, &window, "window-opened");
        self.focus_window(Some(window));
    }

    /// The screen minus what the bar and dock reserve.
    pub fn work_area(&self) -> Rectangle<i32, Logical> {
        let Some(output) = self.space.outputs().next() else {
            return Rectangle::from_size((1280, 800).into());
        };
        let Some(geo) = self.space.output_geometry(output) else {
            return Rectangle::from_size((1280, 800).into());
        };
        let mut zone = layer_map_for_output(output).non_exclusive_zone();
        zone.loc += geo.loc;
        if zone.size.w <= 0 || zone.size.h <= 0 { geo } else { zone }
    }

    /// The whole screen, for pointer limits and fullscreen.
    pub fn screen(&self) -> Rectangle<i32, Logical> {
        self.space
            .outputs()
            .next()
            .and_then(|o| self.space.output_geometry(o))
            .unwrap_or_else(|| Rectangle::from_size((1280, 800).into()))
    }

    pub fn close_focused(&mut self) {
        if let Some(toplevel) = self.focused_window().and_then(|w| w.toplevel().cloned()) {
            toplevel.send_close();
        }
    }

    /// Give focus to the next window down the stack (simple Mod+Tab).
    pub fn cycle_focus(&mut self) {
        let windows: Vec<Window> = self.space.elements().cloned().collect();
        if windows.len() < 2 {
            return;
        }
        // The stack is bottom to top; the bottom one comes up next.
        self.focus_window(windows.first().cloned());
    }
}

/// Where a window was before it was maximized or minimized.
#[derive(Debug, Default)]
pub struct RestoreRect(pub std::sync::Mutex<Option<Rectangle<i32, Logical>>>);

/// Where a minimized window goes back to.
#[derive(Debug, Default)]
pub struct MinimizedAt(pub std::sync::Mutex<Option<Rectangle<i32, Logical>>>);

#[derive(Default)]
pub struct ClientState {
    pub compositor_state: CompositorClientState,
}

impl ClientData for ClientState {
    fn initialized(&self, _client_id: ClientId) {}
    fn disconnected(&self, _client_id: ClientId, _reason: DisconnectReason) {}
}
