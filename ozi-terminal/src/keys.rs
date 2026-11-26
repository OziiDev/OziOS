//! Keys to the bytes a terminal program expects (xterm conventions).

use alacritty_terminal::term::TermMode;
use winit::keyboard::{Key, ModifiersState, NamedKey};

/// xterm's modifier parameter: 1 + Shift 1 + Alt 2 + Ctrl 4.
fn modifier_param(mods: ModifiersState) -> u8 {
    1 + mods.shift_key() as u8 + 2 * mods.alt_key() as u8 + 4 * mods.control_key() as u8
}

/// `ESC [ 1 ; m X` with modifiers, `ESC O X` in application mode, else `ESC [ X`.
fn cursor_key(letter: char, mods: ModifiersState, app: bool) -> Vec<u8> {
    let m = modifier_param(mods);
    if m > 1 {
        format!("\x1b[1;{m}{letter}").into_bytes()
    } else if app {
        format!("\x1bO{letter}").into_bytes()
    } else {
        format!("\x1b[{letter}").into_bytes()
    }
}

/// `ESC [ n ~`, with `; m` when modified.
fn tilde_key(n: u8, mods: ModifiersState) -> Vec<u8> {
    let m = modifier_param(mods);
    if m > 1 { format!("\x1b[{n};{m}~").into_bytes() } else { format!("\x1b[{n}~").into_bytes() }
}

/// The bytes for a key press; None when the key sends nothing.
pub fn bytes(key: &Key, text: Option<&str>, mods: ModifiersState, mode: TermMode) -> Option<Vec<u8>> {
    let app_cursor = mode.contains(TermMode::APP_CURSOR);
    let alt = |mut b: Vec<u8>| {
        if mods.alt_key() {
            b.insert(0, 0x1b);
        }
        b
    };
    let out = match key {
        Key::Named(named) => match named {
            NamedKey::Enter => alt(b"\r".to_vec()),
            NamedKey::Backspace => alt(if mods.control_key() { vec![0x08] } else { vec![0x7f] }),
            NamedKey::Tab if mods.shift_key() => b"\x1b[Z".to_vec(),
            NamedKey::Tab => alt(b"\t".to_vec()),
            NamedKey::Escape => alt(b"\x1b".to_vec()),
            NamedKey::Space if mods.control_key() => vec![0],
            NamedKey::Space => alt(b" ".to_vec()),
            NamedKey::ArrowUp => cursor_key('A', mods, app_cursor),
            NamedKey::ArrowDown => cursor_key('B', mods, app_cursor),
            NamedKey::ArrowRight => cursor_key('C', mods, app_cursor),
            NamedKey::ArrowLeft => cursor_key('D', mods, app_cursor),
            NamedKey::Home => cursor_key('H', mods, app_cursor),
            NamedKey::End => cursor_key('F', mods, app_cursor),
            NamedKey::Insert => tilde_key(2, mods),
            NamedKey::Delete => tilde_key(3, mods),
            NamedKey::PageUp => tilde_key(5, mods),
            NamedKey::PageDown => tilde_key(6, mods),
            NamedKey::F1 => cursor_key('P', mods, true),
            NamedKey::F2 => cursor_key('Q', mods, true),
            NamedKey::F3 => cursor_key('R', mods, true),
            NamedKey::F4 => cursor_key('S', mods, true),
            NamedKey::F5 => tilde_key(15, mods),
            NamedKey::F6 => tilde_key(17, mods),
            NamedKey::F7 => tilde_key(18, mods),
            NamedKey::F8 => tilde_key(19, mods),
            NamedKey::F9 => tilde_key(20, mods),
            NamedKey::F10 => tilde_key(21, mods),
            NamedKey::F11 => tilde_key(23, mods),
            NamedKey::F12 => tilde_key(24, mods),
            _ => return text.filter(|t| !t.is_empty()).map(|t| alt(t.as_bytes().to_vec())),
        },
        Key::Character(chars) => {
            let mut it = chars.chars();
            let c = it.next()?;
            if mods.control_key() && it.next().is_none() {
                let code = match c.to_ascii_lowercase() {
                    'a'..='z' => Some(c.to_ascii_lowercase() as u8 - b'a' + 1),
                    '@' | '2' => Some(0),
                    '[' | '3' => Some(27),
                    '\\' | '4' => Some(28),
                    ']' | '5' => Some(29),
                    '^' | '6' => Some(30),
                    '_' | '-' | '7' => Some(31),
                    '?' | '8' => Some(127),
                    _ => None,
                };
                if let Some(code) = code {
                    return Some(alt(vec![code]));
                }
            }
            let t = text.filter(|t| !t.is_empty()).unwrap_or(chars.as_str());
            alt(t.as_bytes().to_vec())
        }
        _ => return None,
    };
    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn press(key: Key, text: Option<&str>, mods: ModifiersState) -> Vec<u8> {
        bytes(&key, text, mods, TermMode::empty()).unwrap_or_default()
    }

    #[test]
    fn common_keys() {
        let none = ModifiersState::empty();
        assert_eq!(press(Key::Named(NamedKey::Enter), None, none), b"\r");
        assert_eq!(press(Key::Named(NamedKey::Backspace), None, none), b"\x7f");
        assert_eq!(press(Key::Named(NamedKey::ArrowUp), None, none), b"\x1b[A");
        assert_eq!(press(Key::Named(NamedKey::ArrowLeft), None, ModifiersState::CONTROL), b"\x1b[1;5D");
        assert_eq!(press(Key::Named(NamedKey::Delete), None, none), b"\x1b[3~");
        assert_eq!(press(Key::Character("c".into()), Some("c"), ModifiersState::CONTROL), [3]);
        assert_eq!(press(Key::Character("x".into()), Some("x"), ModifiersState::ALT), b"\x1bx");
        assert_eq!(press(Key::Character("ş".into()), Some("ş"), none), "ş".as_bytes());
        let app = bytes(&Key::Named(NamedKey::ArrowUp), None, none, TermMode::APP_CURSOR).unwrap();
        assert_eq!(app, b"\x1bOA");
    }
}
