//! Window titles drawn into small textures with the OziOS typeface.

use ab_glyph::{point, Font, FontVec, PxScale, ScaleFont};

const FONTS: [&str; 4] = [
    "/usr/share/fonts/TTF/overpass-semibold.ttf",
    "/usr/share/fonts/TTF/overpass-regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
];

pub const TEXT_PX: f32 = 13.5;

pub fn load_font() -> Option<FontVec> {
    FONTS.iter().find_map(|path| {
        let data = std::fs::read(path).ok()?;
        FontVec::try_from_vec(data).ok()
    })
}

/// A premultiplied BGRA (little-endian ARGB8888) image of one line of text.
#[derive(Debug, Clone, PartialEq)]
pub struct Rendered {
    pub width: i32,
    pub height: i32,
    pub pixels: Vec<u8>,
}

fn advance_of<F: Font>(font: &impl ScaleFont<F>, text: &str) -> f32 {
    let mut width = 0.0;
    let mut previous = None;
    for c in text.chars() {
        let id = font.glyph_id(c);
        if let Some(p) = previous {
            width += font.kern(p, id);
        }
        width += font.h_advance(id);
        previous = Some(id);
    }
    width
}

/// Shorten `text` with an ellipsis until it fits `max_width` pixels.
pub fn fit(font: &FontVec, px: f32, text: &str, max_width: f32) -> String {
    let scaled = font.as_scaled(PxScale::from(px));
    if advance_of(&scaled, text) <= max_width {
        return text.to_string();
    }
    let mut chars: Vec<char> = text.chars().collect();
    while !chars.is_empty() {
        chars.pop();
        let candidate: String = chars.iter().collect::<String>().trim_end().to_string() + "…";
        if advance_of(&scaled, &candidate) <= max_width {
            return candidate;
        }
    }
    String::new()
}

/// Draw `text` in `color` (0..1 RGB) at `scale` times the normal size.
pub fn render(font: &FontVec, text: &str, color: [f32; 3], scale: f32) -> Option<Rendered> {
    render_px(font, text, color, TEXT_PX * scale)
}

/// Draw `text` at a given pixel size.
pub fn render_px(font: &FontVec, text: &str, color: [f32; 3], size: f32) -> Option<Rendered> {
    if text.is_empty() {
        return None;
    }
    let px = PxScale::from(size);
    let scaled = font.as_scaled(px);
    let width = advance_of(&scaled, text).ceil() as i32 + 2;
    let height = (scaled.ascent() - scaled.descent()).ceil() as i32 + 2;
    if width <= 2 || height <= 0 {
        return None;
    }
    let mut pixels = vec![0u8; (width * height * 4) as usize];
    let mut x = 1.0;
    let mut previous = None;
    for c in text.chars() {
        let id = scaled.glyph_id(c);
        if let Some(p) = previous {
            x += scaled.kern(p, id);
        }
        let glyph = id.with_scale_and_position(px, point(x, 1.0 + scaled.ascent()));
        x += scaled.h_advance(id);
        previous = Some(id);
        let Some(outline) = font.outline_glyph(glyph) else {
            continue;
        };
        let bounds = outline.px_bounds();
        outline.draw(|gx, gy, coverage| {
            let px = bounds.min.x as i32 + gx as i32;
            let py = bounds.min.y as i32 + gy as i32;
            if px < 0 || py < 0 || px >= width || py >= height {
                return;
            }
            let i = ((py * width + px) * 4) as usize;
            let a = coverage.clamp(0.0, 1.0).max(pixels[i + 3] as f32 / 255.0);
            pixels[i] = (color[2] * a * 255.0) as u8;
            pixels[i + 1] = (color[1] * a * 255.0) as u8;
            pixels[i + 2] = (color[0] * a * 255.0) as u8;
            pixels[i + 3] = (a * 255.0) as u8;
        });
    }
    Some(Rendered { width, height, pixels })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn draws_and_fits_when_a_font_is_installed() {
        let Some(font) = load_font() else {
            return; // CI images without fonts
        };
        let r = render(&font, "Konsole — ğüşıöç", [1.0, 1.0, 1.0], 1.0).unwrap();
        assert!(r.width > 40 && r.height > 10);
        assert!(r.pixels.chunks(4).any(|p| p[3] > 200), "some solid pixels");
        assert!(r.pixels.chunks(4).all(|p| p[0] <= p[3] && p[2] <= p[3]), "premultiplied");

        let long = "a very long window title that cannot possibly fit in the bar";
        let short = fit(&font, TEXT_PX, long, 120.0);
        assert!(short.ends_with('…') && short.len() < long.len());
        assert_eq!(fit(&font, TEXT_PX, "ok", 120.0), "ok");
    }

    #[test]
    fn empty_text_draws_nothing() {
        if let Some(font) = load_font() {
            assert!(render(&font, "", [1.0; 3], 1.0).is_none());
        }
    }
}
