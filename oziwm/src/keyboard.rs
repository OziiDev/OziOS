//! Which keyboard layout to use: the one the system already has.

use smithay::input::keyboard::XkbConfig;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Layout {
    pub layout: String,
    pub variant: String,
    pub options: Option<String>,
}

impl Layout {
    pub fn to_config(&self) -> XkbConfig<'_> {
        XkbConfig {
            layout: &self.layout,
            variant: &self.variant,
            options: self.options.clone(),
            ..Default::default()
        }
    }
}

/// Order: OZIWM_XKB_* variables, the Plasma setting, systemd-localed's X11 file,
/// /etc/vconsole.conf, then US.
pub fn system_layout() -> Layout {
    if let Ok(layout) = std::env::var("OZIWM_XKB_LAYOUT") {
        return Layout {
            layout,
            variant: std::env::var("OZIWM_XKB_VARIANT").unwrap_or_default(),
            options: std::env::var("OZIWM_XKB_OPTIONS").ok(),
        };
    }
    let home_kxkbrc = std::env::var("HOME")
        .map(|h| format!("{h}/.config/kxkbrc"))
        .unwrap_or_default();
    let sources: [(&str, fn(&str) -> Option<Layout>); 3] = [
        (home_kxkbrc.as_str(), parse_kxkbrc),
        ("/etc/X11/xorg.conf.d/00-keyboard.conf", parse_xorg),
        ("/etc/vconsole.conf", parse_vconsole),
    ];
    for (path, parse) in sources {
        if let Some(layout) = std::fs::read_to_string(path).ok().as_deref().and_then(parse) {
            return layout;
        }
    }
    Layout { layout: "us".into(), variant: String::new(), options: None }
}

/// Whether Num Lock starts switched on. Plasma's setting (`[Keyboard]
/// NumLock=` in kcminputrc: 0 on, 1 off, 2 leave) is followed; without one it is
/// on, so the number pad types numbers (at a password prompt too).
pub fn numlock_at_start() -> bool {
    let path = std::env::var("HOME").map(|h| format!("{h}/.config/kcminputrc")).unwrap_or_default();
    std::fs::read_to_string(path).ok().as_deref().map(parse_numlock).unwrap_or(true)
}

pub fn parse_numlock(text: &str) -> bool {
    let mut in_keyboard = false;
    for line in text.lines().map(str::trim) {
        if line.starts_with('[') {
            in_keyboard = line == "[Keyboard]";
            continue;
        }
        if in_keyboard && let Some(("NumLock", value)) = line.split_once('=').map(|(k, v)| (k.trim(), v.trim())) {
            return value != "1";
        }
    }
    true
}

fn non_empty(s: &str) -> Option<String> {
    let s = s.trim();
    (!s.is_empty()).then(|| s.to_string())
}

/// Plasma: `[Layout]` with `LayoutList=tr,us`, `VariantList=f,`, `Options=...`.
pub fn parse_kxkbrc(text: &str) -> Option<Layout> {
    let mut in_layout = false;
    let (mut layout, mut variant, mut options) = (None, String::new(), None);
    for line in text.lines().map(str::trim) {
        if line.starts_with('[') {
            in_layout = line == "[Layout]";
            continue;
        }
        if !in_layout {
            continue;
        }
        if let Some((key, value)) = line.split_once('=') {
            match key.trim() {
                "LayoutList" => layout = non_empty(value),
                "VariantList" => variant = value.trim().to_string(),
                "Options" => options = non_empty(value),
                _ => {}
            }
        }
    }
    Some(Layout { layout: layout?, variant, options })
}

/// systemd-localed: `Option "XkbLayout" "tr"` lines.
pub fn parse_xorg(text: &str) -> Option<Layout> {
    let value = |name: &str| {
        text.lines().find_map(|line| {
            let line = line.trim();
            let rest = line.strip_prefix("Option")?.trim();
            let rest = rest.strip_prefix(&format!("\"{name}\""))?.trim();
            Some(rest.trim_matches('"').to_string())
        })
    };
    Some(Layout {
        layout: non_empty(&value("XkbLayout")?)?,
        variant: value("XkbVariant").unwrap_or_default(),
        options: value("XkbOptions").and_then(|o| non_empty(&o)),
    })
}

/// `XKBLAYOUT=tr` (written by localectl), else the console keymap name (`trq`, `trf`).
pub fn parse_vconsole(text: &str) -> Option<Layout> {
    let get = |key: &str| {
        text.lines()
            .find_map(|l| l.trim().strip_prefix(key)?.strip_prefix('='))
            .map(|v| v.trim().trim_matches('"').to_string())
    };
    if let Some(layout) = get("XKBLAYOUT").and_then(|l| non_empty(&l)) {
        return Some(Layout {
            layout,
            variant: get("XKBVARIANT").unwrap_or_default(),
            options: get("XKBOPTIONS").and_then(|o| non_empty(&o)),
        });
    }
    let (layout, variant) = match get("KEYMAP")?.as_str() {
        "trq" => ("tr", ""),
        "trf" => ("tr", "f"),
        "us" => ("us", ""),
        "de" | "de-latin1" => ("de", ""),
        _ => return None,
    };
    Some(Layout { layout: layout.into(), variant: variant.into(), options: None })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plasma_setting() {
        let text = "[General]\nfoo=1\n[Layout]\nLayoutList=tr,us\nVariantList=f,\nOptions=grp:alt_shift_toggle\n";
        let l = parse_kxkbrc(text).unwrap();
        assert_eq!(l.layout, "tr,us");
        assert_eq!(l.variant, "f,");
        assert_eq!(l.options.as_deref(), Some("grp:alt_shift_toggle"));
    }

    #[test]
    fn plasma_without_layouts_falls_through() {
        assert_eq!(parse_kxkbrc("[Layout]\nUse=false\n"), None);
    }

    #[test]
    fn numlock_setting() {
        assert!(parse_numlock(""));
        assert!(parse_numlock("[Keyboard]\nNumLock=0\n"));
        assert!(!parse_numlock("[Keyboard]\nNumLock=1\n"));
        assert!(parse_numlock("[Mouse]\nNumLock=1\n"));
    }

    #[test]
    fn localed_file() {
        let text = "Section \"InputClass\"\n        Option \"XkbLayout\" \"tr\"\n        Option \"XkbVariant\" \"\"\nEndSection\n";
        let l = parse_xorg(text).unwrap();
        assert_eq!((l.layout.as_str(), l.variant.as_str(), l.options), ("tr", "", None));
    }

    #[test]
    fn vconsole() {
        assert_eq!(parse_vconsole("KEYMAP=trq\nXKBLAYOUT=tr\n").unwrap().layout, "tr");
        let f = parse_vconsole("KEYMAP=trf\n").unwrap();
        assert_eq!((f.layout.as_str(), f.variant.as_str()), ("tr", "f"));
        assert_eq!(parse_vconsole("FONT=x\n"), None);
    }
}
