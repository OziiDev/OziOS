//! Text in the session language: the same tables as the shell
//! (data/i18n/<language>.json, English source strings). English when there is
//! no table or no entry.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::OnceLock;

static TABLE: OnceLock<HashMap<String, String>> = OnceLock::new();

/// "tr_TR", "pt_BR"...; "en" when nothing is set.
pub fn locale_name() -> String {
    for key in ["LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"] {
        if let Ok(value) = std::env::var(key)
            && !value.is_empty()
            && value != "C"
            && value != "POSIX"
            && !value.starts_with("C.")
        {
            let first = value.split(':').next().unwrap_or("");
            return first.split(['.', '@']).next().unwrap_or("en").to_string();
        }
    }
    "en".into()
}

fn data_dirs() -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    if let Some(dir) = std::env::var_os("OZIOS_DATA") {
        dirs.push(PathBuf::from(dir));
    }
    // A checkout: oziwm/target/<profile>/oziwm -> data/
    if let Ok(exe) = std::env::current_exe()
        && let Some(root) = exe.ancestors().nth(4)
    {
        dirs.push(root.join("data"));
    }
    dirs.push(PathBuf::from("/usr/share/ozios/data"));
    dirs
}

fn load() -> HashMap<String, String> {
    let full = locale_name();
    let short = full.split('_').next().unwrap_or("en").to_lowercase();
    if short == "en" {
        return HashMap::new();
    }
    for dir in data_dirs() {
        for name in [full.as_str(), short.as_str()] {
            if let Ok(text) = std::fs::read_to_string(dir.join("i18n").join(format!("{name}.json")))
                && let Ok(table) = serde_json::from_str::<HashMap<String, String>>(&text)
            {
                return table;
            }
        }
    }
    HashMap::new()
}

pub fn tr(text: &str) -> String {
    TABLE.get_or_init(load).get(text).cloned().unwrap_or_else(|| text.to_string())
}

/// tr() with `{name}` fields filled in.
pub fn trf(text: &str, values: &[(&str, &str)]) -> String {
    let mut out = tr(text);
    for (name, value) in values {
        out = out.replace(&format!("{{{name}}}"), value);
    }
    out
}
