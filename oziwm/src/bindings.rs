//! Keyboard shortcuts. Pure: tested without a compositor.

use smithay::input::keyboard::Keysym;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Action {
    Spawn(Vec<String>),
    CloseFocused,
    CycleFocus,
    Quit,
    /// Ctrl+Alt+F1..F12: go to another console.
    SwitchVt(i32),
    ToggleLauncher,
    TogglePanel,
    /// Super+V: the clipboard history.
    ToggleClipboard,
    /// Alt+Tab / Super+Tab (back with Shift), and letting go of the modifier.
    SwitchStep { back: bool },
    SwitchCancel,
    Snap(crate::snap::Snap),
    /// Super+Down: give a snapped or maximized window its size back, or minimize.
    Shrink,
    ShowDesktop,
    /// Super+Shift+S: pick a part of the screen to save.
    ScreenshotArea,
    /// 0-based workspace.
    Workspace(usize),
    MoveToWorkspace(usize),
    ToggleTiling,
    ToggleFloating,
    Lock,
    /// A key typed on the lock screen.
    LockKey(Keysym, Option<char>),
    Screenshot,
    /// A hardware key ozi-shell handles (sound, brightness, media, radios).
    Key(&'static str),
}

/// Keys that work the same with any modifiers: consoles and the laptop's
/// special keys. `sym` is the key as typed (not the Latin-layout one).
pub fn special_key(sym: Keysym) -> Option<Action> {
    let raw = sym.raw();
    if (Keysym::XF86_Switch_VT_1.raw()..=Keysym::XF86_Switch_VT_12.raw()).contains(&raw) {
        return Some(Action::SwitchVt((raw - Keysym::XF86_Switch_VT_1.raw()) as i32 + 1));
    }
    let name = match sym {
        Keysym::XF86_AudioRaiseVolume => "volume-up",
        Keysym::XF86_AudioLowerVolume => "volume-down",
        Keysym::XF86_AudioMute => "mute",
        Keysym::XF86_AudioMicMute => "mic-mute",
        Keysym::XF86_MonBrightnessUp => "brightness-up",
        Keysym::XF86_MonBrightnessDown => "brightness-down",
        Keysym::XF86_AudioPlay | Keysym::XF86_AudioPause => "play-pause",
        Keysym::XF86_AudioNext => "next",
        Keysym::XF86_AudioPrev => "previous",
        Keysym::XF86_WLAN | Keysym::XF86_RFKill => "airplane",
        _ => return None,
    };
    Some(Action::Key(name))
}

/// The modifiers that matter for shortcuts.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Mods {
    pub logo: bool,
    pub alt: bool,
    pub ctrl: bool,
    pub shift: bool,
}

pub fn terminal() -> Vec<String> {
    match std::env::var("OZIWM_TERMINAL") {
        Ok(cmd) if !cmd.trim().is_empty() => cmd.split_whitespace().map(String::from).collect(),
        _ => vec![if on_path("ozi-terminal") { "ozi-terminal" } else { "konsole" }.into()],
    }
}

fn on_path(program: &str) -> bool {
    std::env::var_os("PATH")
        .is_some_and(|paths| std::env::split_paths(&paths).any(|dir| dir.join(program).is_file()))
}

/// `sym` is the layout's Latin key (so Q/F Turkish layouts give the same letter).
/// Inside a nested window the host desktop keeps Super for itself, so Alt is the
/// main modifier there.
pub fn action_for(mods: Mods, sym: Keysym, nested: bool) -> Option<Action> {
    let raw = sym.raw();
    if (Keysym::XF86_Switch_VT_1.raw()..=Keysym::XF86_Switch_VT_12.raw()).contains(&raw) {
        return Some(Action::SwitchVt((raw - Keysym::XF86_Switch_VT_1.raw()) as i32 + 1));
    }
    if sym == Keysym::Print && !mods.alt && !mods.ctrl {
        return Some(Action::Screenshot);
    }
    // Ctrl+Shift+Esc: the task manager, as on Windows.
    if mods.ctrl && mods.shift && !mods.alt && !mods.logo && sym == Keysym::Escape {
        return Some(Action::Spawn(vec!["plasma-systemmonitor".into()]));
    }
    let main = if nested { mods.alt && !mods.logo } else { mods.logo };
    if !main || mods.ctrl {
        return None;
    }
    let action = match (mods.shift, sym) {
        (false, Keysym::Return) => Action::Spawn(terminal()),
        (false, Keysym::e) => Action::Spawn(vec!["dolphin".into()]),
        (false, Keysym::q) => Action::CloseFocused,
        (false, Keysym::space) | (false, Keysym::a) => Action::ToggleLauncher,
        (false, Keysym::t) => Action::ToggleTiling,
        (false, Keysym::l) => Action::Lock,
        (false, Keysym::s) => Action::TogglePanel,
        (false, Keysym::v) => Action::ToggleClipboard,
        (false, Keysym::d) => Action::ShowDesktop,
        (false, Keysym::Left) => Action::Snap(crate::snap::Snap::Left),
        (false, Keysym::Right) => Action::Snap(crate::snap::Snap::Right),
        (false, Keysym::Up) => Action::Snap(crate::snap::Snap::Full),
        (false, Keysym::Down) => Action::Shrink,
        (true, Keysym::s) => Action::ScreenshotArea,
        (false, Keysym::period) => Action::Spawn(vec!["plasma-emojier".into()]),
        (false, Keysym::f) => Action::ToggleFloating,
        (shift, k) if (Keysym::_1.raw()..=Keysym::_4.raw()).contains(&k.raw()) => {
            let n = (k.raw() - Keysym::_1.raw()) as usize;
            if shift { Action::MoveToWorkspace(n) } else { Action::Workspace(n) }
        }
        (true, Keysym::Escape) => Action::Quit,
        _ => return None,
    };
    Some(action)
}

#[cfg(test)]
mod tests {
    use super::*;

    const SUPER: Mods = Mods { logo: true, alt: false, ctrl: false, shift: false };
    const ALT: Mods = Mods { logo: false, alt: true, ctrl: false, shift: false };

    #[test]
    fn super_on_real_hardware() {
        assert_eq!(action_for(SUPER, Keysym::q, false), Some(Action::CloseFocused));
        assert_eq!(action_for(ALT, Keysym::q, false), None);
    }

    #[test]
    fn alt_when_nested() {
        assert_eq!(action_for(ALT, Keysym::q, true), Some(Action::CloseFocused));
        assert_eq!(action_for(SUPER, Keysym::q, true), None);
    }

    #[test]
    fn quit_needs_shift() {
        assert_eq!(action_for(SUPER, Keysym::Escape, false), None);
        let mods = Mods { shift: true, ..SUPER };
        assert_eq!(action_for(mods, Keysym::Escape, false), Some(Action::Quit));
    }

    #[test]
    fn ctrl_combinations_go_to_the_program() {
        let mods = Mods { ctrl: true, ..SUPER };
        assert_eq!(action_for(mods, Keysym::Return, false), None);
    }

    #[test]
    fn console_switch_keys() {
        assert_eq!(action_for(Mods::default(), Keysym::XF86_Switch_VT_3, false), Some(Action::SwitchVt(3)));
        assert_eq!(action_for(Mods::default(), Keysym::XF86_Switch_VT_12, false), Some(Action::SwitchVt(12)));
    }

    #[test]
    fn workspaces_and_tiling() {
        assert_eq!(action_for(SUPER, Keysym::_3, false), Some(Action::Workspace(2)));
        let shifted = Mods { shift: true, ..SUPER };
        assert_eq!(action_for(shifted, Keysym::_1, false), Some(Action::MoveToWorkspace(0)));
        assert_eq!(action_for(SUPER, Keysym::_5, false), None);
        assert_eq!(action_for(SUPER, Keysym::t, false), Some(Action::ToggleTiling));
    }

    #[test]
    fn laptop_keys() {
        assert_eq!(special_key(Keysym::XF86_AudioRaiseVolume), Some(Action::Key("volume-up")));
        assert_eq!(special_key(Keysym::XF86_MonBrightnessDown), Some(Action::Key("brightness-down")));
        assert_eq!(special_key(Keysym::XF86_Switch_VT_2), Some(Action::SwitchVt(2)));
        assert_eq!(special_key(Keysym::a), None);
    }

    #[test]
    fn plain_keys_are_never_taken() {
        assert_eq!(action_for(Mods::default(), Keysym::q, false), None);
    }
}
