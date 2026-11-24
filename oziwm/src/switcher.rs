//! Alt+Tab: hold Alt (or Super), press Tab to walk through the windows, most
//! recently used first; letting go of the modifier switches. ozi-shell draws
//! the list from the "switcher" events.

use serde_json::json;

use crate::{ipc, state::window_id, OziWm};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Switcher {
    pub ids: Vec<u64>,
    pub index: usize,
}

/// The windows in the order Alt+Tab offers them: most recently focused first,
/// then any the history does not know yet.
pub fn order(history: &[u64], all: &[u64]) -> Vec<u64> {
    let mut ids: Vec<u64> = history.iter().copied().filter(|id| all.contains(id)).collect();
    for id in all {
        if !ids.contains(id) {
            ids.push(*id);
        }
    }
    ids
}

impl OziWm {
    /// Every window, on any desktop or minimized.
    pub fn all_window_ids(&self) -> Vec<u64> {
        self.space
            .elements()
            .rev()
            .chain(self.hidden.iter().map(|(w, _)| w))
            .chain(self.minimized.iter())
            .map(window_id)
            .collect()
    }

    pub fn note_focus(&mut self, id: u64) {
        self.focus_history.retain(|i| *i != id);
        self.focus_history.insert(0, id);
        self.focus_history.truncate(64);
    }

    /// Tab (or Shift+Tab) while the modifier is held.
    pub fn switcher_step(&mut self, back: bool) {
        let switcher = match self.switcher.take() {
            Some(mut s) => {
                let n = s.ids.len().max(1);
                s.index = if back { (s.index + n - 1) % n } else { (s.index + 1) % n };
                s
            }
            None => {
                let ids = order(&self.focus_history, &self.all_window_ids());
                if ids.is_empty() {
                    return;
                }
                // The window in front is first; Tab goes to the one before it.
                let index = if ids.len() > 1 { if back { ids.len() - 1 } else { 1 } } else { 0 };
                Switcher { ids, index }
            }
        };
        ipc::emit(self, "shell", json!({ "event": "switcher", "ids": switcher.ids, "index": switcher.index }));
        self.switcher = Some(switcher);
    }

    /// The modifier was let go: switch to the chosen window.
    pub fn switcher_finish(&mut self) {
        let Some(switcher) = self.switcher.take() else {
            return;
        };
        ipc::emit(self, "shell", json!({ "event": "switcher-end" }));
        if let Some(window) = switcher.ids.get(switcher.index).and_then(|id| self.window_by_id(*id)) {
            self.focus_window(Some(window));
        }
    }

    pub fn switcher_cancel(&mut self) {
        if self.switcher.take().is_some() {
            ipc::emit(self, "shell", json!({ "event": "switcher-end" }));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn most_recent_first_then_the_rest() {
        assert_eq!(order(&[3, 1], &[1, 2, 3]), vec![3, 1, 2]);
        // Closed windows drop out of the history.
        assert_eq!(order(&[9, 2], &[1, 2]), vec![2, 1]);
        assert_eq!(order(&[], &[]), Vec::<u64>::new());
    }
}
