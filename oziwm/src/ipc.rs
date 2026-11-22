//! JSON-lines socket for the shell and the `ozi` command. Protocol: docs/IPC.md.

use std::{
    ffi::OsStr,
    io::{self, Read, Write},
    os::unix::net::{UnixListener, UnixStream},
    path::PathBuf,
};

use serde_json::{json, Value};
use smithay::{
    desktop::Window,
    reexports::calloop::{generic::Generic, Interest, LoopHandle, Mode, PostAction},
    wayland::{compositor::with_states, shell::xdg::XdgToplevelSurfaceData},
};

use crate::{state::window_id, OziWm};

/// Requests a client may send. Unknown fields are ignored.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Request {
    Get(String),
    Focus(u64),
    Close(u64),
    Minimize(u64),
    Spawn(Vec<String>),
    Workspace(u32),
    /// Read ~/.config/ozios/desktop.json again (theme, glow, corners, speed).
    ReloadLook,
    ToggleLauncher,
    TogglePanel,
    ToggleTiling,
    /// Pretend a laptop key was pressed (for testing ozi-shell's handling).
    Key(String),
    Lock,
    Screenshot(Option<String>),
    Quit,
    Subscribe(Vec<String>),
}

pub fn parse(line: &[u8]) -> Result<Request, String> {
    let value: Value = serde_json::from_slice(line).map_err(|e| format!("not JSON: {e}"))?;
    let id = || {
        value
            .get("id")
            .and_then(Value::as_u64)
            .ok_or_else(|| "\"id\" (a number) is missing".to_string())
    };
    if let Some(what) = value.get("get") {
        let what = what.as_str().ok_or("\"get\" must be a string")?;
        return Ok(Request::Get(what.to_string()));
    }
    if let Some(topics) = value.get("subscribe") {
        let topics = topics
            .as_array()
            .ok_or("\"subscribe\" must be a list")?
            .iter()
            .filter_map(|t| t.as_str().map(String::from))
            .collect();
        return Ok(Request::Subscribe(topics));
    }
    match value.get("do").and_then(Value::as_str) {
        Some("focus") => Ok(Request::Focus(id()?)),
        Some("close") => Ok(Request::Close(id()?)),
        Some("minimize") => Ok(Request::Minimize(id()?)),
        Some("quit") => Ok(Request::Quit),
        Some("reload-look") => Ok(Request::ReloadLook),
        Some("toggle-launcher") => Ok(Request::ToggleLauncher),
        Some("toggle-panel") => Ok(Request::TogglePanel),
        Some("toggle-tiling") => Ok(Request::ToggleTiling),
        Some("key") => Ok(Request::Key(
            value.get("key").and_then(Value::as_str).unwrap_or_default().to_string(),
        )),
        Some("lock") => Ok(Request::Lock),
        Some("screenshot") => Ok(Request::Screenshot(
            value.get("path").and_then(Value::as_str).map(String::from),
        )),
        Some("workspace") => {
            let index = value
                .get("index")
                .and_then(Value::as_u64)
                .ok_or("\"index\" (a number) is missing")?;
            Ok(Request::Workspace(index as u32))
        }
        Some("spawn") => {
            let command: Vec<String> = value
                .get("command")
                .and_then(Value::as_array)
                .ok_or("\"command\" must be a list of strings")?
                .iter()
                .filter_map(|a| a.as_str().map(String::from))
                .collect();
            if command.is_empty() {
                return Err("\"command\" is empty".into());
            }
            Ok(Request::Spawn(command))
        }
        Some(other) => Err(format!("unknown action \"{other}\"")),
        None => Err("expected \"get\", \"do\" or \"subscribe\"".into()),
    }
}

fn ok(value: Value) -> Value {
    json!({ "ok": value })
}

fn error(message: impl Into<String>) -> Value {
    json!({ "error": message.into() })
}

pub fn window_json(state: &OziWm, window: &Window) -> Value {
    let (app_id, title) = window
        .toplevel()
        .map(|t| {
            with_states(t.wl_surface(), |states| {
                states
                    .data_map
                    .get::<XdgToplevelSurfaceData>()
                    .and_then(|d| d.lock().ok().map(|d| (d.app_id.clone(), d.title.clone())))
                    .unwrap_or_default()
            })
        })
        .unwrap_or_default();
    let loc = state.space.element_location(window).unwrap_or_default();
    let size = window.geometry().size;
    let focused = state.focused_window().as_ref() == Some(window);
    json!({
        "id": window_id(window),
        "app_id": app_id.unwrap_or_default(),
        "title": title.unwrap_or_default(),
        "workspace": crate::workspace::workspace_of(window) + 1,
        "focused": focused,
        "minimized": state.minimized.contains(window),
        "x": loc.x, "y": loc.y, "width": size.w, "height": size.h,
    })
}

/// What to do with a request: answer it, or turn the connection into an event stream.
enum Outcome {
    Reply(Value),
    Subscribe(Vec<String>),
}

fn handle(state: &mut OziWm, request: Request) -> Outcome {
    let reply = match request {
        Request::Get(what) => match what.as_str() {
            "version" => ok(json!({ "version": env!("CARGO_PKG_VERSION") })),
            "windows" => ok(Value::Array(
                state
                    .space
                    .elements()
                    .chain(state.minimized.iter())
                    .chain(state.hidden.iter().map(|(w, _)| w))
                    .map(|w| window_json(state, w))
                    .collect(),
            )),
            "outputs" => ok(Value::Array(
                state
                    .space
                    .outputs()
                    .filter_map(|o| {
                        let geo = state.space.output_geometry(o)?;
                        Some(json!({
                            "name": o.name(),
                            "x": geo.loc.x, "y": geo.loc.y,
                            "width": geo.size.w, "height": geo.size.h,
                            "scale": o.current_scale().fractional_scale(),
                        }))
                    })
                    .collect(),
            )),
            "workspaces" => ok(state.workspaces_json()),
            "stats" => ok(state.stats.json()),
            other => error(format!("nothing called \"{other}\"")),
        },
        Request::Focus(id) => match state.window_by_id(id) {
            Some(window) => {
                state.focus_window(Some(window));
                ok(Value::Null)
            }
            None => error(format!("no window {id}")),
        },
        Request::Close(id) => match state.window_by_id(id).and_then(|w| w.toplevel().cloned()) {
            Some(toplevel) => {
                toplevel.send_close();
                ok(Value::Null)
            }
            None => error(format!("no window {id}")),
        },
        Request::Minimize(id) => match state.window_by_id(id) {
            Some(window) => {
                state.minimize(&window);
                ok(Value::Null)
            }
            None => error(format!("no window {id}")),
        },
        Request::Spawn(command) => {
            state.spawn(&command);
            ok(Value::Null)
        }
        Request::Workspace(index) if (1..=crate::workspace::WORKSPACES as u32).contains(&index) => {
            state.switch_workspace(index as usize - 1);
            ok(Value::Null)
        }
        Request::Workspace(index) => error(format!("no workspace {index}")),
        Request::ReloadLook => {
            state.reload_look();
            ok(Value::Null)
        }
        Request::Screenshot(path) => {
            let path = state.request_screenshot(path.map(std::path::PathBuf::from));
            ok(json!(path.to_string_lossy()))
        }
        Request::Lock => {
            state.lock();
            ok(Value::Null)
        }
        Request::Key(key) => {
            emit_key(state, &key);
            ok(Value::Null)
        }
        Request::ToggleTiling => {
            state.toggle_tiling();
            ok(Value::Null)
        }
        Request::TogglePanel => {
            emit_panel(state);
            ok(Value::Null)
        }
        Request::ToggleLauncher => {
            emit_launcher(state);
            ok(Value::Null)
        }
        Request::Quit => {
            state.loop_signal.stop();
            ok(Value::Null)
        }
        Request::Subscribe(topics) => return Outcome::Subscribe(topics),
    };
    Outcome::Reply(reply)
}

pub struct Subscriber {
    stream: UnixStream,
    topics: Vec<String>,
}

fn write_line(mut stream: &UnixStream, value: &Value) -> io::Result<()> {
    let mut line = value.to_string();
    line.push('\n');
    stream.write_all(line.as_bytes())
}

/// Send an event to everyone subscribed to `topic`; drop the ones that went away.
fn emit(state: &mut OziWm, topic: &str, event: Value) {
    state.ipc_subscribers.retain(|s| {
        !s.topics.iter().any(|t| t == topic) || write_line(&s.stream, &event).is_ok()
    });
}

pub fn emit_window(state: &mut OziWm, window: &Window, kind: &str) {
    if state.ipc_subscribers.is_empty() {
        return;
    }
    let event = json!({ "event": kind, "window": window_json(state, window) });
    emit(state, "windows", event);
}

pub fn emit_closed(state: &mut OziWm, id: u64) {
    emit(state, "windows", json!({ "event": "window-closed", "id": id }));
}

pub fn emit_workspace(state: &mut OziWm, index: usize) {
    let event = json!({ "event": "workspace", "index": index + 1, "workspaces": state.workspaces_json() });
    emit(state, "windows", event);
}

pub fn emit_locked(state: &mut OziWm, locked: bool) {
    emit(state, "shell", json!({ "event": "locked", "locked": locked }));
}

/// A laptop key for ozi-shell to act on (and show its gauge for).
pub fn emit_key(state: &mut OziWm, key: &str) {
    emit(state, "shell", json!({ "event": "key", "key": key }));
}

pub fn emit_panel(state: &mut OziWm) {
    emit(state, "shell", json!({ "event": "panel" }));
}

/// Ask ozi-shell to open or close the launcher.
pub fn emit_launcher(state: &mut OziWm) {
    emit(state, "shell", json!({ "event": "launcher" }));
}

pub fn emit_focus(state: &mut OziWm, id: Option<u64>) {
    emit(state, "windows", json!({ "event": "focus", "id": id }));
}

pub fn socket_path(wayland_socket: &OsStr) -> PathBuf {
    let dir = std::env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into());
    let mut name = std::ffi::OsString::from("oziwm-");
    name.push(wayland_socket);
    name.push(".sock");
    PathBuf::from(dir).join(name)
}

pub fn listen(handle: LoopHandle<'static, OziWm>, wayland_socket: &OsStr) -> io::Result<PathBuf> {
    let path = socket_path(wayland_socket);
    // A socket left by a crashed oziwm with the same display name.
    let _ = std::fs::remove_file(&path);
    let listener = UnixListener::bind(&path)?;
    listener.set_nonblocking(true)?;

    handle
        .insert_source(
            Generic::new(listener, Interest::READ, Mode::Level),
            |_, listener, state| {
                loop {
                    match listener.accept() {
                        Ok((stream, _)) => accept(state, stream),
                        Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
                        Err(e) => {
                            tracing::warn!(%e, "IPC accept failed");
                            break;
                        }
                    }
                }
                Ok(PostAction::Continue)
            },
        )
        .map_err(|e| io::Error::other(e.to_string()))?;
    Ok(path)
}

fn accept(state: &mut OziWm, stream: UnixStream) {
    if stream.set_nonblocking(true).is_err() {
        return;
    }
    let mut buffer: Vec<u8> = Vec::new();
    let result = state.loop_handle.insert_source(
        Generic::new(stream, Interest::READ, Mode::Level),
        move |_, stream, state| {
            let mut socket: &UnixStream = stream;
            let mut chunk = [0u8; 4096];
            loop {
                match socket.read(&mut chunk) {
                    Ok(0) => return Ok(PostAction::Remove),
                    Ok(n) => buffer.extend_from_slice(&chunk[..n]),
                    Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
                    Err(_) => return Ok(PostAction::Remove),
                }
                if buffer.len() > 1 << 20 {
                    return Ok(PostAction::Remove);
                }
            }
            while let Some(end) = buffer.iter().position(|b| *b == b'\n') {
                let line: Vec<u8> = buffer.drain(..=end).collect();
                let line = &line[..line.len() - 1];
                if line.iter().all(u8::is_ascii_whitespace) {
                    continue;
                }
                let outcome = match parse(line) {
                    Ok(request) => handle(state, request),
                    Err(message) => Outcome::Reply(error(message)),
                };
                match outcome {
                    Outcome::Reply(reply) => {
                        if write_line(socket, &reply).is_err() {
                            return Ok(PostAction::Remove);
                        }
                    }
                    Outcome::Subscribe(topics) => {
                        if write_line(socket, &ok(Value::Null)).is_err() {
                            return Ok(PostAction::Remove);
                        }
                        if let Ok(copy) = socket.try_clone() {
                            state.ipc_subscribers.push(Subscriber { stream: copy, topics });
                        }
                        // From here on the connection only receives events.
                        return Ok(PostAction::Remove);
                    }
                }
            }
            Ok(PostAction::Continue)
        },
    );
    if let Err(e) = result {
        tracing::warn!(%e, "could not watch an IPC client");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn requests() {
        assert_eq!(parse(br#"{"get":"windows"}"#), Ok(Request::Get("windows".into())));
        assert_eq!(parse(br#"{"do":"focus","id":7}"#), Ok(Request::Focus(7)));
        assert_eq!(parse(br#"{"do":"close","id":3,"extra":true}"#), Ok(Request::Close(3)));
        assert_eq!(
            parse(br#"{"do":"spawn","command":["konsole","-e","htop"]}"#),
            Ok(Request::Spawn(vec!["konsole".into(), "-e".into(), "htop".into()]))
        );
        assert_eq!(parse(br#"{"do":"workspace","index":2}"#), Ok(Request::Workspace(2)));
        assert_eq!(parse(br#"{"do":"quit"}"#), Ok(Request::Quit));
        assert_eq!(parse(br#"{"do":"reload-look"}"#), Ok(Request::ReloadLook));
        assert_eq!(parse(br#"{"do":"toggle-launcher"}"#), Ok(Request::ToggleLauncher));
        assert_eq!(
            parse(br#"{"subscribe":["windows"]}"#),
            Ok(Request::Subscribe(vec!["windows".into()]))
        );
    }

    #[test]
    fn bad_requests_explain_themselves() {
        assert!(parse(b"hello").unwrap_err().contains("JSON"));
        assert!(parse(br#"{"do":"focus"}"#).unwrap_err().contains("id"));
        assert!(parse(br#"{"do":"fly"}"#).unwrap_err().contains("fly"));
        assert!(parse(br#"{"do":"spawn","command":[]}"#).unwrap_err().contains("empty"));
        assert!(parse(br#"{}"#).is_err());
    }

    #[test]
    fn socket_name_follows_the_display() {
        let path = socket_path(OsStr::new("wayland-2"));
        assert!(path.to_string_lossy().ends_with("/oziwm-wayland-2.sock"));
    }
}
