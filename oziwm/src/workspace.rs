//! Four workspaces and tiling.
//!
//! Only the active workspace's windows are in the Space; the others wait in
//! `hidden` with their places. A tiled workspace lays its windows out with
//! `layout::dwindle`, in the order they were opened; floating windows (Super+F)
//! stay where they are.

use std::{
    sync::atomic::{AtomicBool, AtomicUsize, Ordering},
    time::Instant,
};

use smithay::{
    desktop::Window,
    reexports::wayland_protocols::xdg::shell::server::xdg_toplevel::State as XdgState,
    utils::{Logical, Point},
};

use crate::{
    deco::{self, Rect},
    ipc, layout, render,
    state::window_id,
    OziWm,
};

pub const WORKSPACES: usize = 4;

#[derive(Debug, Default)]
struct WsTag(AtomicUsize);

#[derive(Debug, Default)]
struct Floating(AtomicBool);

pub fn workspace_of(window: &Window) -> usize {
    window
        .user_data()
        .get::<WsTag>()
        .map(|t| t.0.load(Ordering::Relaxed))
        .unwrap_or(0)
}

pub fn set_workspace(window: &Window, ws: usize) {
    window.user_data().insert_if_missing_threadsafe(WsTag::default);
    if let Some(tag) = window.user_data().get::<WsTag>() {
        tag.0.store(ws, Ordering::Relaxed);
    }
}

pub fn is_floating(window: &Window) -> bool {
    window
        .user_data()
        .get::<Floating>()
        .is_some_and(|f| f.0.load(Ordering::Relaxed))
}

fn set_floating(window: &Window, floating: bool) {
    window.user_data().insert_if_missing_threadsafe(Floating::default);
    if let Some(f) = window.user_data().get::<Floating>() {
        f.0.store(floating, Ordering::Relaxed);
    }
}

fn has_state(window: &Window, state: XdgState) -> bool {
    window
        .toplevel()
        .is_some_and(|t| t.current_state().states.contains(state))
}

impl OziWm {
    pub fn switch_workspace(&mut self, to: usize) {
        if to >= WORKSPACES || to == self.active_ws {
            return;
        }
        let from = self.active_ws;
        let leaving: Vec<Window> = self.space.elements().cloned().collect();
        for window in leaving {
            let loc = self.space.element_location(&window).unwrap_or_default();
            self.space.unmap_elem(&window);
            self.hidden.push((window, loc));
        }
        let (coming, staying): (Vec<_>, Vec<_>) =
            std::mem::take(&mut self.hidden).into_iter().partition(|(w, _)| workspace_of(w) == to);
        self.hidden = staying;
        for (window, loc) in coming {
            self.space.map_element(window, loc, false);
        }
        self.active_ws = to;
        self.ws_switch = Some((Instant::now(), if to > from { 1 } else { -1 }));
        let top = self.space.elements().last().cloned();
        self.focus_window(top);
        self.needs_redraw = true;
        ipc::emit_workspace(self, to);
    }

    pub fn move_to_workspace(&mut self, window: &Window, to: usize) {
        if to >= WORKSPACES || workspace_of(window) == to {
            return;
        }
        set_workspace(window, to);
        if let Some(loc) = self.space.element_location(window) {
            self.space.unmap_elem(window);
            self.hidden.push((window.clone(), loc));
            let top = self.space.elements().last().cloned();
            self.focus_window(top);
        }
        self.retile();
        ipc::emit_window(self, window, "window-changed");
        ipc::emit_workspace(self, self.active_ws);
    }

    pub fn toggle_tiling(&mut self) {
        let ws = self.active_ws;
        self.tiling[ws] = !self.tiling[ws];
        if self.tiling[ws] {
            self.retile();
        } else {
            // Untile: everyone floats again where they are, without the tiled edges.
            let windows: Vec<Window> = self.space.elements().cloned().collect();
            for window in windows {
                if let Some(t) = window.toplevel() {
                    t.with_pending_state(|s| {
                        for edge in [XdgState::TiledLeft, XdgState::TiledRight, XdgState::TiledTop, XdgState::TiledBottom] {
                            s.states.unset(edge);
                        }
                    });
                    t.send_pending_configure();
                }
            }
        }
        tracing::info!(workspace = ws + 1, on = self.tiling[ws], "tiling");
        ipc::emit_workspace(self, ws);
    }

    pub fn toggle_floating(&mut self, window: &Window) {
        set_floating(window, !is_floating(window));
        self.retile();
    }

    /// Lay out the active workspace if it is tiled.
    pub fn retile(&mut self) {
        if !self.tiling[self.active_ws] {
            return;
        }
        let area = self.work_area();
        let area = Rect::new(area.loc.x, area.loc.y, area.size.w, area.size.h);
        let order = self.tile_order.clone();
        let windows: Vec<Window> = order
            .iter()
            .filter_map(|id| self.space.elements().find(|w| window_id(w) == *id).cloned())
            .filter(|w| !is_floating(w) && !has_state(w, XdgState::Fullscreen) && !has_state(w, XdgState::Maximized))
            .collect();
        let rects = layout::dwindle(area, windows.len());
        for (window, outer) in windows.iter().zip(rects) {
            self.place_window(window, outer, true);
        }
    }

    /// Put a window's frame (title bar included) at `outer`, telling the client its new size.
    pub fn place_window(&mut self, window: &Window, outer: Rect, tiled: bool) {
        let title = if render::is_server_side(window) { deco::TITLE_HEIGHT } else { 0 };
        let content = Rect::new(outer.x, outer.y + title, outer.w, (outer.h - title).max(1));
        self.begin_morph(window);
        if let Some(t) = window.toplevel() {
            t.with_pending_state(|s| {
                s.size = Some((content.w, content.h).into());
                for edge in [XdgState::TiledLeft, XdgState::TiledRight, XdgState::TiledTop, XdgState::TiledBottom] {
                    if tiled {
                        s.states.set(edge);
                    } else {
                        s.states.unset(edge);
                    }
                }
            });
            t.send_pending_configure();
        }
        self.space
            .map_element(window.clone(), Point::<i32, Logical>::from((content.x, content.y)), false);
        self.needs_redraw = true;
    }

    /// Remember where a window is drawn now, so its next move can flow from here.
    pub fn begin_morph(&mut self, window: &Window) {
        if self.look.animation_speed <= 0.0 {
            return;
        }
        let Some(frame) = render::frame_of(self, window) else {
            return;
        };
        let id = window_id(window);
        let now = Instant::now();
        if let Some(look) = self.looks.get_mut(&id) {
            look.morph = Some((frame.outer(), now));
        }
    }

    /// A new window joins the tiling order of its workspace.
    pub fn track_new_window(&mut self, window: &Window) {
        set_workspace(window, self.active_ws);
        self.tile_order.push(window_id(window));
        self.retile();
    }

    pub fn forget_window(&mut self, id: u64) {
        self.tile_order.retain(|w| *w != id);
        self.hidden.retain(|(w, _)| window_id(w) != id);
        self.retile();
    }

    pub fn workspaces_json(&self) -> serde_json::Value {
        let all = self
            .space
            .elements()
            .chain(self.hidden.iter().map(|(w, _)| w))
            .chain(self.minimized.iter());
        let mut counts = [0usize; WORKSPACES];
        for w in all {
            counts[workspace_of(w).min(WORKSPACES - 1)] += 1;
        }
        serde_json::Value::Array(
            (0..WORKSPACES)
                .map(|i| {
                    serde_json::json!({
                        "index": i + 1,
                        "active": i == self.active_ws,
                        "windows": counts[i],
                        "tiling": self.tiling[i],
                    })
                })
                .collect(),
        )
    }
}
