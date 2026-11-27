//! Box drawing, block elements, braille and the powerline arrows, drawn by the
//! terminal itself to fill the cell exactly. From a font they rarely line up:
//! the font's cell is not ours, so frames in htop, mc or a prompt show gaps.

use crate::font::Glyph;

/// Arms of the box-drawing characters U+2500..U+257F, four digits each:
/// up, right, down, left; 0 none, 1 light, 2 heavy, 3 double. "r" after the
/// digits marks a rounded corner, "x" a character drawn some other way.
const BOX: [&str; 128] = [
    "0101", "0202", "1010", "2020", "0101", "0202", "1010", "2020", // 2500
    "0101", "0202", "1010", "2020", "0110", "0210", "0120", "0220", // 2508
    "0011", "0012", "0021", "0022", "1100", "1200", "2100", "2200", // 2510
    "1001", "1002", "2001", "2002", "1110", "1210", "2110", "1120", // 2518
    "2120", "2210", "1220", "2220", "1011", "1012", "2011", "1021", // 2520
    "2021", "2012", "1022", "2022", "0111", "0112", "0211", "0212", // 2528
    "0121", "0122", "0221", "0222", "1101", "1102", "1201", "1202", // 2530
    "2101", "2102", "2201", "2202", "1111", "1112", "1211", "1212", // 2538
    "2111", "1121", "2121", "2112", "2211", "1122", "1221", "2212", // 2540
    "1222", "2122", "2221", "2222", "0101", "0202", "1010", "2020", // 2548
    "0303", "3030", "0310", "0130", "0330", "0013", "0031", "0033", // 2550
    "1300", "3100", "3300", "1003", "3001", "3003", "1310", "3130", // 2558
    "3330", "1013", "3031", "3033", "0313", "0131", "0333", "1303", // 2560
    "3101", "3303", "1313", "3131", "3333", "0110r", "0011r", "1001r", // 2568
    "1100r", "x", "x", "x", "0001", "1000", "0100", "0010", // 2570
    "0002", "2000", "0200", "0020", "0201", "1020", "0102", "2010", // 2578
];

struct Cell {
    w: usize,
    h: usize,
    cov: Vec<u8>,
}

impl Cell {
    fn new(w: usize, h: usize) -> Cell {
        Cell { w, h, cov: vec![0; w * h] }
    }

    /// A filled rectangle in whole pixels, clipped to the cell.
    fn rect(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, value: u8) {
        let (x0, x1) = (x0.clamp(0, self.w as i32) as usize, x1.clamp(0, self.w as i32) as usize);
        let (y0, y1) = (y0.clamp(0, self.h as i32) as usize, y1.clamp(0, self.h as i32) as usize);
        for y in y0..y1 {
            for x in x0..x1 {
                let c = &mut self.cov[y * self.w + x];
                *c = (*c).max(value);
            }
        }
    }

    /// Any shape given by a test on a point (in pixels), smoothed by 4×4 samples.
    fn shape(&mut self, inside: impl Fn(f32, f32) -> bool) {
        for y in 0..self.h {
            for x in 0..self.w {
                let mut hits = 0u32;
                for sy in 0..4 {
                    for sx in 0..4 {
                        if inside(x as f32 + (sx as f32 + 0.5) / 4.0, y as f32 + (sy as f32 + 0.5) / 4.0) {
                            hits += 1;
                        }
                    }
                }
                let c = &mut self.cov[y * self.w + x];
                *c = (*c).max((hits * 255 / 16) as u8);
            }
        }
    }

    fn glyph(self, baseline: i32) -> Glyph {
        Glyph { left: 0, top: baseline, width: self.w, height: self.h, coverage: self.cov, rgba: None }
    }
}

/// The character drawn to fill a cell of `w`×`h` pixels, when it is one we draw.
pub fn glyph(c: char, w: usize, h: usize, baseline: i32) -> Option<Glyph> {
    let code = c as u32;
    let mut cell = Cell::new(w, h);
    let (wi, hi) = (w as i32, h as i32);
    let light = ((w as f32 / 8.0).round() as i32).max(1);
    let heavy = (light * 2).max(2);
    match code {
        0x2500..=0x257F => {
            let spec = BOX[(code - 0x2500) as usize];
            if spec == "x" {
                // The diagonals ╱ ╲ ╳.
                let (fw, fh) = (w as f32, h as f32);
                let half = light as f32 * 0.6;
                let up = move |x: f32, y: f32| ((x / fw) - (1.0 - y / fh)).abs() * fw.min(fh) < half;
                let down = move |x: f32, y: f32| ((x / fw) - (y / fh)).abs() * fw.min(fh) < half;
                match code {
                    0x2571 => cell.shape(up),
                    0x2572 => cell.shape(down),
                    _ => cell.shape(move |x, y| up(x, y) || down(x, y)),
                }
                return Some(cell.glyph(baseline));
            }
            let arms: Vec<u8> = spec.bytes().take(4).map(|b| b - b'0').collect();
            let rounded = spec.ends_with('r');
            let (cx, cy) = (wi / 2, hi / 2);
            if rounded {
                // A quarter circle from the middle of one edge to the middle of the other.
                let r = (w.min(h) as f32) / 2.0;
                let (up, right) = (arms[0] > 0, arms[1] > 0);
                let ox = if right { cx as f32 + r } else { cx as f32 - r };
                let oy = if up { cy as f32 - r } else { cy as f32 + r };
                let t = light as f32 / 2.0;
                cell.shape(move |x, y| {
                    let in_quarter = (if right { x <= ox } else { x >= ox }) && (if up { y >= oy } else { y <= oy });
                    let d = ((x - ox).powi(2) + (y - oy).powi(2)).sqrt();
                    in_quarter && (d - (r - 0.5)).abs() <= t
                });
                // Straight parts where the cell is longer than it is wide.
                let half = light / 2;
                if up {
                    cell.rect(cx - half, 0, cx - half + light, (oy - 0.0) as i32 + 1, 255);
                } else {
                    cell.rect(cx - half, oy as i32, cx - half + light, hi, 255);
                }
                return Some(cell.glyph(baseline));
            }
            let thick = |kind: u8| if kind == 2 { heavy } else { light };
            // A double line is two light ones; their offsets from the middle line.
            let apart = light * 2;
            let offsets = |kind: u8| -> [i32; 2] { if kind == 3 { [-(apart + 1) / 2, apart / 2] } else { [0, 0] } };
            // Where an arm starts, seen from the middle: one line of it at offset `o`
            // (across the arm), with the arms `before`/`after` on either side of it
            // across its direction. Returns (low, high) ends of the inner part.
            let reach = |o: i32, before: u8, after: u8, c: i32| -> (i32, i32) {
                let side = if o < 0 { before } else if o > 0 { after } else { 0 };
                let across = before.max(after);
                match (side, across) {
                    // Meets the near line of a double arm on its own side: a corner.
                    (3, _) => {
                        let [lo, hi] = offsets(3);
                        (c - light / 2 + hi, c - light / 2 + lo + light)
                    }
                    // Meets a single arm on its own side: stops at it.
                    (1 | 2, _) => {
                        let t = thick(side);
                        (c - t / 2, c - t / 2 + t)
                    }
                    // Nothing on its side: runs to the far edge of what crosses it.
                    (_, 0) => (c - light / 2, c - light / 2 + light),
                    (_, k) => {
                        let t = thick(k);
                        let [lo, hi] = offsets(k);
                        (c - t / 2 + lo, c - t / 2 + hi + t)
                    }
                }
            };
            let (up, right, down, left) = (arms[0], arms[1], arms[2], arms[3]);
            let hi_cell = hi;
            for (kind, positive) in [(up, false), (down, true)] {
                if kind == 0 {
                    continue;
                }
                let t = thick(kind);
                for o in offsets(kind) {
                    let x0 = cx - t / 2 + o;
                    let (lo, hi) = reach(o, left, right, cy);
                    if positive {
                        cell.rect(x0, lo, x0 + t, hi_cell, 255);
                    } else {
                        cell.rect(x0, 0, x0 + t, hi, 255);
                    }
                }
            }
            for (kind, positive) in [(right, true), (left, false)] {
                if kind == 0 {
                    continue;
                }
                let t = thick(kind);
                for o in offsets(kind) {
                    let y0 = cy - t / 2 + o;
                    let (lo, hi) = reach(o, up, down, cx);
                    if positive {
                        cell.rect(lo, y0, wi, y0 + t, 255);
                    } else {
                        cell.rect(0, y0, hi, y0 + t, 255);
                    }
                }
            }
        }
        0x2580..=0x259F => {
            let (hw, hh) = (wi / 2, hi / 2);
            let eighth_h = |n: i32| (hi * n + 4) / 8;
            let eighth_w = |n: i32| (wi * n + 4) / 8;
            match code {
                0x2580 => cell.rect(0, 0, wi, hh, 255),
                0x2581..=0x2588 => {
                    let n = (code - 0x2580) as i32;
                    cell.rect(0, hi - eighth_h(n), wi, hi, 255)
                }
                0x2589..=0x258F => {
                    let n = 8 - (code - 0x2588) as i32;
                    cell.rect(0, 0, eighth_w(n), hi, 255)
                }
                0x2590 => cell.rect(hw, 0, wi, hi, 255),
                0x2591..=0x2593 => {
                    let v = [64u8, 128, 192][(code - 0x2591) as usize];
                    cell.rect(0, 0, wi, hi, v)
                }
                0x2594 => cell.rect(0, 0, wi, eighth_h(1), 255),
                0x2595 => cell.rect(wi - eighth_w(1), 0, wi, hi, 255),
                _ => {
                    // Quadrants: upper left, upper right, lower left, lower right.
                    let q: [bool; 4] = match code {
                        0x2596 => [false, false, true, false],
                        0x2597 => [false, false, false, true],
                        0x2598 => [true, false, false, false],
                        0x2599 => [true, false, true, true],
                        0x259A => [true, false, false, true],
                        0x259B => [true, true, true, false],
                        0x259C => [true, true, false, true],
                        0x259D => [false, true, false, false],
                        0x259E => [false, true, true, false],
                        _ => [false, true, true, true],
                    };
                    let boxes = [(0, 0, hw, hh), (hw, 0, wi, hh), (0, hh, hw, hi), (hw, hh, wi, hi)];
                    for (on, (x0, y0, x1, y1)) in q.iter().zip(boxes) {
                        if *on {
                            cell.rect(x0, y0, x1, y1, 255);
                        }
                    }
                }
            }
        }
        0x2800..=0x28FF => {
            let bits = code - 0x2800;
            // Dot n's column and row.
            let dots = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)];
            let (fw, fh) = (w as f32, h as f32);
            let r = (fw / 4.0).min(fh / 8.0) * 0.8;
            let centers: Vec<(f32, f32)> = dots
                .iter()
                .enumerate()
                .filter(|(i, _)| bits & (1 << i) != 0)
                .map(|(_, &(col, row))| (fw * (0.25 + 0.5 * col as f32), fh * (0.125 + 0.25 * row as f32)))
                .collect();
            cell.shape(move |x, y| centers.iter().any(|(cx, cy)| (x - cx).powi(2) + (y - cy).powi(2) <= r * r));
        }
        0xE0B0..=0xE0B3 | 0xE0B4..=0xE0B7 => {
            let (fw, fh) = (w as f32, h as f32);
            let left = matches!(code, 0xE0B2 | 0xE0B3 | 0xE0B6 | 0xE0B7);
            let solid = matches!(code, 0xE0B0 | 0xE0B2 | 0xE0B4 | 0xE0B6);
            let round = code >= 0xE0B4;
            let t = light as f32;
            // x measured from the flat side.
            let fx = move |x: f32| if left { fw - x } else { x };
            if round {
                let (ry, rx) = (fh / 2.0, fw);
                cell.shape(move |x, y| {
                    let d = (fx(x) / rx).powi(2) + ((y - ry) / ry).powi(2);
                    if solid { d <= 1.0 } else { d <= 1.0 && d >= (1.0 - 2.0 * t / rx.min(ry)).powi(2) }
                });
            } else {
                cell.shape(move |x, y| {
                    let edge = fw * (1.0 - (2.0 * y / fh - 1.0).abs());
                    let x = fx(x);
                    if solid { x <= edge } else { (x - edge).abs() <= t * 0.9 }
                });
            }
        }
        _ => return None,
    }
    Some(cell.glyph(baseline))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn filled(g: &Glyph, x: usize, y: usize) -> bool {
        g.coverage[y * g.width + x] > 128
    }

    #[test]
    fn lines_reach_the_edges() {
        let g = glyph('┼', 9, 18, 14).unwrap();
        assert!(filled(&g, 4, 0) && filled(&g, 4, 17), "vertical arm touches top and bottom");
        assert!(filled(&g, 0, 9) && filled(&g, 8, 9), "horizontal arm touches both sides");
        let g = glyph('─', 9, 18, 14).unwrap();
        assert!(!filled(&g, 4, 0));
    }

    #[test]
    fn blocks_and_braille() {
        let g = glyph('▄', 8, 16, 12).unwrap();
        assert!(!filled(&g, 3, 2) && filled(&g, 3, 12));
        let g = glyph('█', 8, 16, 12).unwrap();
        assert!(g.coverage.iter().all(|&c| c == 255));
        let g = glyph('⠁', 8, 16, 12).unwrap();
        assert!(filled(&g, 2, 2) && !filled(&g, 6, 14));
        assert!(glyph('a', 8, 16, 12).is_none());
    }

    #[test]
    fn every_box_character_draws() {
        for code in 0x2500..=0x257F {
            let g = glyph(char::from_u32(code).unwrap(), 9, 18, 14).unwrap();
            assert!(g.coverage.iter().any(|&c| c > 0), "U+{code:X} is empty");
        }
    }
}

