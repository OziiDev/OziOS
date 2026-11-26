//! Colours and look settings, shared with `ozi theme` / `ozi look`.
//!
//! Read from `~/.config/ozios/desktop.json`; anything missing keeps its default:
//!
//! ```json
//! {"theme": "aurora", "glow": 1.0, "animation_speed": 1.0, "corner_radius": 12}
//! ```

use std::path::PathBuf;

use serde_json::Value;

pub type Rgb = [f32; 3];

const fn rgb(r: u8, g: u8, b: u8) -> Rgb {
    [r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0]
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Theme {
    pub id: &'static str,
    pub ink: Rgb,
    pub raised: Rgb,
    pub text: Rgb,
    pub muted: Rgb,
    pub accent: Rgb,
    /// The second glow colour, leaning toward violet like the rest of OziOS.
    pub accent2: Rgb,
}

/// Same palette as python/ozipkg/themes.py.
pub const THEMES: [Theme; 6] = [
    Theme { id: "cyan", ink: rgb(8, 11, 16), raised: rgb(14, 19, 27), text: rgb(244, 252, 255), muted: rgb(128, 150, 160), accent: rgb(0, 229, 255), accent2: rgb(124, 92, 255) },
    Theme { id: "aurora", ink: rgb(11, 8, 20), raised: rgb(19, 15, 33), text: rgb(246, 243, 255), muted: rgb(150, 140, 178), accent: rgb(176, 140, 255), accent2: rgb(255, 92, 200) },
    Theme { id: "ember", ink: rgb(16, 10, 8), raised: rgb(27, 18, 14), text: rgb(255, 247, 240), muted: rgb(172, 146, 132), accent: rgb(255, 140, 64), accent2: rgb(232, 64, 140) },
    Theme { id: "mint", ink: rgb(7, 14, 12), raised: rgb(12, 23, 20), text: rgb(240, 255, 250), muted: rgb(130, 166, 153), accent: rgb(60, 230, 160), accent2: rgb(60, 140, 255) },
    Theme { id: "rose", ink: rgb(16, 8, 11), raised: rgb(27, 14, 19), text: rgb(255, 242, 246), muted: rgb(176, 136, 151), accent: rgb(255, 94, 140), accent2: rgb(160, 92, 255) },
    Theme { id: "frost", ink: rgb(242, 246, 249), raised: rgb(232, 238, 243), text: rgb(12, 19, 25), muted: rgb(92, 111, 122), accent: rgb(0, 145, 172), accent2: rgb(110, 80, 230) },
];

#[derive(Debug, Clone, PartialEq)]
pub struct Look {
    pub theme: Theme,
    /// How much of the accent the focused window's border takes: 0 none (the
    /// default), 1 most. The old 0..2 "glow" setting maps onto it.
    pub glow: f32,
    /// 0 turns animations off, 1 is normal, 2 is twice as fast.
    pub animation_speed: f64,
    pub corner_radius: f32,
    /// Lock after this many minutes without input; 0 never.
    pub lock_after_minutes: u32,
}

impl Default for Look {
    fn default() -> Self {
        Look {
            theme: THEMES[0],
            glow: 0.0,
            animation_speed: 1.0,
            corner_radius: crate::deco::RADIUS,
            lock_after_minutes: 10,
        }
    }
}

/// "#RRGGBB" -> colour.
fn parse_hex(text: &str) -> Option<Rgb> {
    let hex = text.strip_prefix('#')?;
    if hex.len() != 6 || !hex.is_ascii() {
        return None;
    }
    let byte = |i: usize| u8::from_str_radix(&hex[i..i + 2], 16).ok().map(|b| b as f32 / 255.0);
    Some([byte(0)?, byte(2)?, byte(4)?])
}

/// The "auto" theme: colours the shell worked out from the wallpaper and
/// wrote under "colors" (python/ozipkg/wallcolors.py).
fn from_wallpaper(colors: &Value) -> Option<Theme> {
    let get = |key: &str| colors.get(key).and_then(Value::as_str).and_then(parse_hex);
    Some(Theme {
        id: "auto",
        ink: get("ink")?,
        raised: get("raised")?,
        text: get("text")?,
        muted: get("muted")?,
        accent: get("accent")?,
        accent2: get("accent2")?,
    })
}

pub fn theme_by_id(id: &str) -> Option<Theme> {
    THEMES.iter().copied().find(|t| t.id == id)
}

pub fn config_path() -> PathBuf {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config")))
        .unwrap_or_else(|| PathBuf::from("/tmp"));
    base.join("ozios/desktop.json")
}

pub fn parse(text: &str) -> Look {
    let mut look = Look::default();
    let Ok(value) = serde_json::from_str::<Value>(text) else {
        return look;
    };
    match value.get("theme").and_then(Value::as_str) {
        Some("auto") => {
            if let Some(theme) = value.get("colors").and_then(from_wallpaper) {
                look.theme = theme;
            }
        }
        Some(id) => {
            if let Some(theme) = theme_by_id(id) {
                look.theme = theme;
            }
        }
        None => {}
    }
    if let Some(glow) = value.get("glow").and_then(Value::as_f64) {
        look.glow = glow.clamp(0.0, 1.0) as f32;
    }
    if let Some(speed) = value.get("animation_speed").and_then(Value::as_f64) {
        look.animation_speed = speed.clamp(0.0, 3.0);
    }
    if let Some(radius) = value.get("corner_radius").and_then(Value::as_f64) {
        look.corner_radius = radius.clamp(0.0, 16.0) as f32;
    }
    if let Some(minutes) = value.get("lock_after_minutes").and_then(Value::as_u64) {
        look.lock_after_minutes = minutes.min(24 * 60) as u32;
    }
    look
}

pub fn load() -> Look {
    std::fs::read_to_string(config_path())
        .map(|t| parse(&t))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_when_missing_or_broken() {
        assert_eq!(parse("not json"), Look::default());
        assert_eq!(parse("{}"), Look::default());
    }

    #[test]
    fn reads_and_clamps() {
        let look = parse(r#"{"theme":"ember","glow":5,"animation_speed":0,"corner_radius":8}"#);
        assert_eq!(look.theme.id, "ember");
        assert_eq!(look.glow, 1.0);
        assert_eq!(look.animation_speed, 0.0);
        assert_eq!(look.corner_radius, 8.0);
    }

    #[test]
    fn idle_lock_minutes() {
        assert_eq!(parse("{}").lock_after_minutes, 10);
        assert_eq!(parse(r#"{"lock_after_minutes":0}"#).lock_after_minutes, 0);
        assert_eq!(parse(r#"{"lock_after_minutes":99999}"#).lock_after_minutes, 1440);
    }

    #[test]
    fn auto_theme_reads_the_wallpaper_colours() {
        let look = parse(
            r##"{"theme":"auto","colors":{"ink":"#09110C","raised":"#111B14","text":"#F2FCF6",
                "muted":"#8DA897","accent":"#35FF7B","accent2":"#35CAFF"}}"##,
        );
        assert_eq!(look.theme.id, "auto");
        assert_eq!(look.theme.accent, rgb(0x35, 0xFF, 0x7B));
        // Not worked out yet, or broken: cyan.
        assert_eq!(parse(r#"{"theme":"auto"}"#).theme.id, "cyan");
        assert_eq!(parse(r##"{"theme":"auto","colors":{"ink":"#zz"}}"##).theme.id, "cyan");
    }

    #[test]
    fn unknown_theme_keeps_cyan() {
        assert_eq!(parse(r#"{"theme":"plaid"}"#).theme.id, "cyan");
    }
}
