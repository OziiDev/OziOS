//! The pointer on real hardware: the system cursor theme, or the client's own
//! cursor surface when it sets one.

use smithay::{
    backend::{
        allocator::Fourcc,
        renderer::{
            element::{
                memory::{MemoryRenderBuffer, MemoryRenderBufferRenderElement},
                surface::{render_elements_from_surface_tree, WaylandSurfaceRenderElement},
                Kind,
            },
            gles::GlesRenderer,
        },
    },
    input::pointer::{CursorImageAttributes, CursorImageStatus},
    utils::{IsAlive, Logical, Physical, Point, Transform},
    wayland::compositor::with_states,
};

use crate::render::{OziElement, WindowPart};

pub struct Cursor {
    buffer: Option<MemoryRenderBuffer>,
    hotspot: Point<i32, Logical>,
}

fn theme_name() -> String {
    std::env::var("XCURSOR_THEME").unwrap_or_else(|_| "breeze_cursors".into())
}

fn theme_size() -> u32 {
    std::env::var("XCURSOR_SIZE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(24)
}

impl Cursor {
    pub fn load() -> Self {
        let size = theme_size();
        for theme in [theme_name(), "Adwaita".into(), "default".into()] {
            let theme = xcursor::CursorTheme::load(&theme);
            for name in ["default", "left_ptr"] {
                let Some(path) = theme.load_icon(name) else {
                    continue;
                };
                let Ok(bytes) = std::fs::read(path) else {
                    continue;
                };
                let Some(images) = xcursor::parser::parse_xcursor(&bytes) else {
                    continue;
                };
                // The image closest to the wanted size.
                let Some(image) = images
                    .iter()
                    .min_by_key(|i| (i.size as i64 - size as i64).abs())
                else {
                    continue;
                };
                let buffer = MemoryRenderBuffer::from_slice(
                    &image.pixels_rgba,
                    Fourcc::Abgr8888,
                    (image.width as i32, image.height as i32),
                    1,
                    Transform::Normal,
                    None,
                );
                return Cursor {
                    buffer: Some(buffer),
                    hotspot: (image.xhot as i32, image.yhot as i32).into(),
                };
            }
        }
        tracing::warn!("no cursor theme found; drawing a plain pointer is not possible");
        Cursor { buffer: None, hotspot: (0, 0).into() }
    }

    /// Elements for the pointer at `location` (relative to the output), top-most first.
    pub fn elements(
        &self,
        renderer: &mut GlesRenderer,
        status: &CursorImageStatus,
        location: Point<f64, Logical>,
        scale: f64,
    ) -> Vec<OziElement> {
        match status {
            CursorImageStatus::Hidden => Vec::new(),
            CursorImageStatus::Surface(surface) if surface.alive() => {
                let hotspot = with_states(surface, |states| {
                    states
                        .data_map
                        .get::<std::sync::Mutex<CursorImageAttributes>>()
                        .and_then(|a| a.lock().ok().map(|a| a.hotspot))
                        .unwrap_or_default()
                });
                let pos: Point<i32, Physical> = (location - hotspot.to_f64()).to_physical(scale).to_i32_round();
                let parts: Vec<WaylandSurfaceRenderElement<GlesRenderer>> =
                    render_elements_from_surface_tree(renderer, surface, pos, scale, 1.0, Kind::Cursor);
                parts
                    .into_iter()
                    .map(|p| OziElement::Part(WindowPart::Plain(p)))
                    .collect()
            }
            _ => {
                let Some(buffer) = &self.buffer else {
                    return Vec::new();
                };
                let pos = (location - self.hotspot.to_f64()).to_physical(scale);
                MemoryRenderBufferRenderElement::from_buffer(renderer, pos, buffer, None, None, None, Kind::Cursor)
                    .map(|e| vec![OziElement::Part(WindowPart::Title(e))])
                    .unwrap_or_default()
            }
        }
    }
}
