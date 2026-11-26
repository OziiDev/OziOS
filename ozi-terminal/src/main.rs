//! Ozi Terminal: the OziOS terminal. The terminal itself (escape codes, the
//! grid, scrollback, selection) is alacritty_terminal; this program draws it,
//! in the desktop's colours, with tabs.
//!
//!   Ctrl+Shift+T new tab      Ctrl+Shift+W close tab     Ctrl+PageUp/PageDown, Alt+1..9 switch
//!   Ctrl+Shift+C copy         Ctrl+Shift+V paste         Ctrl+Shift+N new window
//!   Ctrl+= / Ctrl+- / Ctrl+0  text size                  Shift+PageUp/PageDown scroll back

mod font;
mod keys;
mod look;
mod render;

use std::borrow::Cow;
use std::collections::HashMap;
use std::num::NonZeroU32;
use std::path::PathBuf;
use std::rc::Rc;
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime};

use alacritty_terminal::event::{Event as TermEvent, EventListener, WindowSize};
use alacritty_terminal::event_loop::{EventLoop as PtyLoop, EventLoopSender, Msg};
use alacritty_terminal::grid::{Dimensions, Scroll};
use alacritty_terminal::index::{Column, Line, Point, Side};
use alacritty_terminal::selection::{Selection, SelectionType};
use alacritty_terminal::sync::FairMutex;
use alacritty_terminal::term::test::TermSize;
use alacritty_terminal::term::{ClipboardType, Config, Term, TermMode};
use alacritty_terminal::tty;
use alacritty_terminal::vte::ansi::NamedColor;
use winit::application::ApplicationHandler;
use winit::dpi::{LogicalSize, PhysicalPosition};
use winit::event::{ElementState, MouseButton, MouseScrollDelta, WindowEvent};
use winit::event_loop::{ActiveEventLoop, EventLoop, EventLoopProxy};
use winit::keyboard::{Key, ModifiersState, NamedKey};
use winit::window::{CursorIcon, Window, WindowId};

pub const FONT_PX: f32 = 15.0;
pub const PADDING: f32 = 8.0;

#[derive(Debug)]
pub enum UserEvent {
    Term(u64, TermEvent),
    LookChanged,
}

#[derive(Clone)]
pub struct Proxy {
    tab: u64,
    proxy: EventLoopProxy<UserEvent>,
}

impl EventListener for Proxy {
    fn send_event(&self, event: TermEvent) {
        let _ = self.proxy.send_event(UserEvent::Term(self.tab, event));
    }
}

pub struct Tab {
    pub id: u64,
    pub term: Arc<FairMutex<Term<Proxy>>>,
    sender: EventLoopSender,
    pub title: String,
    pid: u32,
}

impl Tab {
    fn write(&self, bytes: impl Into<Cow<'static, [u8]>>) {
        let bytes = bytes.into();
        if !bytes.is_empty() {
            let _ = self.sender.send(Msg::Input(bytes));
        }
    }

    /// The folder the shell is in now, for a new tab to start there.
    fn cwd(&self) -> Option<PathBuf> {
        std::fs::read_link(format!("/proc/{}/cwd", self.pid)).ok()
    }
}

struct Args {
    command: Option<tty::Shell>,
    cwd: Option<PathBuf>,
    /// Keep the window after the command ends, until a key is pressed.
    hold: bool,
}

fn parse_args() -> Args {
    let mut args = std::env::args().skip(1);
    let mut out = Args { command: None, cwd: None, hold: false };
    let mut command: Vec<String> = Vec::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-e" | "--command" => {
                command = args.by_ref().collect();
            }
            "-d" | "--working-directory" => out.cwd = args.next().map(PathBuf::from),
            "--hold" => out.hold = true,
            "-h" | "--help" => {
                println!("Usage: ozi-terminal [-d DIR] [--hold] [-e COMMAND ARGS...]");
                std::process::exit(0);
            }
            "--version" => {
                println!("ozi-terminal {}", env!("CARGO_PKG_VERSION"));
                std::process::exit(0);
            }
            other => {
                // Like most terminals: a lone argument after the options is the folder.
                if out.cwd.is_none() && std::path::Path::new(other).is_dir() {
                    out.cwd = Some(other.into());
                }
            }
        }
    }
    if out.hold && !command.is_empty() {
        let mut wrapped = vec![
            "sh".to_string(),
            "-c".to_string(),
            "\"$@\"; printf '\\n\\033[2m[bitti: kapatmak için Enter]\\033[0m'; read -r _".to_string(),
            "sh".to_string(),
        ];
        wrapped.append(&mut command);
        command = wrapped;
    }
    if let Some((program, rest)) = command.split_first() {
        out.command = Some(tty::Shell::new(program.clone(), rest.to_vec()));
    }
    out
}

struct Clicks {
    at: Instant,
    point: Point,
    count: u8,
}

pub struct App {
    proxy: EventLoopProxy<UserEvent>,
    args: Args,
    window: Option<Rc<Window>>,
    surface: Option<softbuffer::Surface<Rc<Window>, Rc<Window>>>,
    clipboard: Option<smithay_clipboard::Clipboard>,
    pub fonts: font::Fonts,
    pub look: look::Look,
    pub tabs: Vec<Tab>,
    pub active: usize,
    next_id: u64,
    mods: ModifiersState,
    pub focused: bool,
    pointer: PhysicalPosition<f64>,
    selecting: bool,
    clicks: Option<Clicks>,
    scroll_rest: f64,
    pub hover_tab: Option<usize>,
}

impl App {
    fn new(proxy: EventLoopProxy<UserEvent>, args: Args) -> App {
        App {
            proxy,
            args,
            window: None,
            surface: None,
            clipboard: None,
            fonts: font::Fonts::new("monospace", FONT_PX),
            look: look::load(),
            tabs: Vec::new(),
            active: 0,
            next_id: 1,
            mods: ModifiersState::empty(),
            focused: true,
            pointer: PhysicalPosition::new(0.0, 0.0),
            selecting: false,
            clicks: None,
            scroll_rest: 0.0,
            hover_tab: None,
        }
    }

    fn scale(&self) -> f32 {
        self.window.as_ref().map(|w| w.scale_factor() as f32).unwrap_or(1.0)
    }

    pub fn padding(&self) -> usize {
        (PADDING * self.scale()).round() as usize
    }

    pub fn tab_bar_height(&self) -> usize {
        if self.tabs.len() > 1 { self.fonts.cell_height + (14.0 * self.scale()) as usize } else { 0 }
    }

    fn size(&self) -> (usize, usize) {
        self.window.as_ref().map(|w| {
            let s = w.inner_size();
            (s.width as usize, s.height as usize)
        }).unwrap_or((800, 500))
    }

    /// Columns and lines that fit the window.
    fn grid_size(&self) -> WindowSize {
        let (w, h) = self.size();
        let pad = self.padding();
        let cw = self.fonts.cell_width;
        let ch = self.fonts.cell_height;
        let cols = (w.saturating_sub(2 * pad) / cw).max(2);
        let lines = (h.saturating_sub(2 * pad + self.tab_bar_height()) / ch).max(1);
        WindowSize { num_lines: lines as u16, num_cols: cols as u16, cell_width: cw as u16, cell_height: ch as u16 }
    }

    fn resize_all(&mut self) {
        let size = self.grid_size();
        for tab in &self.tabs {
            tab.term.lock().resize(TermSize::new(size.num_cols as usize, size.num_lines as usize));
            let _ = tab.sender.send(Msg::Resize(size));
        }
        self.redraw();
    }

    fn redraw(&self) {
        if let Some(w) = &self.window {
            w.request_redraw();
        }
    }

    fn new_tab(&mut self) {
        let cwd = self.tabs.get(self.active).and_then(Tab::cwd).or_else(|| self.args.cwd.clone());
        let id = self.next_id;
        self.next_id += 1;
        // The tab bar appears with the second tab: size the grid with it.
        let had_bar = self.tab_bar_height() > 0;
        let size = self.grid_size();
        let options = tty::Options {
            shell: if self.tabs.is_empty() { self.args.command.clone() } else { None },
            working_directory: cwd,
            drain_on_exit: false,
            env: HashMap::from([("TERM_PROGRAM".into(), "ozi-terminal".into())]),
        };
        let pty = match tty::new(&options, size, id) {
            Ok(pty) => pty,
            Err(err) => {
                eprintln!("ozi-terminal: could not start the shell: {err}");
                return;
            }
        };
        let pid = pty.child().id();
        let proxy = Proxy { tab: id, proxy: self.proxy.clone() };
        let config = Config { scrolling_history: 10_000, ..Config::default() };
        let term = Term::new(config, &TermSize::new(size.num_cols as usize, size.num_lines as usize), proxy.clone());
        let term = Arc::new(FairMutex::new(term));
        let event_loop = match PtyLoop::new(term.clone(), proxy, pty, false, false) {
            Ok(l) => l,
            Err(err) => {
                eprintln!("ozi-terminal: {err}");
                return;
            }
        };
        let sender = event_loop.channel();
        event_loop.spawn();
        term.lock().is_focused = self.focused;
        self.tabs.push(Tab { id, term, sender, title: String::from("Terminal"), pid });
        self.active = self.tabs.len() - 1;
        if had_bar != (self.tab_bar_height() > 0) {
            self.resize_all();
        }
        self.update_title();
        self.redraw();
    }

    fn close_tab(&mut self, index: usize, event_loop: &ActiveEventLoop) {
        if index >= self.tabs.len() {
            return;
        }
        let tab = self.tabs.remove(index);
        let _ = tab.sender.send(Msg::Shutdown);
        if self.tabs.is_empty() {
            event_loop.exit();
            return;
        }
        if self.active > index || self.active >= self.tabs.len() {
            self.active = self.active.saturating_sub(1).min(self.tabs.len() - 1);
        }
        if self.tabs.len() == 1 {
            self.resize_all();
        }
        self.update_title();
        self.redraw();
    }

    fn switch_to(&mut self, index: usize) {
        if index < self.tabs.len() && index != self.active {
            self.active = index;
            self.update_title();
            self.redraw();
        }
    }

    fn update_title(&self) {
        if let (Some(w), Some(tab)) = (&self.window, self.tabs.get(self.active)) {
            w.set_title(&tab.title);
        }
    }

    fn tab(&self) -> Option<&Tab> {
        self.tabs.get(self.active)
    }

    // ---- clipboard ------------------------------------------------------

    fn copy(&self, kind: ClipboardType) {
        let Some(tab) = self.tab() else { return };
        let Some(text) = tab.term.lock().selection_to_string() else { return };
        if let Some(cb) = &self.clipboard {
            match kind {
                ClipboardType::Clipboard => cb.store(text),
                ClipboardType::Selection => cb.store_primary(text),
            }
        }
    }

    fn clipboard_text(&self, kind: ClipboardType) -> String {
        let Some(cb) = &self.clipboard else { return String::new() };
        match kind {
            ClipboardType::Clipboard => cb.load(),
            ClipboardType::Selection => cb.load_primary(),
        }
        .unwrap_or_default()
    }

    fn paste(&self, kind: ClipboardType) {
        let text = self.clipboard_text(kind);
        let Some(tab) = self.tab() else { return };
        if text.is_empty() {
            return;
        }
        let bracketed = tab.term.lock().mode().contains(TermMode::BRACKETED_PASTE);
        let text = if bracketed {
            // A pasted end marker must not end the paste early.
            format!("\x1b[200~{}\x1b[201~", text.replace('\x1b', ""))
        } else {
            text.replace("\r\n", "\r").replace('\n', "\r")
        };
        tab.write(text.into_bytes());
        self.to_bottom();
    }

    fn to_bottom(&self) {
        if let Some(tab) = self.tab() {
            let mut term = tab.term.lock();
            if term.grid().display_offset() != 0 {
                term.scroll_display(Scroll::Bottom);
                drop(term);
                self.redraw();
            }
        }
    }

    // ---- pointer --------------------------------------------------------

    /// The grid cell under the pointer, and which half of it.
    fn cell_at(&self, pos: PhysicalPosition<f64>) -> Option<(Point, Side)> {
        let tab = self.tab()?;
        let pad = self.padding() as f64;
        let top = pad + self.tab_bar_height() as f64;
        let cw = self.fonts.cell_width as f64;
        let ch = self.fonts.cell_height as f64;
        let term = tab.term.lock();
        let cols = term.columns();
        let lines = term.screen_lines();
        let x = ((pos.x - pad) / cw).max(0.0);
        let row = (((pos.y - top) / ch).max(0.0) as usize).min(lines - 1);
        let col = (x as usize).min(cols - 1);
        let side = if x.fract() < 0.5 { Side::Left } else { Side::Right };
        let offset = term.grid().display_offset() as i32;
        Some((Point::new(Line(row as i32 - offset), Column(col)), side))
    }

    fn mouse_reporting(&self) -> Option<TermMode> {
        let mode = *self.tab()?.term.lock().mode();
        (mode.intersects(TermMode::MOUSE_MODE) && !self.mods.shift_key()).then_some(mode)
    }

    /// An SGR mouse report: button, cell (1-based), pressed or released.
    fn report_mouse(&self, button: u8, pressed: bool) {
        let Some(tab) = self.tab() else { return };
        let Some((point, _)) = self.cell_at(self.pointer) else { return };
        let offset = tab.term.lock().grid().display_offset() as i32;
        let (col, row) = (point.column.0 + 1, point.line.0 + offset + 1);
        let mods = 4 * self.mods.shift_key() as u8 + 8 * self.mods.alt_key() as u8 + 16 * self.mods.control_key() as u8;
        let end = if pressed { 'M' } else { 'm' };
        tab.write(format!("\x1b[<{};{col};{row}{end}", button + mods).into_bytes());
    }

    fn tab_at(&self, x: f64, y: f64) -> Option<usize> {
        if y >= self.tab_bar_height() as f64 || self.tabs.len() < 2 {
            return None;
        }
        let (w, _) = self.size();
        let width = render::tab_width(w, self.tabs.len());
        let i = (x / width as f64) as usize;
        (i < self.tabs.len()).then_some(i)
    }

    fn on_mouse_button(&mut self, button: MouseButton, state: ElementState, event_loop: &ActiveEventLoop) {
        let (x, y) = (self.pointer.x, self.pointer.y);
        if state == ElementState::Pressed && let Some(i) = self.tab_at(x, y) {
            match button {
                MouseButton::Left => self.switch_to(i),
                MouseButton::Middle => self.close_tab(i, event_loop),
                _ => {}
            }
            return;
        }
        if self.mouse_reporting().is_some() {
            let code = match button {
                MouseButton::Left => 0,
                MouseButton::Middle => 1,
                MouseButton::Right => 2,
                _ => return,
            };
            self.report_mouse(code, state == ElementState::Pressed);
            return;
        }
        match (button, state) {
            (MouseButton::Left, ElementState::Pressed) => {
                let Some((point, side)) = self.cell_at(self.pointer) else { return };
                let now = Instant::now();
                let count = match &self.clicks {
                    Some(c) if c.point == point && now.duration_since(c.at) < Duration::from_millis(400) => c.count % 3 + 1,
                    _ => 1,
                };
                self.clicks = Some(Clicks { at: now, point, count });
                let ty = match count {
                    2 => SelectionType::Semantic,
                    3 => SelectionType::Lines,
                    _ => SelectionType::Simple,
                };
                if let Some(tab) = self.tab() {
                    // One click clears; dragging starts a new selection. Two: a word, three: the line.
                    tab.term.lock().selection = (count > 1).then(|| Selection::new(ty, point, side));
                }
                self.selecting = true;
                self.redraw();
            }
            (MouseButton::Left, ElementState::Released) => {
                self.selecting = false;
                self.copy(ClipboardType::Selection);
            }
            (MouseButton::Middle, ElementState::Pressed) => self.paste(ClipboardType::Selection),
            _ => {}
        }
    }

    fn on_pointer_moved(&mut self) {
        let hover = self.tab_at(self.pointer.x, self.pointer.y);
        if hover != self.hover_tab {
            self.hover_tab = hover;
            self.redraw();
        }
        if let Some(w) = &self.window {
            w.set_cursor(if hover.is_some() { CursorIcon::Default } else { CursorIcon::Text });
        }
        if !self.selecting {
            return;
        }
        let Some((point, side)) = self.cell_at(self.pointer) else { return };
        if let Some(tab) = self.tab() {
            let mut term = tab.term.lock();
            match term.selection.as_mut() {
                Some(sel) => sel.update(point, side),
                None => term.selection = Some(Selection::new(SelectionType::Simple, point, side)),
            }
        }
        self.redraw();
    }

    fn on_scroll(&mut self, delta: MouseScrollDelta) {
        let lines = match delta {
            MouseScrollDelta::LineDelta(_, y) => y as f64 * 3.0,
            MouseScrollDelta::PixelDelta(p) => p.y / self.fonts.cell_height as f64,
        } + self.scroll_rest;
        let whole = lines.trunc() as i32;
        self.scroll_rest = lines.fract();
        if whole == 0 {
            return;
        }
        if self.mouse_reporting().is_some() {
            for _ in 0..whole.unsigned_abs() {
                self.report_mouse(if whole > 0 { 64 } else { 65 }, true);
            }
            return;
        }
        let Some(tab) = self.tab() else { return };
        let mode = *tab.term.lock().mode();
        if mode.contains(TermMode::ALT_SCREEN) && mode.contains(TermMode::ALTERNATE_SCROLL) {
            let key = if whole > 0 { "A" } else { "B" };
            let prefix = if mode.contains(TermMode::APP_CURSOR) { "\x1bO" } else { "\x1b[" };
            let keys: String = (0..whole.unsigned_abs()).map(|_| format!("{prefix}{key}")).collect();
            tab.write(keys.into_bytes());
        } else {
            tab.term.lock().scroll_display(Scroll::Delta(whole));
            self.redraw();
        }
    }

    // ---- keys -----------------------------------------------------------

    fn set_font_size(&mut self, px: f32) {
        self.fonts.set_size(px * self.scale());
        self.resize_all();
    }

    /// The terminal's own shortcuts; true when the key was one.
    fn shortcut(&mut self, key: &Key, event_loop: &ActiveEventLoop) -> bool {
        let m = self.mods;
        let ctrl_shift = m.control_key() && m.shift_key();
        let lower = match key {
            Key::Character(c) => c.to_lowercase(),
            _ => String::new(),
        };
        match key {
            Key::Character(_) if ctrl_shift && lower == "c" => self.copy(ClipboardType::Clipboard),
            Key::Character(_) if ctrl_shift && lower == "v" => self.paste(ClipboardType::Clipboard),
            Key::Character(_) if ctrl_shift && lower == "t" => self.new_tab(),
            Key::Character(_) if ctrl_shift && lower == "w" => self.close_tab(self.active, event_loop),
            Key::Character(_) if ctrl_shift && lower == "n" => {
                if let Ok(me) = std::env::current_exe() {
                    let mut command = std::process::Command::new(me);
                    if let Some(dir) = self.tab().and_then(Tab::cwd) {
                        command.arg("-d").arg(dir);
                    }
                    let _ = command.spawn();
                }
            }
            Key::Character(_) if m.control_key() && (lower == "=" || lower == "+") => {
                self.set_font_size(self.fonts.px / self.scale() + 1.0)
            }
            Key::Character(_) if m.control_key() && lower == "-" => self.set_font_size(self.fonts.px / self.scale() - 1.0),
            Key::Character(_) if m.control_key() && lower == "0" => self.set_font_size(FONT_PX),
            Key::Character(_) if m.alt_key() && !m.control_key() && lower.len() == 1 && self.tabs.len() > 1 => {
                match lower.parse::<usize>() {
                    Ok(n @ 1..=9) => self.switch_to(n - 1),
                    _ => return false,
                }
            }
            Key::Named(NamedKey::PageUp) if m.control_key() => {
                self.switch_to((self.active + self.tabs.len() - 1) % self.tabs.len().max(1))
            }
            Key::Named(NamedKey::PageDown) if m.control_key() => self.switch_to((self.active + 1) % self.tabs.len().max(1)),
            Key::Named(NamedKey::Tab) if m.control_key() => {
                let n = self.tabs.len().max(1);
                self.switch_to(if m.shift_key() { (self.active + n - 1) % n } else { (self.active + 1) % n })
            }
            Key::Named(NamedKey::PageUp | NamedKey::PageDown | NamedKey::Home | NamedKey::End) if m.shift_key() => {
                let Some(tab) = self.tab() else { return true };
                if tab.term.lock().mode().contains(TermMode::ALT_SCREEN) {
                    return false;
                }
                let scroll = match key {
                    Key::Named(NamedKey::PageUp) => Scroll::PageUp,
                    Key::Named(NamedKey::PageDown) => Scroll::PageDown,
                    Key::Named(NamedKey::Home) => Scroll::Top,
                    _ => Scroll::Bottom,
                };
                tab.term.lock().scroll_display(scroll);
                self.redraw();
            }
            _ => return false,
        }
        true
    }

    // ---- terminal events ------------------------------------------------

    fn on_term_event(&mut self, id: u64, event: TermEvent, event_loop: &ActiveEventLoop) {
        let Some(index) = self.tabs.iter().position(|t| t.id == id) else { return };
        match event {
            TermEvent::Wakeup | TermEvent::CursorBlinkingChange | TermEvent::MouseCursorDirty => {
                if index == self.active {
                    self.redraw();
                }
            }
            TermEvent::Title(title) => {
                self.tabs[index].title = title;
                self.update_title();
                self.redraw();
            }
            TermEvent::ResetTitle => {
                self.tabs[index].title = "Terminal".into();
                self.update_title();
                self.redraw();
            }
            TermEvent::ClipboardStore(kind, text) => {
                if let Some(cb) = &self.clipboard {
                    match kind {
                        ClipboardType::Clipboard => cb.store(text),
                        ClipboardType::Selection => cb.store_primary(text),
                    }
                }
            }
            TermEvent::ClipboardLoad(kind, format) => {
                let text = self.clipboard_text(kind);
                self.tabs[index].write(format(&text).into_bytes());
            }
            TermEvent::ColorRequest(i, format) => {
                let colors = *self.tabs[index].term.lock().colors();
                let rgb = colors[i].unwrap_or_else(|| {
                    if i < 256 { self.look.indexed(i as u8) } else { self.look.named(named_from_index(i)) }
                });
                self.tabs[index].write(format(rgb).into_bytes());
            }
            TermEvent::PtyWrite(text) => self.tabs[index].write(text.into_bytes()),
            TermEvent::TextAreaSizeRequest(format) => {
                let size = self.grid_size();
                self.tabs[index].write(format(size).into_bytes());
            }
            TermEvent::Bell => {
                if !self.focused && let Some(w) = &self.window {
                    w.request_user_attention(Some(winit::window::UserAttentionType::Informational));
                }
            }
            TermEvent::Exit | TermEvent::ChildExit(_) => self.close_tab(index, event_loop),
        }
    }
}

fn named_from_index(i: usize) -> NamedColor {
    match i {
        257 => NamedColor::Background,
        258 => NamedColor::Cursor,
        _ => NamedColor::Foreground,
    }
}

impl ApplicationHandler<UserEvent> for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.window.is_some() {
            return;
        }
        let mut attrs = Window::default_attributes()
            .with_title("Terminal")
            .with_transparent(true)
            .with_inner_size(LogicalSize::new(860.0, 540.0));
        #[cfg(target_os = "linux")]
        {
            use winit::platform::wayland::WindowAttributesExtWayland;
            attrs = attrs.with_name("ozi-terminal", "ozi-terminal");
        }
        let window = match event_loop.create_window(attrs) {
            Ok(w) => Rc::new(w),
            Err(err) => {
                eprintln!("ozi-terminal: no window: {err}");
                event_loop.exit();
                return;
            }
        };
        window.set_cursor(CursorIcon::Text);
        let context = softbuffer::Context::new(window.clone()).expect("softbuffer context");
        self.surface = Some(softbuffer::Surface::new(&context, window.clone()).expect("softbuffer surface"));
        // The clipboard needs the Wayland connection winit opened.
        {
            use winit::raw_window_handle::{HasDisplayHandle, RawDisplayHandle};
            if let Ok(handle) = window.display_handle()
                && let RawDisplayHandle::Wayland(wl) = handle.as_raw()
            {
                self.clipboard = Some(unsafe { smithay_clipboard::Clipboard::new(wl.display.as_ptr()) });
            }
        }
        self.window = Some(window);
        self.fonts.set_size(FONT_PX * self.scale());
        self.new_tab();
        self.resize_all();
    }

    fn user_event(&mut self, event_loop: &ActiveEventLoop, event: UserEvent) {
        match event {
            UserEvent::Term(id, event) => self.on_term_event(id, event, event_loop),
            UserEvent::LookChanged => {
                let look = look::load();
                if look != self.look {
                    self.look = look;
                    self.redraw();
                }
            }
        }
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _id: WindowId, event: WindowEvent) {
        match event {
            WindowEvent::CloseRequested => {
                for tab in &self.tabs {
                    let _ = tab.sender.send(Msg::Shutdown);
                }
                event_loop.exit();
            }
            WindowEvent::Resized(_) => self.resize_all(),
            WindowEvent::ScaleFactorChanged { .. } => {
                self.fonts.set_size(FONT_PX * self.scale());
                self.resize_all();
            }
            WindowEvent::Focused(focused) => {
                self.focused = focused;
                for tab in &self.tabs {
                    let mut term = tab.term.lock();
                    term.is_focused = focused;
                    if term.mode().contains(TermMode::FOCUS_IN_OUT) {
                        drop(term);
                        tab.write(if focused { b"\x1b[I".to_vec() } else { b"\x1b[O".to_vec() });
                    }
                }
                self.redraw();
            }
            WindowEvent::ModifiersChanged(m) => self.mods = m.state(),
            WindowEvent::KeyboardInput { event, .. } if event.state == ElementState::Pressed => {
                if self.shortcut(&event.logical_key, event_loop) {
                    return;
                }
                let Some(tab) = self.tab() else { return };
                let mode = *tab.term.lock().mode();
                if let Some(bytes) = keys::bytes(&event.logical_key, event.text.as_deref(), self.mods, mode) {
                    tab.term.lock().selection = None;
                    tab.write(bytes);
                    self.to_bottom();
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
                self.pointer = position;
                self.on_pointer_moved();
            }
            WindowEvent::CursorLeft { .. } => {
                if self.hover_tab.take().is_some() {
                    self.redraw();
                }
            }
            WindowEvent::MouseInput { state, button, .. } => self.on_mouse_button(button, state, event_loop),
            WindowEvent::MouseWheel { delta, .. } => self.on_scroll(delta),
            WindowEvent::RedrawRequested => {
                let (w, h) = self.size();
                let (Some(nw), Some(nh)) = (NonZeroU32::new(w as u32), NonZeroU32::new(h as u32)) else { return };
                let Some(mut surface) = self.surface.take() else { return };
                if surface.resize(nw, nh).is_ok()
                    && let Ok(mut buffer) = surface.buffer_mut()
                {
                    render::draw(self, &mut buffer, w, h);
                    let _ = buffer.present();
                }
                self.surface = Some(surface);
            }
            _ => {}
        }
    }
}

/// Tell the window when the desktop look changes (a new theme or wallpaper).
fn watch_look(proxy: EventLoopProxy<UserEvent>) {
    std::thread::spawn(move || {
        let path = look::config_path();
        let stamp = || std::fs::metadata(&path).and_then(|m| m.modified()).ok();
        let mut last: Option<SystemTime> = stamp();
        loop {
            std::thread::sleep(Duration::from_secs(2));
            let now = stamp();
            if now != last {
                last = now;
                if proxy.send_event(UserEvent::LookChanged).is_err() {
                    return;
                }
            }
        }
    });
}

fn main() {
    let args = parse_args();
    tty::setup_env();
    let event_loop = match EventLoop::<UserEvent>::with_user_event().build() {
        Ok(l) => l,
        Err(err) => {
            eprintln!("ozi-terminal: {err}");
            std::process::exit(1);
        }
    };
    let proxy = event_loop.create_proxy();
    watch_look(proxy.clone());
    let mut app = App::new(proxy, args);
    if let Err(err) = event_loop.run_app(&mut app) {
        eprintln!("ozi-terminal: {err}");
        std::process::exit(1);
    }
}
