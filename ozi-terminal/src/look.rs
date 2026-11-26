//! Colours of the terminal, taken from the desktop look (~/.config/ozios/desktop.json):
//! the background is the desktop's ink, the cursor and the selection its accent.
//! The sixteen ANSI colours are a fixed, calm set that reads well on any dark ink.

use std::path::PathBuf;

use alacritty_terminal::vte::ansi::{Color, NamedColor, Rgb};
use alacritty_terminal::term::color::Colors;
use serde_json::Value;

#[derive(Debug, Clone, PartialEq)]
pub struct Look {
    pub ink: Rgb,
    pub raised: Rgb,
    pub text: Rgb,
    pub muted: Rgb,
    pub accent: Rgb,
    pub on_accent: Rgb,
    /// How opaque the background is, 0..1.
    pub opacity: f32,
    pub ansi: [Rgb; 16],
}

const fn rgb(r: u8, g: u8, b: u8) -> Rgb {
    Rgb { r, g, b }
}

/// The same themes as the desktop (python/ozipkg/themes.py, oziwm/src/theme.rs):
/// id, ink, raised, text, muted, accent.
const THEMES: [(&str, Rgb, Rgb, Rgb, Rgb, Rgb); 6] = [
    ("cyan", rgb(8, 11, 16), rgb(14, 19, 27), rgb(244, 252, 255), rgb(128, 150, 160), rgb(0, 229, 255)),
    ("aurora", rgb(11, 8, 20), rgb(19, 15, 33), rgb(246, 243, 255), rgb(150, 140, 178), rgb(176, 140, 255)),
    ("ember", rgb(16, 10, 8), rgb(27, 18, 14), rgb(255, 247, 240), rgb(172, 146, 132), rgb(255, 140, 64)),
    ("mint", rgb(7, 14, 12), rgb(12, 23, 20), rgb(240, 255, 250), rgb(130, 166, 153), rgb(60, 230, 160)),
    ("rose", rgb(16, 8, 11), rgb(27, 14, 19), rgb(255, 242, 246), rgb(176, 136, 151), rgb(255, 94, 140)),
    ("frost", rgb(242, 246, 249), rgb(232, 238, 243), rgb(12, 19, 25), rgb(92, 111, 122), rgb(0, 145, 172)),
];

const DARK_ANSI: [Rgb; 16] = [
    rgb(0x1d, 0x23, 0x2b), rgb(0xf0, 0x5d, 0x5e), rgb(0x5f, 0xd6, 0x8a), rgb(0xf2, 0xc1, 0x4e),
    rgb(0x5c, 0x9c, 0xf5), rgb(0xc4, 0x7f, 0xf0), rgb(0x3f, 0xd0, 0xd8), rgb(0xc9, 0xd1, 0xd9),
    rgb(0x5a, 0x66, 0x73), rgb(0xff, 0x7b, 0x7b), rgb(0x7d, 0xeb, 0xa4), rgb(0xff, 0xd8, 0x6e),
    rgb(0x82, 0xb6, 0xff), rgb(0xd8, 0x9c, 0xff), rgb(0x6d, 0xe6, 0xec), rgb(0xf6, 0xf8, 0xfa),
];

const LIGHT_ANSI: [Rgb; 16] = [
    rgb(0x24, 0x29, 0x2f), rgb(0xcf, 0x22, 0x2e), rgb(0x11, 0x7f, 0x3a), rgb(0x9a, 0x67, 0x00),
    rgb(0x09, 0x69, 0xda), rgb(0x82, 0x50, 0xdf), rgb(0x1b, 0x7c, 0x83), rgb(0x6e, 0x77, 0x81),
    rgb(0x57, 0x60, 0x6a), rgb(0xa4, 0x0e, 0x26), rgb(0x1a, 0x7f, 0x37), rgb(0x63, 0x3c, 0x01),
    rgb(0x21, 0x8b, 0xff), rgb(0xa4, 0x75, 0xf9), rgb(0x31, 0x92, 0xaa), rgb(0x8c, 0x95, 0x9f),
];

impl Default for Look {
    fn default() -> Self {
        from_theme("cyan")
    }
}

fn from_theme(id: &str) -> Look {
    let (_, ink, raised, text, muted, accent) = THEMES.iter().copied().find(|t| t.0 == id).unwrap_or(THEMES[0]);
    let light = id == "frost";
    Look {
        ink,
        raised,
        text,
        muted,
        accent,
        on_accent: if light { rgb(255, 255, 255) } else { ink },
        opacity: if light { 0.97 } else { 0.92 },
        ansi: if light { LIGHT_ANSI } else { DARK_ANSI },
    }
}

fn hex(value: Option<&Value>) -> Option<Rgb> {
    let text = value?.as_str()?.strip_prefix('#')?;
    if text.len() != 6 || !text.is_ascii() {
        return None;
    }
    let byte = |i: usize| u8::from_str_radix(&text[i..i + 2], 16).ok();
    Some(rgb(byte(0)?, byte(2)?, byte(4)?))
}

pub fn config_path() -> PathBuf {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config")))
        .unwrap_or_else(|| PathBuf::from("/tmp"));
    base.join("ozios/desktop.json")
}

pub fn parse(text: &str) -> Look {
    let Ok(value) = serde_json::from_str::<Value>(text) else {
        return Look::default();
    };
    let theme = value.get("theme").and_then(Value::as_str).unwrap_or("auto");
    let mut look = from_theme(theme);
    if theme == "auto"
        && let Some(colors) = value.get("colors")
        && let (Some(ink), Some(raised), Some(text), Some(muted), Some(accent)) = (
            hex(colors.get("ink")),
            hex(colors.get("raised")),
            hex(colors.get("text")),
            hex(colors.get("muted")),
            hex(colors.get("accent")),
        )
    {
        look = Look { ink, raised, text, muted, accent, ..from_theme("cyan") };
        look.on_accent = hex(colors.get("onAccent")).unwrap_or(ink);
    }
    if let Some(o) = value.get("terminal_opacity").and_then(Value::as_f64) {
        look.opacity = o.clamp(0.5, 1.0) as f32;
    }
    look
}

pub fn load() -> Look {
    std::fs::read_to_string(config_path()).map(|t| parse(&t)).unwrap_or_default()
}

impl Look {
    /// The colour of a cell's colour, after colours a program set (OSC 4/10/11).
    pub fn resolve(&self, color: Color, set: &Colors) -> Rgb {
        match color {
            Color::Spec(rgb) => rgb,
            Color::Named(name) => set[name].unwrap_or_else(|| self.named(name)),
            Color::Indexed(i) => set[i as usize].unwrap_or_else(|| self.indexed(i)),
        }
    }

    pub fn named(&self, name: NamedColor) -> Rgb {
        let i = name as usize;
        match name {
            NamedColor::Foreground | NamedColor::BrightForeground => self.text,
            NamedColor::Background => self.ink,
            NamedColor::Cursor => self.accent,
            NamedColor::DimForeground => mix(self.text, self.ink, 0.35),
            _ if i < 16 => self.ansi[i],
            // Dim black..white
            _ if (NamedColor::DimBlack as usize..=NamedColor::DimWhite as usize).contains(&i) => {
                mix(self.ansi[i - NamedColor::DimBlack as usize], self.ink, 0.35)
            }
            _ => self.text,
        }
    }

    pub fn indexed(&self, i: u8) -> Rgb {
        match i {
            0..=15 => self.ansi[i as usize],
            16..=231 => {
                let i = i - 16;
                let level = |v: u8| if v == 0 { 0 } else { 55 + v * 40 };
                rgb(level(i / 36), level((i / 6) % 6), level(i % 6))
            }
            _ => {
                let v = 8 + (i - 232) * 10;
                rgb(v, v, v)
            }
        }
    }
}

pub fn mix(a: Rgb, b: Rgb, amount: f32) -> Rgb {
    let m = |x: u8, y: u8| (x as f32 + (y as f32 - x as f32) * amount).round().clamp(0.0, 255.0) as u8;
    rgb(m(a.r, b.r), m(a.g, b.g), m(a.b, b.b))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn follows_the_desktop() {
        assert_eq!(parse("{}").accent, rgb(0, 229, 255));
        assert_eq!(parse(r#"{"theme":"ember"}"#).accent, rgb(255, 140, 64));
        let auto = parse(
            r##"{"theme":"auto","colors":{"ink":"#09110C","raised":"#111B14","text":"#F2FCF6","muted":"#8DA897","accent":"#45F582"}}"##,
        );
        assert_eq!(auto.accent, rgb(0x45, 0xF5, 0x82));
        assert_eq!(auto.ink, rgb(0x09, 0x11, 0x0C));
        assert_eq!(parse(r#"{"terminal_opacity":0.1}"#).opacity, 0.5);
    }

    #[test]
    fn xterm_256_colours() {
        let look = Look::default();
        assert_eq!(look.indexed(16), rgb(0, 0, 0));
        assert_eq!(look.indexed(231), rgb(255, 255, 255));
        assert_eq!(look.indexed(196), rgb(255, 0, 0));
        assert_eq!(look.indexed(232), rgb(8, 8, 8));
    }
}
