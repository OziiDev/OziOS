//! The lock screen, drawn by oziwm itself: no client can hide it, and if the
//! shell crashes the screen stays locked. The password is checked with PAM
//! (service `oziwm`, /etc/pam.d/oziwm) on a separate thread.

use std::time::{Duration, Instant};

use smithay::{
    backend::{
        allocator::Fourcc,
        renderer::{
            element::{
                memory::{MemoryRenderBuffer, MemoryRenderBufferRenderElement},
                Kind,
            },
            gles::{element::PixelShaderElement, GlesPixelProgram, GlesRenderer, Uniform},
        },
    },
    input::keyboard::Keysym,
    reexports::{
        calloop::channel::{channel, Event, Sender},
        wayland_server::protocol::wl_surface::WlSurface,
    },
    utils::{IsAlive, Logical, Point, Rectangle, Transform, SERIAL_COUNTER},
};

use crate::{
    render::{OziElement, WindowPart},
    title, OziWm,
};

const MONTHS: [&str; 12] = [
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
    "December",
];
const DAYS: [&str; 7] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/// "Sunday, November 22" (in Turkish "22 Kasım Pazar") from a day, a 1-based
/// month and a weekday (0 = Monday).
pub fn local_date(day: u32, month: u32, weekday: u32) -> String {
    let day = day.to_string();
    let month = crate::i18n::tr(MONTHS[(month.clamp(1, 12) - 1) as usize]);
    let weekday = crate::i18n::tr(DAYS[weekday.min(6) as usize]);
    crate::i18n::trf("{weekday}, {month} {day}", &[("weekday", &weekday), ("month", &month), ("day", &day)])
}

/// Longest password kept; more is ignored.
const MAX_LEN: usize = 256;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    Typing,
    Checking,
    Wrong,
}

pub struct Lock {
    typed: String,
    pub phase: Phase,
    wrong_at: Option<Instant>,
    /// Last key or the moment of locking: the lights move for a while after it, then rest.
    woke: Instant,
    background: Option<PixelShaderElement>,
    texts: Vec<(String, f32, [f32; 3], MemoryRenderBuffer, (i32, i32))>,
}

impl Lock {
    fn new() -> Self {
        Lock {
            typed: String::new(),
            phase: Phase::Typing,
            wrong_at: None,
            woke: Instant::now(),
            background: None,
            texts: Vec::new(),
        }
    }

    /// What one key does on the lock screen. Returns true when Enter asks to check.
    pub fn key(&mut self, sym: Keysym, ch: Option<char>) -> bool {
        self.woke = Instant::now();
        if self.phase == Phase::Checking {
            return false;
        }
        match sym {
            Keysym::Return | Keysym::KP_Enter => return !self.typed.is_empty(),
            Keysym::BackSpace => {
                self.typed.pop();
            }
            Keysym::Escape => self.typed.clear(),
            _ => {
                if let Some(c) = ch.filter(|c| !c.is_control()) {
                    if self.typed.chars().count() < MAX_LEN {
                        self.typed.push(c);
                    }
                }
            }
        }
        if self.phase == Phase::Wrong && !self.typed.is_empty() {
            self.phase = Phase::Typing;
        }
        false
    }

    pub fn dots(&self) -> usize {
        self.typed.chars().count()
    }

    fn text(
        &mut self,
        font: &ab_glyph::FontVec,
        text: &str,
        px: f32,
        color: [f32; 3],
    ) -> Option<(MemoryRenderBuffer, (i32, i32))> {
        if let Some((_, _, _, buffer, size)) = self
            .texts
            .iter()
            .find(|(t, p, c, _, _)| t == text && *p == px && *c == color)
        {
            return Some((buffer.clone(), *size));
        }
        let rendered = title::render_px(font, text, color, px)?;
        let buffer = MemoryRenderBuffer::from_slice(
            &rendered.pixels,
            Fourcc::Argb8888,
            (rendered.width, rendered.height),
            1,
            Transform::Normal,
            None,
        );
        let size = (rendered.width, rendered.height);
        // Keep only a handful: the clock changes every minute, the dots per key.
        if self.texts.len() > 24 {
            self.texts.remove(0);
        }
        self.texts.push((text.to_string(), px, color, buffer.clone(), size));
        Some((buffer, size))
    }
}

fn user_name() -> String {
    std::env::var("USER")
        .or_else(|_| std::env::var("LOGNAME"))
        .unwrap_or_default()
}

/// Ask PAM, off the main thread, and report back through the event loop.
fn check(password: String, reply: Sender<bool>) {
    std::thread::spawn(move || {
        let user = user_name();
        let ok = match pam::Client::with_password("oziwm") {
            Ok(mut client) => {
                client.conversation_mut().set_credentials(user, password);
                client.authenticate().is_ok()
            }
            Err(err) => {
                tracing::warn!(?err, "PAM is not available");
                false
            }
        };
        // A wrong guess costs a moment, like every other lock screen.
        if !ok {
            std::thread::sleep(Duration::from_millis(900));
        }
        let _ = reply.send(ok);
    });
}

pub struct LockAnswers(pub Sender<bool>);

/// Lock when nobody touched anything for the configured time, unless a
/// visible program (a video, a game) asked the screen to stay awake.
fn check_idle(state: &mut OziWm) {
    let minutes = state.look.lock_after_minutes;
    if minutes == 0 || state.lock.is_some() {
        return;
    }
    state.inhibitors.retain(|s| s.alive());
    let awake = state.inhibitors.iter().any(|s| {
        state.space.elements().any(|w| w.toplevel().is_some_and(|t| t.wl_surface() == s))
            || smithay::wayland::compositor::get_parent(s).is_some()
    });
    if awake {
        return;
    }
    if state.last_input.elapsed() >= Duration::from_secs(minutes as u64 * 60) {
        state.lock();
    }
}

/// Listen for PAM answers; call once at start.
pub fn init(state: &mut OziWm) -> Result<(), Box<dyn std::error::Error>> {
    let (tx, rx) = channel::<bool>();
    state.loop_handle.insert_source(rx, |event, _, state| {
        if let Event::Msg(ok) = event {
            state.on_unlock_answer(ok);
        }
    })?;
    state.lock_answers = Some(LockAnswers(tx));
    state.loop_handle.insert_source(
        smithay::reexports::calloop::timer::Timer::from_duration(Duration::from_secs(20)),
        |_, _, state| {
            check_idle(state);
            smithay::reexports::calloop::timer::TimeoutAction::ToDuration(Duration::from_secs(20))
        },
    )?;
    Ok(())
}

impl OziWm {
    pub fn lock(&mut self) {
        if self.lock.is_some() {
            return;
        }
        tracing::info!("screen locked");
        self.lock = Some(Lock::new());
        // Nobody keeps the keyboard or the pointer while locked.
        let serial = SERIAL_COUNTER.next_serial();
        if let Some(keyboard) = self.seat.get_keyboard() {
            keyboard.set_focus(self, Option::<WlSurface>::None, serial);
        }
        if let Some(pointer) = self.seat.get_pointer() {
            let location = pointer.current_location();
            pointer.motion(
                self,
                None,
                &smithay::input::pointer::MotionEvent { location, serial, time: 0 },
            );
            pointer.frame(self);
        }
        self.needs_redraw = true;
        crate::ipc::emit_locked(self, true);
    }

    /// A key while locked: type, delete, clear, or check on Enter.
    pub fn lock_key(&mut self, sym: Keysym, ch: Option<char>) {
        let Some(lock) = self.lock.as_mut() else {
            return;
        };
        if lock.key(sym, ch) {
            lock.phase = Phase::Checking;
            let password = std::mem::take(&mut lock.typed);
            if let Some(LockAnswers(tx)) = &self.lock_answers {
                check(password, tx.clone());
            }
        }
        self.needs_redraw = true;
    }

    fn on_unlock_answer(&mut self, ok: bool) {
        let Some(lock) = self.lock.as_mut() else {
            return;
        };
        if ok {
            tracing::info!("screen unlocked");
            self.lock = None;
            let top = self.space.elements().last().cloned();
            self.focus_window(top);
            crate::ipc::emit_locked(self, false);
        } else {
            lock.phase = Phase::Wrong;
            lock.wrong_at = Some(Instant::now());
        }
        self.needs_redraw = true;
    }

    /// The lock screen for one output, top-most first, and whether it is still moving.
    pub fn lock_elements(
        &mut self,
        renderer: &mut GlesRenderer,
        program: &GlesPixelProgram,
        output_size: (i32, i32),
        scale: f64,
        now: Instant,
    ) -> (Vec<OziElement>, bool) {
        let theme = self.look.theme;
        let Some(lock) = self.lock.as_mut() else {
            return (Vec::new(), false);
        };
        // The lights drift for half a minute after a key, then hold still.
        const MOVING: Duration = Duration::from_secs(30);
        let awake_for = now.saturating_duration_since(lock.woke);
        let shown = if awake_for < MOVING { now } else { lock.woke + MOVING };
        let time = shown.duration_since(self.start_time).as_secs_f32();
        let mut moving = awake_for < MOVING || lock.phase == Phase::Checking;
        let (w, h) = output_size;
        let field = (w / 2 - 170, h / 2 + 60, 340, 52);
        let shake = lock
            .wrong_at
            .map(|t| (now.duration_since(t).as_secs_f32() / 0.5).min(1.0))
            .filter(|s| *s < 1.0)
            .unwrap_or(0.0);
        moving |= shake > 0.0;
        let phase = match lock.phase {
            Phase::Typing => 0.0f32,
            Phase::Checking => 1.0,
            Phase::Wrong => 2.0,
        };
        let uniforms = vec![
            Uniform::new("ozi_time", time),
            Uniform::new("ozi_ink", theme.ink),
            Uniform::new("ozi_c1", theme.accent),
            Uniform::new("ozi_c2", theme.accent2),
            Uniform::new("ozi_field", [field.0 as f32, field.1 as f32, field.2 as f32, field.3 as f32]),
            Uniform::new("ozi_state", phase),
            Uniform::new("ozi_shake", shake),
        ];
        let area = Rectangle::<i32, Logical>::from_size((w, h).into());
        let background = match lock.background.as_mut() {
            Some(element) => {
                element.resize(area, None);
                element.update_uniforms(uniforms);
                element.clone()
            }
            None => {
                let e = PixelShaderElement::new(program.clone(), area, None, 1.0, uniforms, Kind::Unspecified);
                lock.background = Some(e.clone());
                e
            }
        };

        let mut out: Vec<OziElement> = Vec::new();
        if let Some(font) = self.font.as_ref() {
            let local = chrono::Local::now();
            use chrono::{Datelike, Timelike};
            let clock = format!("{:02}:{:02}", local.hour(), local.minute());
            let date = local_date(local.day(), local.month(), local.weekday().num_days_from_monday());
            let hint = match lock.phase {
                Phase::Typing if lock.dots() == 0 => crate::i18n::tr("Type your password to unlock"),
                Phase::Typing => "•".repeat(lock.dots().min(24)),
                Phase::Checking => crate::i18n::tr("Checking…"),
                Phase::Wrong => crate::i18n::tr("Wrong password, try again"),
            };
            let hint_color = match lock.phase {
                Phase::Wrong => [1.0, 0.333, 0.431],
                Phase::Typing if lock.dots() > 0 => theme.text,
                _ => theme.muted,
            };
            let user = user_name();
            let lines: [(String, f32, [f32; 3], i32); 4] = [
                (clock, 112.0, theme.text, h / 2 - 150),
                (date, 22.0, theme.muted, h / 2 - 20),
                (hint, if lock.dots() > 0 && lock.phase == Phase::Typing { 26.0 } else { 15.0 }, hint_color, field.1 + field.3 / 2),
                (user, 15.0, theme.muted, field.1 + field.3 + 28),
            ];
            for (text, px, color, centre_y) in lines {
                let px = px * scale as f32;
                let Some((buffer, (tw, th))) = lock.text(font, &text, px, color) else {
                    continue;
                };
                let x = (w as f64 * scale - tw as f64) / 2.0;
                let y = centre_y as f64 * scale - th as f64 / 2.0;
                if let Ok(e) = MemoryRenderBufferRenderElement::from_buffer(
                    renderer,
                    Point::from((x.round(), y.round())),
                    &buffer,
                    None,
                    None,
                    None,
                    Kind::Unspecified,
                ) {
                    out.push(OziElement::Part(WindowPart::Title(e)));
                }
            }
        }
        out.push(OziElement::Part(WindowPart::Frame(background)));
        (out, moving)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn typing_editing_and_enter() {
        let mut lock = Lock::new();
        assert!(!lock.key(Keysym::Return, None), "nothing typed, nothing to check");
        lock.key(Keysym::a, Some('a'));
        lock.key(Keysym::odiaeresis, Some('ö'));
        assert_eq!(lock.dots(), 2);
        lock.key(Keysym::BackSpace, None);
        assert_eq!(lock.dots(), 1);
        lock.key(Keysym::Tab, Some('\t'));
        assert_eq!(lock.dots(), 1, "control characters are not part of a password");
        assert!(lock.key(Keysym::Return, None));
        lock.key(Keysym::Escape, None);
        assert_eq!(lock.dots(), 0);
    }

    #[test]
    fn no_typing_while_checking() {
        let mut lock = Lock::new();
        lock.phase = Phase::Checking;
        lock.key(Keysym::a, Some('a'));
        assert_eq!(lock.dots(), 0);
    }

    #[test]
    fn wrong_phase_ends_when_typing_again() {
        let mut lock = Lock::new();
        lock.phase = Phase::Wrong;
        lock.key(Keysym::b, Some('b'));
        assert_eq!(lock.phase, Phase::Typing);
    }

    #[test]
    fn dates_in_turkish() {
        // The words follow the session language; the day is always there.
        assert!(local_date(22, 11, 6).contains("22"));
        assert!(local_date(1, 1, 0).contains('1'));
    }
}
