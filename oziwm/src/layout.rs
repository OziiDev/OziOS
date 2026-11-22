//! Tiling: the free area halved again and again in a spiral. Pure: tested
//! without a compositor. Same rules as the 0.3 KWin script: 12 px from the
//! screen edges, 10 px between windows, each new window takes half of the
//! last one's place.

use crate::deco::Rect;

pub const OUTER_GAP: i32 = 12;
pub const INNER_GAP: i32 = 10;

/// Rectangles for `n` windows in `area`, in the order the windows were opened.
pub fn dwindle(area: Rect, n: usize) -> Vec<Rect> {
    if n == 0 {
        return Vec::new();
    }
    let mut free = Rect::new(
        area.x + OUTER_GAP,
        area.y + OUTER_GAP,
        (area.w - 2 * OUTER_GAP).max(1),
        (area.h - 2 * OUTER_GAP).max(1),
    );
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        if i == n - 1 {
            out.push(free);
            break;
        }
        // Split the longer side, so windows stay close to square.
        if free.w >= free.h {
            let left = (free.w - INNER_GAP) / 2;
            out.push(Rect::new(free.x, free.y, left, free.h));
            free = Rect::new(free.x + left + INNER_GAP, free.y, free.w - left - INNER_GAP, free.h);
        } else {
            let top = (free.h - INNER_GAP) / 2;
            out.push(Rect::new(free.x, free.y, free.w, top));
            free = Rect::new(free.x, free.y + top + INNER_GAP, free.w, free.h - top - INNER_GAP);
        }
    }
    out
}

/// Position `from` moved `t` (0..1) of the way to `to`.
pub fn lerp(from: Rect, to: Rect, t: f64) -> (f64, f64, f64, f64) {
    let l = |a: i32, b: i32| a as f64 + (b - a) as f64 * t;
    (l(from.x, to.x), l(from.y, to.y), l(from.w, to.w), l(from.h, to.h))
}

#[cfg(test)]
mod tests {
    use super::*;

    const SCREEN: Rect = Rect::new(0, 0, 1920, 1080);

    #[test]
    fn one_window_fills_the_area_minus_the_edge_gap() {
        assert_eq!(dwindle(SCREEN, 1), vec![Rect::new(12, 12, 1896, 1056)]);
    }

    #[test]
    fn two_windows_side_by_side() {
        let r = dwindle(SCREEN, 2);
        assert_eq!(r[0], Rect::new(12, 12, 943, 1056));
        assert_eq!(r[1].x, 12 + 943 + 10);
        assert_eq!(r[1].x + r[1].w, 1920 - 12);
    }

    #[test]
    fn third_window_halves_the_second_vertically() {
        let r = dwindle(SCREEN, 3);
        assert_eq!(r[1].x, r[2].x);
        assert_eq!(r[1].w, r[2].w);
        assert_eq!(r[2].y, r[1].y + r[1].h + 10);
        assert_eq!(r[2].y + r[2].h, 1080 - 12);
    }

    #[test]
    fn nothing_overlaps_and_nothing_is_lost() {
        for n in 1..9 {
            let r = dwindle(SCREEN, n);
            assert_eq!(r.len(), n);
            for (i, a) in r.iter().enumerate() {
                assert!(a.w > 0 && a.h > 0);
                for b in &r[i + 1..] {
                    let apart = a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y;
                    assert!(apart, "{a:?} overlaps {b:?} with {n} windows");
                }
            }
        }
    }

    #[test]
    fn lerp_ends() {
        let a = Rect::new(0, 0, 100, 100);
        let b = Rect::new(100, 50, 200, 300);
        assert_eq!(lerp(a, b, 0.0), (0.0, 0.0, 100.0, 100.0));
        assert_eq!(lerp(a, b, 1.0), (100.0, 50.0, 200.0, 300.0));
    }
}
