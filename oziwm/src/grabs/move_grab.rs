use smithay::{
    desktop::Window,
    input::pointer::{
        AxisFrame, ButtonEvent, GestureHoldBeginEvent, GestureHoldEndEvent, GesturePinchBeginEvent,
        GesturePinchEndEvent, GesturePinchUpdateEvent, GestureSwipeBeginEvent, GestureSwipeEndEvent,
        GestureSwipeUpdateEvent, GrabStartData as PointerGrabStartData, MotionEvent, PointerGrab,
        PointerInnerHandle, RelativeMotionEvent,
    },
    reexports::wayland_server::protocol::wl_surface::WlSurface,
    utils::{Logical, Point},
};

use super::BTN_LEFT;
use crate::{ipc, OziWm};

/// Dragging a window with the left button (title bar or Mod + drag).
pub struct MoveSurfaceGrab {
    pub start_data: PointerGrabStartData<OziWm>,
    pub window: Window,
    pub initial_window_location: Point<i32, Logical>,
}

impl PointerGrab<OziWm> for MoveSurfaceGrab {
    fn motion(
        &mut self,
        data: &mut OziWm,
        handle: &mut PointerInnerHandle<'_, OziWm>,
        _focus: Option<(WlSurface, Point<f64, Logical>)>,
        event: &MotionEvent,
    ) {
        // No client gets pointer events while a window is being dragged.
        handle.motion(data, None, event);
        let delta = event.location - self.start_data.location;
        let new_location = self.initial_window_location.to_f64() + delta;
        data.space
            .map_element(self.window.clone(), new_location.to_i32_round(), true);
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
        if !handle.current_pressed().contains(&BTN_LEFT) {
            handle.unset_grab(self, data, event.serial, event.time, true);
            ipc::emit_window(data, &self.window, "window-changed");
        }
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
