//! Drawing into the window's pixels (premultiplied ARGB): the see-through
//! background, the cells, the cursor, the selection and, with two tabs or
//! more, the tab bar.

use alacritty_terminal::index::Point;
use alacritty_terminal::term::cell::Flags;
use alacritty_terminal::vte::ansi::{Color, CursorShape, NamedColor, Rgb};

use crate::look::mix;
use crate::App;

struct Canvas<'a> {
    px: &'a mut [u32],
    w: usize,
    h: usize,
}

fn opaque(c: Rgb) -> u32 {
    0xFF00_0000 | (c.r as u32) << 16 | (c.g as u32) << 8 | c.b as u32
}

fn premultiplied(c: Rgb, alpha: f32) -> u32 {
    let a = (alpha.clamp(0.0, 1.0) * 255.0).round() as u32;
    let m = |v: u8| (v as u32 * a + 127) / 255;
    a << 24 | m(c.r) << 16 | m(c.g) << 8 | m(c.b)
}

impl Canvas<'_> {
    fn fill(&mut self, x: i32, y: i32, w: usize, h: usize, color: u32) {
        let x0 = x.max(0) as usize;
        let y0 = y.max(0) as usize;
        let x1 = ((x + w as i32).max(0) as usize).min(self.w);
        let y1 = ((y + h as i32).max(0) as usize).min(self.h);
        if x0 >= x1 {
            return;
        }
        for row in y0..y1 {
            self.px[row * self.w + x0..row * self.w + x1].fill(color);
        }
    }

    /// A glyph's coverage over what is there, in an opaque colour.
    fn glyph(&mut self, x: i32, y: i32, g: &crate::font::Glyph, c: Rgb, clip_right: i32) {
        if let Some(rgba) = &g.rgba {
            return self.picture(x, y, g.width, g.height, rgba, clip_right);
        }
        for gy in 0..g.height {
            let py = y + gy as i32;
            if py < 0 || py as usize >= self.h {
                continue;
            }
            for gx in 0..g.width {
                let px = x + gx as i32;
                if px < 0 || px as usize >= self.w || px >= clip_right {
                    continue;
                }
                let cov = g.coverage[gy * g.width + gx] as u32;
                if cov == 0 {
                    continue;
                }
                let i = py as usize * self.w + px as usize;
                let d = self.px[i];
                let inv = 255 - cov;
                let ch = |src: u8, shift: u32| ((src as u32 * cov + ((d >> shift) & 0xFF) * inv + 127) / 255) << shift;
                let a = ((255 * cov + (d >> 24) * inv + 127) / 255) << 24;
                self.px[i] = a | ch(c.r, 16) | ch(c.g, 8) | ch(c.b, 0);
            }
        }
    }
}

impl Canvas<'_> {
    /// A colour picture (premultiplied RGBA) over what is there.
    fn picture(&mut self, x: i32, y: i32, w: usize, h: usize, rgba: &[[u8; 4]], clip_right: i32) {
        for gy in 0..h {
            let py = y + gy as i32;
            if py < 0 || py as usize >= self.h {
                continue;
            }
            for gx in 0..w {
                let px = x + gx as i32;
                if px < 0 || px as usize >= self.w || px >= clip_right {
                    continue;
                }
                let [r, g, b, a] = rgba[gy * w + gx];
                if a == 0 {
                    continue;
                }
                let i = py as usize * self.w + px as usize;
                let d = self.px[i];
                let inv = 255 - a as u32;
                let over = |src: u8, shift: u32| ((src as u32 + (((d >> shift) & 0xFF) * inv + 127) / 255).min(255)) << shift;
                self.px[i] = over(a, 24) | over(r, 16) | over(g, 8) | over(b, 0);
            }
        }
    }
}

pub fn tab_width(window_width: usize, tabs: usize) -> usize {
    (window_width / tabs.max(1)).min(260)
}

fn draw_text(app: &mut App, canvas: &mut Canvas, mut x: i32, baseline: i32, text: &str, color: Rgb, max_x: i32) {
    let cw = app.fonts.cell_width as i32;
    let chars: Vec<char> = text.chars().collect();
    let fits = ((max_x - x) / cw).max(0) as usize;
    let shown: Vec<char> = if chars.len() > fits && fits > 1 {
        chars[..fits - 1].iter().copied().chain(std::iter::once('…')).collect()
    } else {
        chars.into_iter().take(fits).collect()
    };
    for c in shown {
        if let Some(g) = app.fonts.glyph(c, crate::font::Style { bold: false, italic: false }, 1) {
            canvas.glyph(x + g.left, baseline - g.top, g, color, max_x);
        }
        x += cw;
    }
}

pub fn draw(app: &mut App, buffer: &mut [u32], w: usize, h: usize) {
    let look = app.look.clone();
    let mut canvas = Canvas { px: buffer, w, h };
    canvas.px.fill(premultiplied(look.ink, look.opacity));

    let cw = app.fonts.cell_width;
    let ch = app.fonts.cell_height;
    let pad = app.padding() as i32;
    let bar = app.tab_bar_height() as i32;
    let baseline = app.fonts.baseline;

    // Tabs.
    if bar > 0 {
        canvas.fill(0, 0, w, bar as usize, premultiplied(look.raised, (look.opacity + 0.05).min(1.0)));
        let tw = tab_width(w, app.tabs.len()) as i32;
        let titles: Vec<String> = app.tabs.iter().map(|t| t.title.clone()).collect();
        for (i, title) in titles.iter().enumerate() {
            let x = i as i32 * tw;
            let active = i == app.active;
            if active {
                canvas.fill(x, 0, tw as usize, bar as usize, opaque(mix(look.raised, look.text, 0.06)));
                canvas.fill(x + 10, bar - 3, (tw - 20).max(0) as usize, 2, opaque(look.accent));
            } else if app.hover_tab == Some(i) {
                canvas.fill(x, 0, tw as usize, bar as usize, opaque(mix(look.raised, look.text, 0.03)));
            }
            if i > 0 && !active && i - 1 != app.active {
                canvas.fill(x, bar / 4, 1, (bar / 2) as usize, opaque(mix(look.raised, look.text, 0.12)));
            }
            let color = if active { look.text } else { look.muted };
            let text_y = (bar - ch as i32) / 2 + baseline - 1;
            draw_text(app, &mut canvas, x + 14, text_y, title, color, x + tw - 10);
        }
    }

    let Some(tab) = app.tabs.get(app.active) else { return };
    let term_arc = tab.term.clone();
    let term = term_arc.lock();
    let content = term.renderable_content();
    let offset = content.display_offset as i32;
    let colors = *content.colors;
    let cursor = content.cursor;
    let selection = content.selection;
    let focused = app.focused;
    let top = pad + bar;
    let default_bg = Color::Named(NamedColor::Background);

    // What to draw, collected first: drawing glyphs needs the font cache mutably.
    struct Item {
        x: i32,
        y: i32,
        c: char,
        width: usize,
        fg: Rgb,
        bg: Option<Rgb>,
        flags: Flags,
    }
    let mut items = Vec::with_capacity(term_columns(&term) * 50);
    let cursor_screen = Point::new(cursor.point.line.0 + offset, cursor.point.column.0);
    for indexed in content.display_iter {
        let cell = indexed.cell;
        let flags = cell.flags;
        if flags.contains(Flags::WIDE_CHAR_SPACER) {
            continue;
        }
        let row = indexed.point.line.0 + offset;
        let col = indexed.point.column.0;
        let mut fg_color = cell.fg;
        if let Color::Named(n) = fg_color {
            if flags.contains(Flags::BOLD) && (n as usize) < 8 {
                fg_color = Color::Named(n.to_bright());
            } else if flags.contains(Flags::DIM) {
                fg_color = Color::Named(n.to_dim());
            }
        }
        let mut fg = look.resolve(fg_color, &colors);
        let mut bg = look.resolve(cell.bg, &colors);
        let mut has_bg = cell.bg != default_bg;
        if flags.contains(Flags::DIM) && !matches!(cell.fg, Color::Named(_)) {
            fg = mix(fg, bg, 0.35);
        }
        if flags.contains(Flags::INVERSE) {
            std::mem::swap(&mut fg, &mut bg);
            has_bg = true;
        }
        if flags.contains(Flags::HIDDEN) {
            fg = bg;
        }
        if selection.is_some_and(|s| s.contains(indexed.point)) {
            bg = mix(if has_bg { bg } else { look.ink }, look.accent, 0.38);
            has_bg = true;
        }
        let is_cursor = cursor.shape != CursorShape::Hidden && row == cursor_screen.line && col == cursor_screen.column;
        if is_cursor && focused && cursor.shape == CursorShape::Block {
            bg = look.accent;
            fg = look.on_accent;
            has_bg = true;
        }
        let width = if flags.contains(Flags::WIDE_CHAR) { 2 } else { 1 };
        items.push(Item {
            x: pad + (col * cw) as i32,
            y: top + row * ch as i32,
            c: cell.c,
            width,
            fg,
            bg: has_bg.then_some(bg),
            flags,
        });
    }
    let cursor_rect = (cursor.shape != CursorShape::Hidden).then(|| {
        (pad + (cursor_screen.column * cw) as i32, top + cursor_screen.line * ch as i32, cursor.shape)
    });
    drop(term);

    for it in &items {
        if let Some(bg) = it.bg {
            canvas.fill(it.x, it.y, cw * it.width, ch, opaque(bg));
        }
    }
    let right = (w as i32) - pad / 2;
    for it in &items {
        if it.c != ' ' && !it.flags.contains(Flags::HIDDEN) {
            let style = crate::font::Style { bold: it.flags.contains(Flags::BOLD), italic: it.flags.contains(Flags::ITALIC) };
            if let Some(g) = app.fonts.glyph(it.c, style, it.width) {
                canvas.glyph(it.x + g.left, it.y + baseline - g.top, g, it.fg, right);
            }
        }
        if it.flags.intersects(Flags::ALL_UNDERLINES) {
            canvas.fill(it.x, it.y + baseline + 2, cw * it.width, 1, opaque(it.fg));
        }
        if it.flags.contains(Flags::STRIKEOUT) {
            canvas.fill(it.x, it.y + ch as i32 / 2, cw * it.width, 1, opaque(it.fg));
        }
    }

    // A cursor that is not a filled block: a bar, a line, or a hollow box when unfocused.
    if let Some((x, y, shape)) = cursor_rect {
        let accent = opaque(look.accent);
        let thick = (2.0 * (ch as f32 / 18.0)).round().max(1.0) as usize;
        match shape {
            CursorShape::Beam => canvas.fill(x, y, thick, ch, accent),
            CursorShape::Underline => canvas.fill(x, y + ch as i32 - thick as i32, cw, thick, accent),
            CursorShape::Block if focused => {}
            _ => {
                canvas.fill(x, y, cw, 1, accent);
                canvas.fill(x, y + ch as i32 - 1, cw, 1, accent);
                canvas.fill(x, y, 1, ch, accent);
                canvas.fill(x + cw as i32 - 1, y, 1, ch, accent);
            }
        }
    }

    // While scrolled back: a thin mark on the right shows where.
    let term = term_arc.lock();
    let history = term_history(&term);
    let shown_offset = term.grid().display_offset();
    let lines = term_screen_lines(&term);
    drop(term);
    if shown_offset > 0 && history > 0 {
        let track = h as i32 - top - pad;
        let total = (history + lines) as f32;
        let size = ((lines as f32 / total) * track as f32).max(24.0) as i32;
        let pos = top + ((history - shown_offset) as f32 / total * track as f32) as i32;
        canvas.fill(w as i32 - 5, pos, 3, size as usize, opaque(mix(look.ink, look.text, 0.4)));
    }
}

fn term_columns<T>(term: &alacritty_terminal::Term<T>) -> usize {
    use alacritty_terminal::grid::Dimensions;
    term.columns()
}

fn term_screen_lines<T>(term: &alacritty_terminal::Term<T>) -> usize {
    use alacritty_terminal::grid::Dimensions;
    term.screen_lines()
}

fn term_history<T>(term: &alacritty_terminal::Term<T>) -> usize {
    use alacritty_terminal::grid::Dimensions;
    term.history_size()
}
