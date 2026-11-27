//! Text: the monospace font fontconfig picks, its bold and italic faces, and
//! for any character they lack, a font fontconfig finds for that character.
//! Lines and blocks are drawn by `boxdraw`, colour emoji come from the
//! emoji font's pictures. Glyphs are drawn once per size and kept.

use std::collections::HashMap;
use std::process::Command;

use fontdue::{Font, FontSettings};

pub struct Glyph {
    pub left: i32,
    /// Distance from the baseline up to the glyph's top row.
    pub top: i32,
    pub width: usize,
    pub height: usize,
    pub coverage: Vec<u8>,
    /// A picture in colour (premultiplied RGBA), for emoji; then `coverage` is unused.
    pub rgba: Option<Vec<[u8; 4]>>,
}

/// Regular, bold, italic or both.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Style {
    pub bold: bool,
    pub italic: bool,
}

pub struct Fonts {
    regular: Font,
    bold: Option<Font>,
    italic: Option<Font>,
    bold_italic: Option<Font>,
    /// The colour emoji font's file, read once when the first emoji shows up.
    emoji: Option<Option<Vec<u8>>>,
    /// Fonts found for characters the main font lacks, by file.
    fallbacks: Vec<Font>,
    fallback_files: Vec<String>,
    /// Which fallback draws a character (None: nothing does).
    fallback_for: HashMap<char, Option<usize>>,
    pub px: f32,
    pub cell_width: usize,
    pub cell_height: usize,
    pub baseline: i32,
    cache: HashMap<(char, Style), Option<Glyph>>,
}

fn fc_match(pattern: &str) -> Option<String> {
    let out = Command::new("fc-match").args(["-f", "%{file}", pattern]).output().ok()?;
    let path = String::from_utf8(out.stdout).ok()?;
    (!path.is_empty()).then_some(path)
}

fn load(path: &str) -> Option<Font> {
    let data = std::fs::read(path).ok()?;
    Font::from_bytes(data, FontSettings { scale: 40.0, ..FontSettings::default() }).ok()
}

impl Fonts {
    pub fn new(family: &str, px: f32) -> Fonts {
        let regular = fc_match(family)
            .and_then(|p| load(&p))
            .or_else(|| load("/usr/share/fonts/noto/NotoSansMono-Regular.ttf"))
            .or_else(|| load("/usr/share/fonts/TTF/DejaVuSansMono.ttf"))
            .expect("no monospace font found (install noto-fonts or ttf-dejavu)");
        // fontconfig falls back to another face when one is missing (bold for
        // bold italic, regular for italic): keep only faces of their own.
        let regular_path = fc_match(family);
        let bold_path = fc_match(&format!("{family}:bold"));
        let face = |style: &str, not: &[&Option<String>]| {
            let path = fc_match(&format!("{family}:{style}"))?;
            if not.iter().any(|p| p.as_deref() == Some(path.as_str())) {
                return None;
            }
            load(&path)
        };
        let bold = face("bold", &[&regular_path]);
        let italic = face("italic", &[&regular_path, &bold_path]);
        let bold_italic = face("bold:italic", &[&regular_path, &bold_path]);
        let mut fonts = Fonts {
            regular,
            bold,
            italic,
            bold_italic,
            emoji: None,
            fallbacks: Vec::new(),
            fallback_files: Vec::new(),
            fallback_for: HashMap::new(),
            px,
            cell_width: 1,
            cell_height: 1,
            baseline: 1,
            cache: HashMap::new(),
        };
        fonts.set_size(px);
        fonts
    }

    pub fn set_size(&mut self, px: f32) {
        self.px = px.clamp(6.0, 72.0);
        self.cache.clear();
        let line = self.regular.horizontal_line_metrics(self.px);
        let (ascent, descent, gap) = line.map(|l| (l.ascent, l.descent, l.line_gap)).unwrap_or((self.px * 0.8, -self.px * 0.2, 0.0));
        self.cell_width = self.regular.metrics('M', self.px).advance_width.round().max(1.0) as usize;
        self.cell_height = (ascent - descent + gap).ceil().max(1.0) as usize;
        self.baseline = (ascent + gap / 2.0).round() as i32;
    }

    fn font_for(&mut self, c: char, style: Style) -> Option<&Font> {
        let styled = match (style.bold, style.italic) {
            (true, true) => self.bold_italic.as_ref().or(self.bold.as_ref()),
            (true, false) => self.bold.as_ref(),
            (false, true) => self.italic.as_ref(),
            (false, false) => None,
        };
        if let Some(f) = styled && f.lookup_glyph_index(c) != 0 {
            return match (style.bold, style.italic) {
                (true, true) => self.bold_italic.as_ref().or(self.bold.as_ref()),
                (true, false) => self.bold.as_ref(),
                _ => self.italic.as_ref(),
            };
        }
        if self.regular.lookup_glyph_index(c) != 0 {
            return Some(&self.regular);
        }
        let index = match self.fallback_for.get(&c) {
            Some(found) => *found,
            None => {
                let found = self.find_fallback(c);
                self.fallback_for.insert(c, found);
                found
            }
        };
        index.map(|i| &self.fallbacks[i])
    }

    fn find_fallback(&mut self, c: char) -> Option<usize> {
        if let Some(i) = self.fallbacks.iter().position(|f| f.lookup_glyph_index(c) != 0) {
            return Some(i);
        }
        let path = fc_match(&format!("monospace:charset={:x}", c as u32))?;
        if self.fallback_files.contains(&path) {
            return None; // that font was tried and lacks it too
        }
        let font = load(&path)?;
        self.fallback_files.push(path);
        self.fallbacks.push(font);
        let i = self.fallbacks.len() - 1;
        (self.fallbacks[i].lookup_glyph_index(c) != 0).then_some(i)
    }

    /// The picture of an emoji, `cells` cells wide, from the colour emoji font.
    fn emoji(&mut self, c: char, cells: usize) -> Option<Glyph> {
        let data = self.emoji.get_or_insert_with(|| fc_match("emoji:color=true").and_then(|p| std::fs::read(p).ok()));
        let face = ttf_parser::Face::parse(data.as_ref()?, 0).ok()?;
        let id = face.glyph_index(c)?;
        let image = face.glyph_raster_image(id, u16::MAX)?;
        if image.format != ttf_parser::RasterImageFormat::PNG {
            return None;
        }
        let mut decoder = png::Decoder::new(std::io::Cursor::new(image.data));
        decoder.set_transformations(png::Transformations::EXPAND);
        let mut reader = decoder.read_info().ok()?;
        let mut buf = vec![0; reader.output_buffer_size()];
        let info = reader.next_frame(&mut buf).ok()?;
        let (sw, sh) = (info.width as usize, info.height as usize);
        let channels = match info.color_type {
            png::ColorType::Rgba => 4,
            png::ColorType::Rgb => 3,
            _ => return None,
        };
        if info.bit_depth != png::BitDepth::Eight || sw == 0 || sh == 0 {
            return None;
        }
        // Fit the cell height and the cells' width, keeping the shape.
        let max_w = self.cell_width * cells;
        let scale = (self.cell_height as f32 / sh as f32).min(max_w as f32 / sw as f32);
        let (dw, dh) = (((sw as f32 * scale).round() as usize).max(1), ((sh as f32 * scale).round() as usize).max(1));
        let mut rgba = vec![[0u8; 4]; dw * dh];
        // Each pixel averages the source pixels it covers.
        for y in 0..dh {
            let (y0, y1) = (y * sh / dh, ((y + 1) * sh / dh).max(y * sh / dh + 1));
            for x in 0..dw {
                let (x0, x1) = (x * sw / dw, ((x + 1) * sw / dw).max(x * sw / dw + 1));
                let mut sum = [0u32; 4];
                for sy in y0..y1 {
                    for sx in x0..x1 {
                        let p = &buf[(sy * sw + sx) * channels..];
                        let a = if channels == 4 { p[3] as u32 } else { 255 };
                        sum[0] += p[0] as u32 * a / 255;
                        sum[1] += p[1] as u32 * a / 255;
                        sum[2] += p[2] as u32 * a / 255;
                        sum[3] += a;
                    }
                }
                let n = ((y1 - y0) * (x1 - x0)) as u32;
                rgba[y * dw + x] = sum.map(|v| (v / n) as u8);
            }
        }
        Some(Glyph {
            left: ((max_w - dw) / 2) as i32,
            top: self.baseline - ((self.cell_height - dh) / 2) as i32,
            width: dw,
            height: dh,
            coverage: Vec::new(),
            rgba: Some(rgba),
        })
    }

    fn draw(&mut self, c: char, style: Style, cells: usize) -> Option<Glyph> {
        if let Some(g) = crate::boxdraw::glyph(c, self.cell_width, self.cell_height, self.baseline) {
            return Some(g);
        }
        // Emoji pictures first for characters that are usually shown in colour.
        let pictorial = matches!(c as u32, 0x1F000..=0x1FAFF | 0x2600..=0x27BF | 0x2B00..=0x2BFF);
        if pictorial && cells == 2 && let Some(g) = self.emoji(c, cells) {
            return Some(g);
        }
        let px = self.px;
        // No italic face: lean the upright one.
        let lean = style.italic && if style.bold { self.bold_italic.is_none() && self.italic.is_none() } else { self.italic.is_none() };
        let outline = self.font_for(c, style).map(|font| {
            let (m, coverage) = font.rasterize(c, px);
            let g = Glyph { left: m.xmin, top: m.height as i32 + m.ymin, width: m.width, height: m.height, coverage, rgba: None };
            if lean { slant(g) } else { g }
        });
        match outline {
            Some(g) if g.coverage.iter().any(|&v| v > 0) => Some(g),
            // A font with only coloured pictures for it (no outline): try the picture.
            _ => self.emoji(c, cells.max(1)),
        }
    }

    pub fn glyph(&mut self, c: char, style: Style, cells: usize) -> Option<&Glyph> {
        if c == ' ' || c == '\0' {
            return None;
        }
        if !self.cache.contains_key(&(c, style)) {
            let g = self.draw(c, style, cells);
            self.cache.insert((c, style), g);
        }
        self.cache.get(&(c, style)).and_then(Option::as_ref)
    }
}

/// The glyph leaned to the right, as an italic stand-in: each row moves by a
/// fifth of its height above the baseline.
fn slant(g: Glyph) -> Glyph {
    const SLOPE: f32 = 0.2;
    if g.width == 0 || g.height == 0 {
        return g;
    }
    let shift_of = |y: usize| (g.top - y as i32) as f32 * SLOPE;
    let min_shift = shift_of(g.height - 1).min(0.0);
    let max_shift = shift_of(0).max(0.0);
    let extra = (max_shift - min_shift).ceil() as usize + 1;
    let width = g.width + extra;
    let mut coverage = vec![0u8; width * g.height];
    for y in 0..g.height {
        let shift = shift_of(y) - min_shift;
        let (whole, frac) = (shift.floor() as usize, shift.fract());
        for x in 0..g.width {
            let v = g.coverage[y * g.width + x] as f32;
            if v == 0.0 {
                continue;
            }
            let i = y * width + x + whole;
            coverage[i] = (coverage[i] as f32 + v * (1.0 - frac)).min(255.0) as u8;
            coverage[i + 1] = (coverage[i + 1] as f32 + v * frac).min(255.0) as u8;
        }
    }
    Glyph { left: g.left + min_shift.floor() as i32, width, coverage, ..g }
}
