//! Where a new floating window appears. Pure: tested without a compositor.

/// Step between windows that would otherwise open on top of each other.
const CASCADE: i32 = 32;

/// Centre the window in `area` (x, y, w, h); if another window already starts
/// there, step down and right. Always keeps the top-left corner on screen.
pub fn place(area: (i32, i32, i32, i32), size: (i32, i32), taken: &[(i32, i32)]) -> (i32, i32) {
    let (ax, ay, aw, ah) = area;
    let (w, h) = (size.0.min(aw), size.1.min(ah));
    let mut x = ax + (aw - w) / 2;
    let mut y = ay + (ah - h) / 2;
    let max_x = ax + (aw - w).max(0);
    let max_y = ay + (ah - h).max(0);

    let mut tries = 0;
    while taken.contains(&(x, y)) && tries < 64 {
        x += CASCADE;
        y += CASCADE;
        if x > max_x || y > max_y {
            // Wrap to the top-left of the area and keep stepping from there.
            x = ax + CASCADE * (tries % 8);
            y = ay + CASCADE * (tries % 8);
        }
        tries += 1;
    }
    (x.clamp(ax, max_x.max(ax)), y.clamp(ay, max_y.max(ay)))
}

#[cfg(test)]
mod tests {
    use super::*;

    const AREA: (i32, i32, i32, i32) = (0, 0, 1920, 1080);

    #[test]
    fn first_window_is_centred() {
        assert_eq!(place(AREA, (800, 600), &[]), (560, 240));
    }

    #[test]
    fn second_window_steps_down_and_right() {
        assert_eq!(place(AREA, (800, 600), &[(560, 240)]), (592, 272));
    }

    #[test]
    fn huge_window_starts_at_the_corner() {
        assert_eq!(place(AREA, (4000, 3000), &[]), (0, 0));
    }

    #[test]
    fn stays_on_screen_when_crowded() {
        let taken: Vec<(i32, i32)> = (0..200).map(|i| (560 + 32 * i, 240 + 32 * i)).collect();
        let (x, y) = place(AREA, (800, 600), &taken);
        assert!((0..=1120).contains(&x) && (0..=480).contains(&y), "{x},{y}");
    }

    #[test]
    fn offset_area() {
        assert_eq!(place((100, 50, 1000, 800), (500, 400), &[]), (350, 250));
    }
}
