//! Text: the monospace font fontconfig picks, its bold face, and for any
//! character they lack, a font fontconfig finds for that character. Glyphs are
//! drawn once per size and kept.

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
}

pub struct Fonts {
    regular: Font,
    bold: Option<Font>,
    /// Fonts found for characters the main font lacks, by file.
    fallbacks: Vec<Font>,
    fallback_files: Vec<String>,
    /// Which fallback draws a character (None: nothing does).
    fallback_for: HashMap<char, Option<usize>>,
    pub px: f32,
    pub cell_width: usize,
    pub cell_height: usize,
    pub baseline: i32,
    cache: HashMap<(char, bool), Glyph>,
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
        let bold = fc_match(&format!("{family}:bold")).and_then(|p| load(&p));
        let mut fonts = Fonts {
            regular,
            bold,
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

    fn font_for(&mut self, c: char, bold: bool) -> Option<&Font> {
        if bold && let Some(b) = &self.bold && b.lookup_glyph_index(c) != 0 {
            return self.bold.as_ref();
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

    pub fn glyph(&mut self, c: char, bold: bool) -> Option<&Glyph> {
        if c == ' ' || c == '\0' {
            return None;
        }
        if !self.cache.contains_key(&(c, bold)) {
            let px = self.px;
            let glyph = self.font_for(c, bold).map(|font| {
                let (m, coverage) = font.rasterize(c, px);
                Glyph {
                    left: m.xmin,
                    top: m.height as i32 + m.ymin,
                    width: m.width,
                    height: m.height,
                    coverage,
                }
            });
            match glyph {
                Some(g) => self.cache.insert((c, bold), g),
                None => return None,
            };
        }
        self.cache.get(&(c, bold))
    }
}
