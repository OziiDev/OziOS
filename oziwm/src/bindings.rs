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
    /// 0-based workspace.
    Workspace(usize),
    MoveToWorkspace(usize),
    ToggleTiling,
    ToggleFloating,
    Lock,
    /// A key typed on the lock screen.
    LockKey(Keysym, Option<char>),
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
        _ => vec!["konsole".into()],
    }
}

/// `sym` is the layout's Latin key (so Q/F Turkish layouts give the same letter).
/// Inside a nested window the host desktop keeps Super for itself, so Alt is the
/// main modifier there.
pub fn action_for(mods: Mods, sym: Keysym, nested: bool) -> Option<Action> {
    let raw = sym.raw();
    if (Keysym::XF86_Switch_VT_1.raw()..=Keysym::XF86_Switch_VT_12.raw()).contains(&raw) {
        return Some(Action::SwitchVt((raw - Keysym::XF86_Switch_VT_1.raw()) as i32 + 1));
    }
    let main = if nested { mods.alt && !mods.logo } else { mods.logo };
    if !main || mods.ctrl {
        return None;
    }
    let action = match (mods.shift, sym) {
        (false, Keysym::Return) => Action::Spawn(terminal()),
        (false, Keysym::e) => Action::Spawn(vec!["dolphin".into()]),
        (false, Keysym::q) => Action::CloseFocused,
        (false, Keysym::Tab) => Action::CycleFocus,
        (false, Keysym::space) | (false, Keysym::a) => Action::ToggleLauncher,
        (false, Keysym::t) => Action::ToggleTiling,
        (false, Keysym::l) => Action::Lock,
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
    fn plain_keys_are_never_taken() {
        assert_eq!(action_for(Mods::default(), Keysym::q, false), None);
    }
}
