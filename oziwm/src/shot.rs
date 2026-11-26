//! Screenshots: the frame as it is on screen, saved as PNG. Print saves one to
//! the Pictures folder; IPC `{"do":"screenshot","path":...}` writes one anywhere
//! (used to test the real session from outside it).

use std::{fs::File, io::BufWriter, path::{Path, PathBuf}, time::Instant};

use smithay::{
    backend::{
        allocator::Fourcc,
        renderer::{
            damage::OutputDamageTracker,
            gles::{GlesRenderer, GlesTexture},
            Bind, ExportMem, Offscreen,
        },
    },
    utils::{Buffer as BufferCoords, Physical, Rectangle, Size, Transform},
};

use crate::render::OziElement;

/// OziOS ink, `#080B10`.
const BACKGROUND: [f32; 4] = [0.031, 0.043, 0.063, 1.0];

/// Draw `elements` off screen and return tightly packed RGBA rows, top row first.
pub fn capture(
    renderer: &mut GlesRenderer,
    elements: &[OziElement],
    size: Size<i32, Physical>,
    scale: f64,
) -> Result<Vec<u8>, String> {
    let buffer_size = Size::<i32, BufferCoords>::from((size.w, size.h));
    let mut texture: GlesTexture = renderer
        .create_buffer(Fourcc::Abgr8888, buffer_size)
        .map_err(|e| format!("no offscreen buffer: {e:?}"))?;
    let mut framebuffer = renderer.bind(&mut texture).map_err(|e| format!("bind: {e:?}"))?;
    let mut tracker = OutputDamageTracker::new(size, scale, Transform::Normal);
    tracker
        .render_output(renderer, &mut framebuffer, 0, elements, BACKGROUND)
        .map_err(|e| format!("render: {e:?}"))?;
    let mapping = renderer
        .copy_framebuffer(&framebuffer, Rectangle::from_size(buffer_size), Fourcc::Abgr8888)
        .map_err(|e| format!("read back: {e:?}"))?;
    let bytes = renderer.map_texture(&mapping).map_err(|e| format!("map: {e:?}"))?;
    let mut rgba = bytes.to_vec();
    // A screen is opaque; keep the PNG from looking washed out where alpha was left low.
    for px in rgba.chunks_exact_mut(4) {
        px[3] = 255;
    }
    Ok(rgba)
}

pub fn write_png(path: &Path, rgba: &[u8], width: u32, height: u32) -> Result<(), String> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    let file = File::create(path).map_err(|e| e.to_string())?;
    let mut encoder = png::Encoder::new(BufWriter::new(file), width, height);
    encoder.set_color(png::ColorType::Rgba);
    encoder.set_depth(png::BitDepth::Eight);
    let mut writer = encoder.write_header().map_err(|e| e.to_string())?;
    writer.write_image_data(rgba).map_err(|e| e.to_string())
}

/// The user's Pictures folder (XDG_PICTURES_DIR, "Resimler" on a Turkish system).
pub fn pictures_dir() -> PathBuf {
    let home = std::env::var("HOME").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("/tmp"));
    let config = std::env::var("XDG_CONFIG_HOME").map(PathBuf::from).unwrap_or_else(|_| home.join(".config"));
    std::fs::read_to_string(config.join("user-dirs.dirs"))
        .ok()
        .and_then(|text| parse_pictures_dir(&text, &home))
        .unwrap_or_else(|| home.join("Pictures"))
}

pub fn parse_pictures_dir(text: &str, home: &Path) -> Option<PathBuf> {
    let line = text.lines().find(|l| l.trim_start().starts_with("XDG_PICTURES_DIR="))?;
    let value = line.split_once('=')?.1.trim().trim_matches('"');
    let value = value.replace("$HOME", &home.to_string_lossy());
    (!value.is_empty()).then(|| PathBuf::from(value))
}

pub fn default_name() -> String {
    let now = chrono::Local::now();
    format!("{} {}.png", crate::i18n::tr("Screenshot"), now.format("%Y-%m-%d %H-%M-%S"))
}

/// Rolling frame timings, for `{"get":"stats"}`.
#[derive(Debug, Default)]
pub struct FrameStats {
    times_ms: Vec<f32>,
    stamps: Vec<Instant>,
}

impl FrameStats {
    pub fn record(&mut self, ms: f32) {
        let now = Instant::now();
        self.times_ms.push(ms);
        self.stamps.push(now);
        if self.times_ms.len() > 240 {
            self.times_ms.remove(0);
            self.stamps.remove(0);
        }
    }

    pub fn json(&self) -> serde_json::Value {
        let n = self.times_ms.len().max(1) as f32;
        let avg = self.times_ms.iter().sum::<f32>() / n;
        let max = self.times_ms.iter().copied().fold(0.0, f32::max);
        let fps = self
            .stamps
            .iter()
            .filter(|t| t.elapsed().as_secs_f32() < 1.0)
            .count();
        serde_json::json!({
            "frames": self.times_ms.len(),
            "avg_ms": (avg * 100.0).round() / 100.0,
            "max_ms": (max * 100.0).round() / 100.0,
            "last_ms": self.times_ms.last().copied().unwrap_or(0.0),
            "fps": fps,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pictures_dir_from_user_dirs() {
        let text = "# comment\nXDG_DESKTOP_DIR=\"$HOME/Masaüstü\"\nXDG_PICTURES_DIR=\"$HOME/Resimler\"\n";
        assert_eq!(parse_pictures_dir(text, Path::new("/home/ozi")), Some(PathBuf::from("/home/ozi/Resimler")));
        assert_eq!(parse_pictures_dir("XDG_MUSIC_DIR=x\n", Path::new("/h")), None);
    }

    #[test]
    fn stats() {
        let mut s = FrameStats::default();
        s.record(4.0);
        s.record(8.0);
        let j = s.json();
        assert_eq!(j["frames"], 2);
        assert_eq!(j["avg_ms"], 6.0);
        assert_eq!(j["max_ms"], 8.0);
        assert_eq!(j["fps"], 2);
    }

    #[test]
    fn png_round_trip() {
        let dir = std::env::temp_dir().join(format!("oziwm-shot-{}", std::process::id()));
        let path = dir.join("a.png");
        write_png(&path, &[255, 0, 0, 255, 0, 255, 0, 255], 2, 1).unwrap();
        let decoder = png::Decoder::new(std::io::BufReader::new(File::open(&path).unwrap()));
        let reader = decoder.read_info().unwrap();
        assert_eq!((reader.info().width, reader.info().height), (2, 1));
        let _ = std::fs::remove_dir_all(dir);
    }
}
