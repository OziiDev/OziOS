//! Clipboard history (Super+V): oziwm keeps the last texts copied in any
//! program, and puts one back on the clipboard when it is picked from the list.
//! Only text is kept, never what a password manager marks as secret, and only
//! in memory: the history ends with the session.

use std::{
    io::{Read, Write},
    os::fd::OwnedFd,
    sync::Arc,
};

use serde_json::{json, Value};
use smithay::{
    input::Seat,
    reexports::calloop::channel,
    wayland::selection::{
        data_device::{request_data_device_client_selection, set_data_device_selection},
        SelectionSource, SelectionTarget,
    },
};

use crate::{ipc, OziWm};

/// How many texts the history keeps, and how long one may be.
pub const KEEP: usize = 30;
pub const MAX_BYTES: usize = 256 * 1024;

const TEXT_TYPES: [&str; 5] = ["text/plain;charset=utf-8", "UTF8_STRING", "text/plain", "STRING", "TEXT"];

#[derive(Debug, Default)]
pub struct History {
    pub items: Vec<Arc<str>>,
    /// Texts read from programs arrive here, off the main thread.
    pub sender: Option<channel::Sender<String>>,
}

/// The text type to read from a selection's offered types, unless it is a secret.
pub fn pick_type(mime_types: &[String]) -> Option<String> {
    // KDE Wallet, KeePassXC and others mark passwords like this.
    if mime_types.iter().any(|m| m == "x-kde-passwordManagerHint") {
        return None;
    }
    TEXT_TYPES
        .iter()
        .find(|t| mime_types.iter().any(|m| m == *t))
        .map(|t| t.to_string())
}

/// Add a text to the front; an older copy of it moves up instead of repeating.
pub fn remember(items: &mut Vec<Arc<str>>, text: &str) -> bool {
    if text.trim().is_empty() || text.len() > MAX_BYTES {
        return false;
    }
    if items.first().is_some_and(|t| &**t == text) {
        return false;
    }
    items.retain(|t| &**t != text);
    items.insert(0, Arc::from(text));
    items.truncate(KEEP);
    true
}

impl OziWm {
    pub fn init_clipboard(&mut self) {
        let (sender, receiver) = channel::channel::<String>();
        self.clipboard.sender = Some(sender);
        let _ = self.loop_handle.insert_source(receiver, |event, _, state| {
            if let channel::Event::Msg(text) = event
                && remember(&mut state.clipboard.items, &text)
            {
                ipc::emit(state, "shell", json!({ "event": "clipboard-changed" }));
            }
        });
    }

    /// A program set the clipboard: read its text in the background.
    pub fn clipboard_offered(&mut self, ty: SelectionTarget, source: Option<SelectionSource>, seat: &Seat<OziWm>) {
        if ty != SelectionTarget::Clipboard {
            return;
        }
        let Some(source) = source else {
            return;
        };
        let Some(mime) = pick_type(&source.mime_types()) else {
            return;
        };
        let Some(sender) = self.clipboard.sender.clone() else {
            return;
        };
        let Ok((mut reader, writer)) = std::io::pipe() else {
            return;
        };
        if request_data_device_client_selection(seat, mime, OwnedFd::from(writer)).is_err() {
            return;
        }
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            let _ = (&mut reader).take(MAX_BYTES as u64 + 1).read_to_end(&mut bytes);
            if let Ok(text) = String::from_utf8(bytes) {
                let _ = sender.send(text);
            }
        });
    }

    /// A program pastes what oziwm put on the clipboard: write it out in the background.
    pub fn clipboard_send(&self, fd: OwnedFd, text: &Arc<str>) {
        let text = text.clone();
        std::thread::spawn(move || {
            let mut file = std::fs::File::from(fd);
            let _ = file.write_all(text.as_bytes());
        });
    }

    /// Put a text from the history back on the clipboard; it moves to the front.
    pub fn clipboard_use(&mut self, index: usize) -> bool {
        let Some(text) = self.clipboard.items.get(index).cloned() else {
            return false;
        };
        remember(&mut self.clipboard.items, &text);
        let types = TEXT_TYPES.iter().map(|t| t.to_string()).collect();
        set_data_device_selection(&self.display_handle, &self.seat, types, Some(text));
        ipc::emit(self, "shell", json!({ "event": "clipboard-changed" }));
        true
    }

    pub fn clipboard_remove(&mut self, index: Option<usize>) {
        match index {
            Some(i) if i < self.clipboard.items.len() => {
                self.clipboard.items.remove(i);
            }
            Some(_) => return,
            None => self.clipboard.items.clear(),
        }
        ipc::emit(self, "shell", json!({ "event": "clipboard-changed" }));
    }

    pub fn clipboard_json(&self) -> Value {
        Value::Array(self.clipboard.items.iter().map(|t| Value::String(t.to_string())).collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_text_newest_first_without_repeats() {
        let mut items = Vec::new();
        assert!(remember(&mut items, "a"));
        assert!(remember(&mut items, "b"));
        assert!(!remember(&mut items, "b"));
        assert!(remember(&mut items, "a"));
        assert_eq!(items.iter().map(|t| t.to_string()).collect::<Vec<_>>(), ["a", "b"]);
        assert!(!remember(&mut items, "   "));
        for i in 0..40 {
            remember(&mut items, &i.to_string());
        }
        assert_eq!(items.len(), KEEP);
    }

    #[test]
    fn reads_text_but_not_secrets() {
        let t = |v: &[&str]| v.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert_eq!(pick_type(&t(&["image/png", "text/plain"])), Some("text/plain".into()));
        assert_eq!(pick_type(&t(&["text/plain", "text/plain;charset=utf-8"])), Some("text/plain;charset=utf-8".into()));
        assert_eq!(pick_type(&t(&["image/png"])), None);
        assert_eq!(pick_type(&t(&["text/plain", "x-kde-passwordManagerHint"])), None);
    }
}
