use std::cell::RefCell;

use smithay::{
    desktop::{Space, Window},
    input::pointer::{
        AxisFrame, ButtonEvent, GestureHoldBeginEvent, GestureHoldEndEvent, GesturePinchBeginEvent,
        GesturePinchEndEvent, GesturePinchUpdateEvent, GestureSwipeBeginEvent, GestureSwipeEndEvent,
        GestureSwipeUpdateEvent, GrabStartData as PointerGrabStartData, MotionEvent, PointerGrab,
        PointerInnerHandle, RelativeMotionEvent,
    },
    reexports::{
        wayland_protocols::xdg::shell::server::xdg_toplevel,
        wayland_server::protocol::wl_surface::WlSurface,
    },
    utils::{Logical, Point, Rectangle, Size},
    wayland::{compositor, shell::xdg::SurfaceCachedState},
};

use super::BTN_LEFT;
use crate::{ipc, OziWm};

/// Which window edges follow the pointer.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Edges {
    pub top: bool,
    pub bottom: bool,
    pub left: bool,
    pub right: bool,
}

impl From<xdg_toplevel::ResizeEdge> for Edges {
    fn from(edge: xdg_toplevel::ResizeEdge) -> Self {
        use xdg_toplevel::ResizeEdge as E;
        let (top, bottom, left, right) = match edge {
            E::Top => (true, false, false, false),
            E::Bottom => (false, true, false, false),
            E::Left => (false, false, true, false),
            E::Right => (false, false, false, true),
            E::TopLeft => (true, false, true, false),
            E::TopRight => (true, false, false, true),
            E::BottomLeft => (false, true, true, false),
            E::BottomRight => (false, true, false, true),
            _ => (false, false, false, false),
        };
        Edges { top, bottom, left, right }
    }
}

/// New window size for a pointer that moved by `delta` since the drag began.
/// `min`/`max` come from the client; 0 means "no limit".
pub fn resized(
    initial: (i32, i32),
    delta: (f64, f64),
    edges: Edges,
    min: (i32, i32),
    max: (i32, i32),
) -> (i32, i32) {
    let (mut w, mut h) = initial;
    if edges.left || edges.right {
        let dx = if edges.left { -delta.0 } else { delta.0 };
        w = (initial.0 as f64 + dx).round() as i32;
    }
    if edges.top || edges.bottom {
        let dy = if edges.top { -delta.1 } else { delta.1 };
        h = (initial.1 as f64 + dy).round() as i32;
    }
    let limit = |v: i32, lo: i32, hi: i32| {
        let lo = lo.max(1);
        let hi = if hi == 0 { i32::MAX } else { hi.max(lo) };
        v.clamp(lo, hi)
    };
    (limit(w, min.0, max.0), limit(h, min.1, max.1))
}

pub struct ResizeSurfaceGrab {
    start_data: PointerGrabStartData<OziWm>,
    window: Window,
    edges: Edges,
    initial_rect: Rectangle<i32, Logical>,
    last_window_size: Size<i32, Logical>,
}

impl ResizeSurfaceGrab {
    pub fn start(
        start_data: PointerGrabStartData<OziWm>,
        window: Window,
        edges: Edges,
        initial_rect: Rectangle<i32, Logical>,
    ) -> Self {
        if let Some(toplevel) = window.toplevel() {
            ResizeSurfaceState::with(toplevel.wl_surface(), |state| {
                *state = ResizeSurfaceState::Resizing { edges, initial_rect };
            });
        }
        Self {
            start_data,
            window,
            edges,
            initial_rect,
            last_window_size: initial_rect.size,
        }
    }
}

impl PointerGrab<OziWm> for ResizeSurfaceGrab {
    fn motion(
        &mut self,
        data: &mut OziWm,
        handle: &mut PointerInnerHandle<'_, OziWm>,
        _focus: Option<(WlSurface, Point<f64, Logical>)>,
        event: &MotionEvent,
    ) {
        handle.motion(data, None, event);
        let Some(toplevel) = self.window.toplevel() else {
            return;
        };
        let delta = event.location - self.start_data.location;
        let (min, max) = compositor::with_states(toplevel.wl_surface(), |states| {
            let mut guard = states.cached_state.get::<SurfaceCachedState>();
            let data = guard.current();
            (data.min_size, data.max_size)
        });
        let (w, h) = resized(
            (self.initial_rect.size.w, self.initial_rect.size.h),
            (delta.x, delta.y),
            self.edges,
            (min.w, min.h),
            (max.w, max.h),
        );
        self.last_window_size = (w, h).into();
        toplevel.with_pending_state(|state| {
            state.states.set(xdg_toplevel::State::Resizing);
            state.size = Some(self.last_window_size);
        });
        toplevel.send_pending_configure();
    }

    fn relative_motion(
        &mut self,
        data: &mut OziWm,
        handle: &mut PointerInnerHandle<'_, OziWm>,
        focus: Option<(WlSurface, Point<f64, Logical>)>,
        event: &RelativeMotionEvent,
    ) {
        handle.relative_motion(data, focus, event);
    }

    fn button(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &ButtonEvent) {
        handle.button(data, event);
        if handle.current_pressed().contains(&BTN_LEFT) {
            return;
        }
        handle.unset_grab(self, data, event.serial, event.time, true);
        let Some(toplevel) = self.window.toplevel() else {
            return;
        };
        toplevel.with_pending_state(|state| {
            state.states.unset(xdg_toplevel::State::Resizing);
            state.size = Some(self.last_window_size);
        });
        toplevel.send_pending_configure();
        let (edges, initial_rect) = (self.edges, self.initial_rect);
        ResizeSurfaceState::with(toplevel.wl_surface(), |state| {
            *state = ResizeSurfaceState::WaitingForLastCommit { edges, initial_rect };
        });
        ipc::emit_window(data, &self.window, "window-changed");
    }

    fn axis(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, details: AxisFrame) {
        handle.axis(data, details)
    }

    fn frame(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>) {
        handle.frame(data);
    }

    fn gesture_swipe_begin(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GestureSwipeBeginEvent) {
        handle.gesture_swipe_begin(data, event)
    }

    fn gesture_swipe_update(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GestureSwipeUpdateEvent) {
        handle.gesture_swipe_update(data, event)
    }

    fn gesture_swipe_end(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GestureSwipeEndEvent) {
        handle.gesture_swipe_end(data, event)
    }

    fn gesture_pinch_begin(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GesturePinchBeginEvent) {
        handle.gesture_pinch_begin(data, event)
    }

    fn gesture_pinch_update(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GesturePinchUpdateEvent) {
        handle.gesture_pinch_update(data, event)
    }

    fn gesture_pinch_end(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GesturePinchEndEvent) {
        handle.gesture_pinch_end(data, event)
    }

    fn gesture_hold_begin(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GestureHoldBeginEvent) {
        handle.gesture_hold_begin(data, event)
    }

    fn gesture_hold_end(&mut self, data: &mut OziWm, handle: &mut PointerInnerHandle<'_, OziWm>, event: &GestureHoldEndEvent) {
        handle.gesture_hold_end(data, event)
    }

    fn start_data(&self) -> &PointerGrabStartData<OziWm> {
        &self.start_data
    }

    fn unset(&mut self, _data: &mut OziWm) {}
}

/// Resize progress stored on the surface, so commits can keep the far edge in place.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
enum ResizeSurfaceState {
    #[default]
    Idle,
    Resizing {
        edges: Edges,
        initial_rect: Rectangle<i32, Logical>,
    },
    /// The button is up; the client's next commit is the last one of this resize.
    WaitingForLastCommit {
        edges: Edges,
        initial_rect: Rectangle<i32, Logical>,
    },
}

impl ResizeSurfaceState {
    fn with<F, T>(surface: &WlSurface, cb: F) -> T
    where
        F: FnOnce(&mut Self) -> T,
    {
        compositor::with_states(surface, |states| {
            states.data_map.insert_if_missing(RefCell::<Self>::default);
            let state = states
                .data_map
                .get::<RefCell<Self>>()
                .expect("inserted above");
            cb(&mut state.borrow_mut())
        })
    }

    fn commit(&mut self) -> Option<(Edges, Rectangle<i32, Logical>)> {
        match *self {
            Self::Resizing { edges, initial_rect } => Some((edges, initial_rect)),
            Self::WaitingForLastCommit { edges, initial_rect } => {
                *self = Self::Idle;
                Some((edges, initial_rect))
            }
            Self::Idle => None,
        }
    }
}

/// When the top or left edge is dragged, the window moves so the opposite edge stays put.
pub fn handle_commit(space: &mut Space<Window>, surface: &WlSurface) {
    let Some(window) = space
        .elements()
        .find(|w| w.toplevel().is_some_and(|t| t.wl_surface() == surface))
        .cloned()
    else {
        return;
    };
    let Some(mut location) = space.element_location(&window) else {
        return;
    };
    let size = window.geometry().size;
    let Some((edges, initial_rect)) = ResizeSurfaceState::with(surface, |state| state.commit()) else {
        return;
    };
    let mut moved = false;
    if edges.left {
        location.x = initial_rect.loc.x + (initial_rect.size.w - size.w);
        moved = true;
    }
    if edges.top {
        location.y = initial_rect.loc.y + (initial_rect.size.h - size.h);
        moved = true;
    }
    if moved {
        space.map_element(window, location, false);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const RIGHT: Edges = Edges { top: false, bottom: false, left: false, right: true };
    const TOP_LEFT: Edges = Edges { top: true, bottom: false, left: true, right: false };

    #[test]
    fn right_edge_grows_with_pointer() {
        assert_eq!(resized((800, 600), (50.0, 30.0), RIGHT, (0, 0), (0, 0)), (850, 600));
    }

    #[test]
    fn top_left_grows_against_pointer() {
        assert_eq!(resized((800, 600), (-20.0, -10.0), TOP_LEFT, (0, 0), (0, 0)), (820, 610));
    }

    #[test]
    fn client_limits_are_kept() {
        assert_eq!(resized((800, 600), (-900.0, 0.0), RIGHT, (200, 100), (0, 0)), (200, 600));
        assert_eq!(resized((800, 600), (900.0, 0.0), RIGHT, (0, 0), (1000, 0)), (1000, 600));
    }

    #[test]
    fn never_zero() {
        assert_eq!(resized((10, 10), (-50.0, 0.0), RIGHT, (0, 0), (0, 0)), (1, 10));
    }
}
