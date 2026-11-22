use smithay::{
    backend::input::{
        AbsolutePositionEvent, Axis, AxisSource, ButtonState, Event, InputBackend, InputEvent,
        KeyState, KeyboardKeyEvent, PointerAxisEvent, PointerButtonEvent, PointerMotionEvent,
    },
    input::{
        keyboard::{FilterResult, Keysym},
        pointer::{AxisFrame, ButtonEvent, Focus, GrabStartData, MotionEvent, RelativeMotionEvent},
    },
    utils::{Logical, Point, SERIAL_COUNTER},
};

use std::time::{Duration, Instant};

use smithay::{desktop::Window, utils::{Rectangle, Serial}};

use crate::{
    bindings::{self, Action, Mods},
    deco::{Button, Hit},
    grabs::{MoveSurfaceGrab, ResizeSurfaceGrab, BTN_LEFT},
    state::window_id,
    OziWm,
};

impl OziWm {
    pub fn process_input_event<I: InputBackend>(&mut self, event: InputEvent<I>) {
        self.last_input = Instant::now();
        match event {
            InputEvent::Keyboard { event } => self.on_key(event),
            InputEvent::PointerMotion { event } => {
                let pointer_location = self.pointer_location() + event.delta();
                self.on_pointer_moved(pointer_location, event.time_msec());
                if let Some(pointer) = self.seat.get_pointer() {
                    let under = self.surface_under(pointer.current_location());
                    pointer.relative_motion(
                        self,
                        under,
                        &RelativeMotionEvent {
                            delta: event.delta(),
                            delta_unaccel: event.delta_unaccel(),
                            utime: event.time(),
                        },
                    );
                    pointer.frame(self);
                }
            }
            InputEvent::PointerMotionAbsolute { event } => {
                let area = self.screen();
                let location = event.position_transformed(area.size) + area.loc.to_f64();
                self.on_pointer_moved(location, event.time_msec());
            }
            InputEvent::PointerButton { event } => self.on_button(
                event.button_code(),
                event.state(),
                event.time_msec(),
            ),
            InputEvent::PointerAxis { event } => self.on_axis::<I>(&event),
            _ => {}
        }
    }

    fn pointer_location(&self) -> Point<f64, Logical> {
        self.seat
            .get_pointer()
            .map(|p| p.current_location())
            .unwrap_or_default()
    }

    fn on_key<E: KeyboardKeyEvent<B>, B: InputBackend>(&mut self, event: E) {
        let Some(keyboard) = self.seat.get_keyboard() else {
            return;
        };
        let serial = SERIAL_COUNTER.next_serial();
        let time = Event::time_msec(&event);
        let code = event.key_code();
        let state = event.state();
        let nested = self.nested;

        let action = keyboard.input::<Option<Action>, _>(self, code, state, serial, time, |wm, mods, handle| {
            // A Super tap on its own opens the launcher, like the Windows key.
            let is_super = matches!(handle.modified_sym(), Keysym::Super_L | Keysym::Super_R);
            if state == KeyState::Pressed {
                wm.super_alone = is_super;
            } else if is_super && wm.super_alone && !wm.nested {
                wm.super_alone = false;
                return FilterResult::Intercept(Some(Action::ToggleLauncher));
            }
            // Locked: every key goes to the lock screen, except console switching.
            if wm.lock.is_some() {
                if state == KeyState::Pressed {
                    // Consoles, sound and brightness keep working on the lock screen.
                    let special = bindings::special_key(handle.modified_sym());
                    let key = Action::LockKey(handle.modified_sym(), handle.modified_sym().key_char());
                    return FilterResult::Intercept(Some(special.unwrap_or(key)));
                }
                return FilterResult::Intercept(None);
            }
            if state == KeyState::Released {
                // The press was a shortcut, so the program never saw it: hide the release too.
                if let Some(i) = wm.suppressed_keys.iter().position(|k| *k == code) {
                    wm.suppressed_keys.remove(i);
                    return FilterResult::Intercept(None);
                }
                return FilterResult::Forward;
            }
            let mods = Mods { logo: mods.logo, alt: mods.alt, ctrl: mods.ctrl, shift: mods.shift };
            let sym = handle.raw_latin_sym_or_raw_current_sym().unwrap_or(handle.modified_sym());
            let special = bindings::special_key(handle.modified_sym());
            match special.or_else(|| bindings::action_for(mods, sym, nested)) {
                Some(action) => {
                    wm.suppressed_keys.push(code);
                    FilterResult::Intercept(Some(action))
                }
                None => FilterResult::Forward,
            }
        });

        if let Some(Some(action)) = action {
            self.run_action(action);
        }
    }

    pub fn run_action(&mut self, action: Action) {
        tracing::debug!(?action, "shortcut");
        match action {
            Action::Spawn(argv) => self.spawn(&argv),
            Action::CloseFocused => self.close_focused(),
            Action::CycleFocus => self.cycle_focus(),
            Action::Quit => self.loop_signal.stop(),
            Action::ToggleLauncher => crate::ipc::emit_launcher(self),
            Action::TogglePanel => crate::ipc::emit_panel(self),
            Action::Workspace(n) => self.switch_workspace(n),
            Action::MoveToWorkspace(n) => {
                if let Some(w) = self.focused_window() {
                    self.move_to_workspace(&w, n);
                }
            }
            Action::ToggleTiling => self.toggle_tiling(),
            Action::Lock => self.lock(),
            Action::Key(name) => crate::ipc::emit_key(self, name),
            Action::Screenshot => {
                self.request_screenshot(None);
            }
            Action::LockKey(sym, ch) => self.lock_key(sym, ch),
            Action::ToggleFloating => {
                if let Some(w) = self.focused_window() {
                    self.toggle_floating(&w);
                }
            }
            Action::SwitchVt(vt) => {
                if let Some(tty) = self.tty.as_mut() {
                    tty.change_vt(vt);
                }
            }
        }
    }

    fn on_pointer_moved(&mut self, location: Point<f64, Logical>, time: u32) {
        let area = self.screen();
        let location = Point::from((
            location.x.clamp(area.loc.x as f64, (area.loc.x + area.size.w - 1) as f64),
            location.y.clamp(area.loc.y as f64, (area.loc.y + area.size.h - 1) as f64),
        ));
        let Some(pointer) = self.seat.get_pointer() else {
            return;
        };
        // Over our own frame (or on the lock screen) no client gets the pointer.
        let under = if self.lock.is_some() || self.frame_hit(location).is_some() {
            None
        } else {
            self.surface_under(location)
        };
        let serial = SERIAL_COUNTER.next_serial();
        pointer.motion(self, under, &MotionEvent { location, serial, time });
        pointer.frame(self);
        self.update_hover(location);
    }

    fn on_button(&mut self, button: u32, state: ButtonState, time: u32) {
        self.super_alone = false;
        if self.lock.is_some() {
            return;
        }
        let Some(pointer) = self.seat.get_pointer() else {
            return;
        };
        let serial = SERIAL_COUNTER.next_serial();

        if state == ButtonState::Pressed && !pointer.is_grabbed() && button == BTN_LEFT {
            let location = pointer.current_location();
            if let Some((window, hit)) = self.frame_hit(location) {
                self.on_frame_press(window, hit, location, serial);
                pointer.frame(self);
                return;
            }
        }

        if state == ButtonState::Pressed && !pointer.is_grabbed() {
            let location = pointer.current_location();
            if let Some(layer) = self.focusable_layer_at(location) {
                self.focus_layer(&layer);
                pointer.button(self, &ButtonEvent { button, state, serial, time });
                pointer.frame(self);
                return;
            }
            let clicked = self
                .space
                .element_under(location)
                .map(|(w, loc)| (w.clone(), loc));
            match clicked {
                Some((window, window_location)) => {
                    self.focus_window(Some(window.clone()));
                    // Mod + left drag moves a window from anywhere inside it.
                    if button == BTN_LEFT && self.mod_held() {
                        let grab = MoveSurfaceGrab {
                            start_data: GrabStartData { focus: None, button, location },
                            window,
                            initial_window_location: window_location,
                        };
                        pointer.set_grab(self, grab, serial, Focus::Clear);
                    }
                }
                None => self.focus_window(None),
            }
        }

        pointer.button(self, &ButtonEvent { button, state, serial, time });
        pointer.frame(self);
    }

    /// A press on our own frame: buttons act, the bar drags, edges resize.
    fn on_frame_press(&mut self, window: Window, hit: Hit, location: Point<f64, Logical>, serial: Serial) {
        let Some(pointer) = self.seat.get_pointer() else {
            return;
        };
        self.focus_window(Some(window.clone()));
        let start_data = GrabStartData { focus: None, button: BTN_LEFT, location };
        match hit {
            Hit::Button(Button::Close) => {
                if let Some(t) = window.toplevel() {
                    t.send_close();
                }
            }
            Hit::Button(Button::Maximize) => self.toggle_maximize(&window),
            Hit::Button(Button::Minimize) => self.minimize(&window),
            Hit::Title => {
                let id = window_id(&window);
                let now = Instant::now();
                let double = self
                    .last_title_click
                    .is_some_and(|(last, at)| last == id && now.duration_since(at) < Duration::from_millis(400));
                if double {
                    self.last_title_click = None;
                    self.toggle_maximize(&window);
                    return;
                }
                self.last_title_click = Some((id, now));
                let Some(initial_window_location) = self.space.element_location(&window) else {
                    return;
                };
                let grab = MoveSurfaceGrab { start_data, window, initial_window_location };
                pointer.set_grab(self, grab, serial, Focus::Clear);
            }
            Hit::Edge(edges) => {
                let Some(loc) = self.space.element_location(&window) else {
                    return;
                };
                let size = window.geometry().size;
                let grab = ResizeSurfaceGrab::start(start_data, window, edges, Rectangle::new(loc, size));
                pointer.set_grab(self, grab, serial, Focus::Clear);
            }
        }
    }

    /// Light up the button under the pointer.
    fn update_hover(&mut self, location: Point<f64, Logical>) {
        let hovered = match self.frame_hit(location) {
            Some((window, Hit::Button(b))) => Some((window_id(&window), b)),
            _ => None,
        };
        for (id, look) in self.looks.iter_mut() {
            look.hover = hovered.and_then(|(h, b)| (h == *id).then_some(b));
        }
    }

    fn mod_held(&self) -> bool {
        self.seat
            .get_keyboard()
            .map(|k| {
                let m = k.modifier_state();
                if self.nested { m.alt } else { m.logo }
            })
            .unwrap_or(false)
    }

    fn on_axis<I: InputBackend>(&mut self, event: &I::PointerAxisEvent) {
        if self.lock.is_some() {
            return;
        }
        let Some(pointer) = self.seat.get_pointer() else {
            return;
        };
        let source = event.source();
        let mut frame = AxisFrame::new(event.time_msec()).source(source);
        for axis in [Axis::Horizontal, Axis::Vertical] {
            let amount = event
                .amount(axis)
                .unwrap_or_else(|| event.amount_v120(axis).unwrap_or(0.0) * 15.0 / 120.0);
            if amount != 0.0 {
                frame = frame.value(axis, amount);
                if let Some(v120) = event.amount_v120(axis) {
                    frame = frame.v120(axis, v120 as i32);
                }
            }
            // A finger lifted off the touchpad ends kinetic scrolling.
            if source == AxisSource::Finger && event.amount(axis) == Some(0.0) {
                frame = frame.stop(axis);
            }
        }
        pointer.axis(self, frame);
        pointer.frame(self);
    }
}
