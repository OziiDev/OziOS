//! Touch screens and pens: smart boards, tablets, touch laptops.
//!
//! A finger goes to the program under it as a real touch when that program
//! listens for touches (Firefox, Qt and GTK programs scroll, pinch and press
//! and hold that way). Everywhere else it works as the mouse: on our window
//! frames (drag a title bar, press the buttons, pull an edge), on the lock
//! screen, and over programs that know no touch. One finger at a time drives
//! the mouse; more fingers on a program that listens all go to it.
//!
//! A pen that reports itself as a tablet tool (some boards' styluses) is the
//! mouse: the tip is the left button, the pen's button the right one.

use std::collections::HashMap;

use smithay::{
    backend::input::{
        AbsolutePositionEvent, ButtonState, InputBackend, TabletToolButtonEvent,
        TabletToolEvent, TabletToolTipEvent, TabletToolTipState, TouchEvent, TouchSlot,
    },
    input::touch::{DownEvent, MotionEvent, UpEvent},
    reexports::wayland_server::protocol::wl_surface::WlSurface,
    utils::{Logical, Point, SERIAL_COUNTER},
};

use crate::{grabs::BTN_LEFT, OziWm};

const BTN_RIGHT: u32 = 0x111;
const BTN_MIDDLE: u32 = 0x112;
const BTN_STYLUS: u32 = 0x14b;
const BTN_STYLUS2: u32 = 0x14c;

/// Where each finger on the screen went.
#[derive(Default)]
pub struct Touches {
    /// The finger that drives the mouse, if one does.
    mouse: Option<TouchSlot>,
    /// Fingers given to programs, with the surface they went to.
    clients: HashMap<TouchSlot, (WlSurface, Point<f64, Logical>)>,
    /// The pen's tip is on the screen.
    pen_down: bool,
    /// The last press came from a finger or a pen, not a mouse or keyboard:
    /// then a text field brings up the on-screen keyboard.
    pub last_was_touch: bool,
    /// A touch screen or pen tablet is plugged in.
    pub screen_present: bool,
}

impl OziWm {
    /// Where on the screen a touch or pen position lands: touch screens cover
    /// the first screen (the board), not every screen side by side.
    fn touch_position<B: InputBackend>(&self, event: &impl AbsolutePositionEvent<B>) -> Point<f64, Logical> {
        let area = self.screen();
        event.position_transformed(area.size) + area.loc.to_f64()
    }

    /// The program surface a finger at this point goes to, if it takes touches.
    fn touch_target(&self, location: Point<f64, Logical>) -> Option<(WlSurface, Point<f64, Logical>)> {
        if self.lock.is_some() || self.frame_hit(location).is_some() {
            return None;
        }
        let touch = self.seat.get_touch()?;
        self.surface_under(location).filter(|(surface, _)| touch.listens(surface))
    }

    pub fn on_touch_down<B: InputBackend>(
        &mut self,
        event: &(impl TouchEvent<B> + AbsolutePositionEvent<B>),
    ) {
        let location = self.touch_position(event);
        self.touch_down(event.slot(), location, event.time_msec());
    }

    pub fn on_touch_motion<B: InputBackend>(
        &mut self,
        event: &(impl TouchEvent<B> + AbsolutePositionEvent<B>),
    ) {
        let location = self.touch_position(event);
        self.touch_motion(event.slot(), location, event.time_msec());
    }

    pub fn on_touch_up<B: InputBackend>(&mut self, event: &impl TouchEvent<B>) {
        self.touch_up(event.slot(), event.time_msec());
    }

    pub fn touch_down(&mut self, slot: TouchSlot, location: Point<f64, Logical>, time: u32) {
        self.touches.last_was_touch = true;
        self.touch_device_added();
        if let Some(target) = self.touch_target(location)
            && let Some(touch) = self.seat.get_touch()
        {
            self.focus_at(location);
            self.touches.clients.insert(slot, target.clone());
            let serial = SERIAL_COUNTER.next_serial();
            touch.down(self, Some(target), &DownEvent { slot, location, serial, time });
            return;
        }
        // The mouse: one finger at a time.
        if self.touches.mouse.is_some() {
            return;
        }
        self.touches.mouse = Some(slot);
        self.pointer_to(location, time);
        self.press(BTN_LEFT, ButtonState::Pressed, time);
    }

    pub fn touch_motion(&mut self, slot: TouchSlot, location: Point<f64, Logical>, time: u32) {
        if self.touches.mouse == Some(slot) {
            self.pointer_to(location, time);
            return;
        }
        if let Some(target) = self.touches.clients.get(&slot).cloned()
            && let Some(touch) = self.seat.get_touch()
        {
            touch.motion(self, Some(target), &MotionEvent { slot, location, time });
        }
    }

    pub fn touch_up(&mut self, slot: TouchSlot, time: u32) {
        if self.touches.mouse == Some(slot) {
            self.touches.mouse = None;
            self.press(BTN_LEFT, ButtonState::Released, time);
            return;
        }
        if self.touches.clients.remove(&slot).is_some()
            && let Some(touch) = self.seat.get_touch()
        {
            let serial = SERIAL_COUNTER.next_serial();
            touch.up(self, &UpEvent { slot, serial, time });
        }
    }

    /// The IPC "touch" request: a finger down, moving or up, as a touch screen
    /// would send it (tests and remote help use it).
    pub fn ipc_touch(&mut self, slot: u32, location: Point<f64, Logical>, action: &str) {
        let time = self.start_time.elapsed().as_millis() as u32;
        let slot: TouchSlot = Some(slot).into();
        match action {
            "down" => self.touch_down(slot, location, time),
            "move" => self.touch_motion(slot, location, time),
            "up" => self.touch_up(slot, time),
            _ => {
                self.touch_down(slot, location, time);
                self.on_touch_frame();
                self.touch_up(slot, time + 60);
            }
        }
        self.on_touch_frame();
    }

    pub fn on_touch_frame(&mut self) {
        if !self.touches.clients.is_empty()
            && let Some(touch) = self.seat.get_touch()
        {
            touch.frame(self);
        }
    }

    /// The screen gave up on the touches (a palm, a gesture of its own).
    pub fn on_touch_cancel(&mut self) {
        if self.touches.mouse.take().is_some() {
            let time = self.start_time.elapsed().as_millis() as u32;
            self.press(BTN_LEFT, ButtonState::Released, time);
        }
        if !std::mem::take(&mut self.touches.clients).is_empty()
            && let Some(touch) = self.seat.get_touch()
        {
            touch.cancel(self);
        }
    }

    pub fn on_pen_move<B: InputBackend>(&mut self, event: &impl TabletToolEvent<B>) {
        let location = self.touch_position(event);
        self.pointer_to(location, event.time_msec());
    }

    pub fn on_pen_tip<B: InputBackend>(&mut self, event: &impl TabletToolTipEvent<B>) {
        let location = self.touch_position(event);
        let time = event.time_msec();
        self.pointer_to(location, time);
        let down = event.tip_state() == TabletToolTipState::Down;
        self.touches.last_was_touch = true;
        if down != self.touches.pen_down {
            self.touches.pen_down = down;
            let state = if down { ButtonState::Pressed } else { ButtonState::Released };
            self.press(BTN_LEFT, state, time);
        }
    }

    pub fn on_pen_button<B: InputBackend>(&mut self, event: &impl TabletToolButtonEvent<B>) {
        let button = match event.button() {
            BTN_STYLUS => BTN_RIGHT,
            BTN_STYLUS2 => BTN_MIDDLE,
            _ => return,
        };
        self.press(button, event.button_state(), event.time_msec());
    }
}

impl OziWm {
    /// Whether text fields should report themselves, for the on-screen
    /// keyboard: on touch screens and in the Education edition by default.
    pub fn refresh_osk(&mut self) {
        let on = match self.look.osk.as_str() {
            "always" => true,
            "never" => false,
            _ => self.touches.screen_present || education(),
        };
        smithay::wayland::text_input::set_enter_without_ime(on);
    }

    /// A touch screen or pen came in (libinput device added).
    pub fn touch_device_added(&mut self) {
        if !self.touches.screen_present {
            self.touches.screen_present = true;
            self.refresh_osk();
        }
    }

    /// After each round of client requests: tell the shell when a text field
    /// starts or stops wanting typing, so the on-screen keyboard can follow.
    pub fn check_text_input(&mut self) {
        use smithay::wayland::text_input::TextInputSeat;
        let mut active = false;
        self.seat.text_input().with_active_text_input(|_, _| active = true);
        if active != self.text_input_active {
            self.text_input_active = active;
            let touch = self.touches.last_was_touch;
            crate::ipc::emit(
                self,
                "shell",
                serde_json::json!({ "event": "text-input", "active": active, "touch": touch }),
            );
        }
    }
}

/// The OziOS Education edition (smart boards) is installed.
fn education() -> bool {
    std::fs::read_to_string("/usr/share/ozios/edition").is_ok_and(|e| e.trim() == "edu")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slots_are_told_apart() {
        let mut touches = Touches::default();
        let a: TouchSlot = Some(0).into();
        let b: TouchSlot = Some(1).into();
        touches.mouse = Some(a);
        assert_eq!(touches.mouse, Some(a));
        assert_ne!(touches.mouse, Some(b));
    }
}
