//! Window snapping: Super+Left/Right fill half the screen, Super+Up fills it,
//! Super+Down gives the old size back (or minimizes). Dragging a window to the
//! left or right edge shows where it will go, and letting go snaps it there;
//! to the top edge maximizes. Super+D shows the desktop and brings it back.

use std::sync::Mutex;

use smithay::{
    desktop::Window,
    reexports::wayland_protocols::xdg::shell::server::xdg_toplevel::State as XdgState,
    utils::{Logical, Point, Rectangle},
};

use crate::{
    deco::Rect,
    ipc,
    state::{window_id, RestoreRect},
    OziWm,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Snap {
    Left,
    Right,
    Full,
}

/// Which side a window is snapped to, if any.
#[derive(Debug, Default)]
pub struct Snapped(pub Mutex<Option<Snap>>);

pub fn snapped(window: &Window) -> Option<Snap> {
    window.user_data().get::<Snapped>().and_then(|s| s.0.lock().ok().and_then(|g| *g))
}

fn set_snapped(window: &Window, snap: Option<Snap>) {
    window.user_data().insert_if_missing_threadsafe(Snapped::default);
    if let Some(Ok(mut g)) = window.user_data().get::<Snapped>().map(|s| s.0.lock()) {
        *g = snap;
    }
}

/// The outer rectangle (frame included) a snapped window takes in the work area.
pub fn target(area: Rectangle<i32, Logical>, snap: Snap, gap: i32) -> Rect {
    let (x, y, w, h) = (area.loc.x + gap, area.loc.y + gap, area.size.w - 2 * gap, area.size.h - 2 * gap);
    match snap {
        Snap::Full => Rect::new(x, y, w, h),
        Snap::Left => Rect::new(x, y, (w - gap) / 2, h),
        Snap::Right => {
            let half = (w - gap) / 2;
            Rect::new(x + w - half, y, half, h)
        }
    }
}

/// Where a dragged window would snap with the pointer at `pos` on `screen`.
pub fn edge_snap(screen: Rectangle<i32, Logical>, pos: Point<f64, Logical>) -> Option<Snap> {
    let near = 3.0;
    if pos.x <= screen.loc.x as f64 + near {
        Some(Snap::Left)
    } else if pos.x >= (screen.loc.x + screen.size.w) as f64 - 1.0 - near {
        Some(Snap::Right)
    } else if pos.y <= screen.loc.y as f64 + near {
        Some(Snap::Full)
    } else {
        None
    }
}

pub const GAP: i32 = 8;

impl OziWm {
    fn remember_size(&self, window: &Window) {
        if snapped(window).is_some() || is_maximized(window) {
            return;
        }
        let Some(loc) = self.space.element_location(window) else {
            return;
        };
        window.user_data().insert_if_missing_threadsafe(RestoreRect::default);
        if let Some(Ok(mut g)) = window.user_data().get::<RestoreRect>().map(|r| r.0.lock()) {
            *g = Some(Rectangle::new(loc, window.geometry().size));
        }
    }

    pub fn snap_window(&mut self, window: &Window, snap: Snap) {
        if snap == Snap::Full {
            if !is_maximized(window) {
                if snapped(window).is_some() {
                    self.unsnap(window);
                }
                self.toggle_maximize(window);
            }
            return;
        }
        if is_maximized(window) {
            self.toggle_maximize(window);
        }
        self.remember_size(window);
        let rect = target(self.work_area(), snap, GAP);
        self.place_window(window, rect, true);
        set_snapped(window, Some(snap));
        self.focus_window(Some(window.clone()));
        ipc::emit_window(self, window, "window-changed");
    }

    /// Back to the size and place it had before it was snapped.
    pub fn unsnap(&mut self, window: &Window) {
        if snapped(window).is_none() {
            return;
        }
        set_snapped(window, None);
        let restore = window.user_data().get::<RestoreRect>().and_then(|r| r.0.lock().ok().and_then(|g| *g));
        if let Some(t) = window.toplevel() {
            t.with_pending_state(|s| {
                for edge in [XdgState::TiledLeft, XdgState::TiledRight, XdgState::TiledTop, XdgState::TiledBottom] {
                    s.states.unset(edge);
                }
                s.size = restore.map(|r| r.size);
            });
            t.send_pending_configure();
        }
        if let Some(r) = restore {
            self.begin_morph(window);
            self.space.map_element(window.clone(), r.loc, true);
        }
        ipc::emit_window(self, window, "window-changed");
    }

    /// Super+Left / Super+Right: snap; pressed again on the same side, let go.
    pub fn snap_focused(&mut self, snap: Snap) {
        let Some(window) = self.focused_window() else {
            return;
        };
        if snapped(&window) == Some(snap) {
            self.unsnap(&window);
        } else {
            self.snap_window(&window, snap);
        }
    }

    /// Super+Down: a snapped or maximized window gets its size back; otherwise it is minimized.
    pub fn shrink_focused(&mut self) {
        let Some(window) = self.focused_window() else {
            return;
        };
        if is_maximized(&window) {
            self.toggle_maximize(&window);
        } else if snapped(&window).is_some() {
            self.unsnap(&window);
        } else {
            self.minimize(&window);
        }
    }

    /// Super+D: minimize every window of this desktop; again, bring them back.
    pub fn toggle_show_desktop(&mut self) {
        if !self.desktop_shown.is_empty() {
            let ids = std::mem::take(&mut self.desktop_shown);
            for id in ids.iter().rev() {
                if let Some(w) = self.window_by_id(*id)
                    && self.minimized.contains(&w)
                {
                    self.focus_window(Some(w));
                }
            }
            return;
        }
        let windows: Vec<Window> = self.space.elements().cloned().collect();
        if windows.is_empty() {
            return;
        }
        self.desktop_shown = windows.iter().map(window_id).collect();
        for w in &windows {
            self.minimize(w);
        }
    }

    /// While a window is dragged: the snap it would get, shown as a preview.
    pub fn drag_preview(&mut self, pos: Point<f64, Logical>) -> Option<Snap> {
        let snap = edge_snap(self.screen(), pos);
        let preview = snap.map(|s| {
            let r = target(self.work_area(), s, GAP);
            Rectangle::<i32, Logical>::new((r.x, r.y).into(), (r.w, r.h).into())
        });
        if preview != self.snap_preview {
            self.snap_preview = preview;
            self.needs_redraw = true;
        }
        snap
    }
}

pub fn is_maximized(window: &Window) -> bool {
    window.toplevel().is_some_and(|t| t.current_state().states.contains(XdgState::Maximized))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn area() -> Rectangle<i32, Logical> {
        Rectangle::new((0, 34).into(), (1000, 700).into())
    }

    #[test]
    fn halves_split_the_work_area() {
        let l = target(area(), Snap::Left, 8);
        let r = target(area(), Snap::Right, 8);
        assert_eq!((l.x, l.y, l.h), (8, 42, 684));
        assert_eq!(r.x + r.w, 992);
        assert_eq!(r.x - (l.x + l.w), 8);
        assert_eq!(l.w, r.w);
    }

    #[test]
    fn edges_pick_a_side() {
        let screen = Rectangle::new((0, 0).into(), (1000, 800).into());
        assert_eq!(edge_snap(screen, (0.0, 400.0).into()), Some(Snap::Left));
        assert_eq!(edge_snap(screen, (999.0, 400.0).into()), Some(Snap::Right));
        assert_eq!(edge_snap(screen, (500.0, 0.0).into()), Some(Snap::Full));
        assert_eq!(edge_snap(screen, (500.0, 400.0).into()), None);
    }
}
