//! The Education edition's restricted mode (Kısıtlı): a board that has not
//! been unlocked by the teacher does not start the terminal, settings, the
//! store and the like, whichever way it is asked (a shortcut, IPC). The same
//! list is in python/ozipkg/mode.py, which the shell and the apps use.

use std::path::Path;

const BLOCKED: &[&str] = &[
    "ozi-terminal", "konsole", "xterm", "alacritty", "kitty", "foot", "gnome-terminal", "kgx", "xfce4-terminal",
    "ozi-store", "ozi-look", "systemsettings", "ozi-welcome", "calamares", "pamac-manager", "octopi", "gparted",
    "btrfs-assistant", "partitionmanager", "ozi", "pkexec", "sudo", "su",
];

fn read(path: &str) -> String {
    std::fs::read_to_string(path).map(|s| s.trim().to_string()).unwrap_or_default()
}

/// True on an Education board that is in restricted mode.
pub fn restricted() -> bool {
    read("/usr/share/ozios/edition") == "edu" && read("/run/ozios/mode") != "yetkili"
}

/// The program a command line starts, by file name (through `sh -c` or `env` too).
fn program(argv: &[String]) -> String {
    let base = |s: &str| Path::new(s).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let Some(first) = argv.first() else { return String::new() };
    match base(first).as_str() {
        "sh" | "bash" if argv.len() > 2 && argv[1] == "-c" => {
            argv[2].split_whitespace().next().map(base).unwrap_or_default()
        }
        "env" => argv.iter().skip(1).find(|a| !a.contains('=') && !a.starts_with('-')).map(|a| base(a)).unwrap_or_default(),
        name => name.to_string(),
    }
}

pub fn blocked_program(argv: &[String]) -> bool {
    BLOCKED.contains(&program(argv).as_str())
}

/// May this command start now?
pub fn allowed(argv: &[String]) -> bool {
    !blocked_program(argv) || !restricted()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(args: &[&str]) -> Vec<String> {
        args.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn finds_the_program_behind_shells() {
        assert!(blocked_program(&v(&["/usr/bin/ozi-terminal"])));
        assert!(blocked_program(&v(&["sh", "-c", "konsole -e htop"])));
        assert!(blocked_program(&v(&["env", "FOO=1", "ozi-store"])));
        assert!(!blocked_program(&v(&["firefox"])));
        assert!(!blocked_program(&v(&["sh", "-c", "/usr/bin/ozi-shell"])));
    }
}
