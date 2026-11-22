//! Turning windows into render elements: rounded content, the OziOS frame, titles
//! and the opening animation.

use std::{collections::HashMap, time::Instant};

use smithay::{
    backend::{
        allocator::Fourcc,
        renderer::{
            element::{
                memory::{MemoryRenderBuffer, MemoryRenderBufferRenderElement},
                render_elements,
                surface::{WaylandSurfaceRenderElement, WaylandSurfaceTexture},
                utils::{Relocate, RelocateRenderElement, RescaleRenderElement},
                AsRenderElements, Element, Id, Kind, RenderElement, UnderlyingStorage,
            },
            gles::{
                element::PixelShaderElement, GlesError, GlesFrame, GlesPixelProgram, GlesRenderer,
                GlesTexProgram, Uniform, UniformName, UniformType,
            },
            utils::{CommitCounter, DamageSet, OpaqueRegions},
            Texture,
        },
    },
    desktop::Window,
    reexports::wayland_protocols::xdg::decoration::zv1::server::zxdg_toplevel_decoration_v1::Mode as DecorationMode,
    utils::{Buffer as BufferCoords, Logical, Physical, Point, Rectangle, Scale, Size, Transform},
};

use crate::{
    anim::{Fade, Opening},
    deco::{self, Button, Frame, Rect},
    state::window_id,
    theme::Look,
    title, OziWm,
};

pub struct Shaders {
    frame: GlesPixelProgram,
    rounded: GlesTexProgram,
    lock: GlesPixelProgram,
}

impl Shaders {
    pub fn compile(renderer: &mut GlesRenderer) -> Result<Self, GlesError> {
        use UniformType::*;
        let frame = renderer.compile_custom_pixel_shader(
            include_str!("shaders/frame.frag"),
            &[
                UniformName::new("ozi_rect", _4f),
                UniformName::new("ozi_radius", _1f),
                UniformName::new("ozi_border", _1f),
                UniformName::new("ozi_title", _1f),
                UniformName::new("ozi_active", _1f),
                UniformName::new("ozi_glow", _1f),
                UniformName::new("ozi_time", _1f),
                UniformName::new("ozi_c1", _3f),
                UniformName::new("ozi_c2", _3f),
                UniformName::new("ozi_bar", _3f),
                UniformName::new("ozi_muted", _3f),
                UniformName::new("ozi_btn", _4f),
                UniformName::new("ozi_hover", _1f),
            ],
        )?;
        let rounded = renderer.compile_custom_texture_shader(
            include_str!("shaders/rounded.frag"),
            &[
                UniformName::new("ozi_origin", _2f),
                UniformName::new("ozi_tex_size", _2f),
                UniformName::new("ozi_px_size", _2f),
                UniformName::new("ozi_radius", _1f),
                UniformName::new("ozi_round_top", _1f),
            ],
        )?;
        let lock = renderer.compile_custom_pixel_shader(
            include_str!("shaders/lock.frag"),
            &[
                UniformName::new("ozi_time", _1f),
                UniformName::new("ozi_ink", _3f),
                UniformName::new("ozi_c1", _3f),
                UniformName::new("ozi_c2", _3f),
                UniformName::new("ozi_field", _4f),
                UniformName::new("ozi_state", _1f),
                UniformName::new("ozi_shake", _1f),
            ],
        )?;
        Ok(Shaders { frame, rounded, lock })
    }
}

/// Per-window visual state that outlives a single frame.
pub struct WindowLook {
    pub active: Fade,
    pub opening: Option<Opening>,
    pub hover: Option<Button>,
    /// Where the frame was when it last moved: it flows from there to its new place.
    pub morph: Option<(Rect, Instant)>,
    frame: Option<PixelShaderElement>,
    title: Option<CachedTitle>,
}

impl WindowLook {
    /// Colours changed: draw the title again.
    pub fn forget_title(&mut self) {
        self.title = None;
    }

    pub fn new(now: Instant) -> Self {
        WindowLook {
            active: Fade::new(0.0),
            opening: Some(Opening { start: now }),
            hover: None,
            morph: None,
            frame: None,
            title: None,
        }
    }
}

pub type Looks = HashMap<u64, WindowLook>;

struct CachedTitle {
    text: String,
    bar_width: i32,
    active: bool,
    size: (i32, i32),
    buffer: MemoryRenderBuffer,
}

/// A client surface drawn through the rounded-corner shader.
#[derive(Debug)]
pub struct RoundedSurface {
    inner: WaylandSurfaceRenderElement<GlesRenderer>,
    program: GlesTexProgram,
    /// The window's content rectangle, in physical pixels.
    window: Rectangle<i32, Physical>,
    radius: f32,
    round_top: bool,
}

impl Element for RoundedSurface {
    fn id(&self) -> &Id {
        self.inner.id()
    }
    fn current_commit(&self) -> CommitCounter {
        self.inner.current_commit()
    }
    fn location(&self, scale: Scale<f64>) -> Point<i32, Physical> {
        self.inner.location(scale)
    }
    fn src(&self) -> Rectangle<f64, BufferCoords> {
        self.inner.src()
    }
    fn transform(&self) -> Transform {
        self.inner.transform()
    }
    fn geometry(&self, scale: Scale<f64>) -> Rectangle<i32, Physical> {
        self.inner.geometry(scale)
    }
    fn damage_since(&self, scale: Scale<f64>, commit: Option<CommitCounter>) -> DamageSet<i32, Physical> {
        self.inner.damage_since(scale, commit)
    }
    fn opaque_regions(&self, _scale: Scale<f64>) -> OpaqueRegions<i32, Physical> {
        // Corners are transparent now; claiming nothing is always correct.
        OpaqueRegions::default()
    }
    fn alpha(&self) -> f32 {
        self.inner.alpha()
    }
    fn kind(&self) -> Kind {
        self.inner.kind()
    }
}

impl RenderElement<GlesRenderer> for RoundedSurface {
    fn draw(
        &self,
        frame: &mut GlesFrame<'_, '_>,
        src: Rectangle<f64, BufferCoords>,
        dst: Rectangle<i32, Physical>,
        damage: &[Rectangle<i32, Physical>],
        opaque_regions: &[Rectangle<i32, Physical>],
    ) -> Result<(), GlesError> {
        let buffer = match self.inner.texture() {
            WaylandSurfaceTexture::Texture(texture) => texture.size(),
            WaylandSurfaceTexture::SolidColor(_) => {
                return self.inner.draw(frame, src, dst, damage, opaque_regions);
            }
        };
        if self.radius <= 0.0
            || self.inner.transform() != Transform::Normal
            || dst.size.w <= 0
            || dst.size.h <= 0
            || buffer.w <= 0
            || buffer.h <= 0
        {
            return self.inner.draw(frame, src, dst, damage, opaque_regions);
        }
        // Texture coordinate of a physical point, for this element's src -> dst mapping.
        let sx = src.size.w / dst.size.w as f64;
        let sy = src.size.h / dst.size.h as f64;
        let to_tex = |x: i32, y: i32| {
            (
                ((src.loc.x + (x - dst.loc.x) as f64 * sx) / buffer.w as f64) as f32,
                ((src.loc.y + (y - dst.loc.y) as f64 * sy) / buffer.h as f64) as f32,
            )
        };
        let origin = to_tex(self.window.loc.x, self.window.loc.y);
        let tex_size = (
            (self.window.size.w as f64 * sx / buffer.w as f64) as f32,
            (self.window.size.h as f64 * sy / buffer.h as f64) as f32,
        );
        frame.override_default_tex_program(
            self.program.clone(),
            vec![
                Uniform::new("ozi_origin", origin),
                Uniform::new("ozi_tex_size", tex_size),
                Uniform::new("ozi_px_size", (self.window.size.w as f32, self.window.size.h as f32)),
                Uniform::new("ozi_radius", self.radius),
                Uniform::new("ozi_round_top", if self.round_top { 1.0f32 } else { 0.0 }),
            ],
        );
        let result = self.inner.draw(frame, src, dst, damage, &[]);
        frame.clear_tex_program_override();
        result
    }

    fn underlying_storage(&self, _renderer: &mut GlesRenderer) -> Option<UnderlyingStorage<'_>> {
        // Never scan out directly: the corners must go through the shader.
        None
    }
}

render_elements! {
    pub WindowPart<=GlesRenderer>;
    Surface=RoundedSurface,
    Frame=PixelShaderElement,
    Title=MemoryRenderBufferRenderElement<GlesRenderer>,
    Plain=WaylandSurfaceRenderElement<GlesRenderer>,
}

render_elements! {
    pub OziElement<=GlesRenderer>;
    Part=WindowPart,
    Scaled=RescaleRenderElement<WindowPart>,
    Moved=RelocateRenderElement<RescaleRenderElement<WindowPart>>,
}

pub fn is_server_side(window: &Window) -> bool {
    window
        .toplevel()
        .is_some_and(|t| t.current_state().decoration_mode == Some(DecorationMode::ServerSide))
}

pub fn frame_of(state: &OziWm, window: &Window) -> Option<Frame> {
    let loc = state.space.element_location(window)?;
    let size = window.geometry().size;
    let maximized_or_full = window.toplevel().is_some_and(|t| {
        let s = t.current_state();
        s.states.contains(smithay::reexports::wayland_protocols::xdg::shell::server::xdg_toplevel::State::Fullscreen)
    });
    let titled = is_server_side(window) && !maximized_or_full;
    Some(Frame::new(Rect::new(loc.x, loc.y, size.w, size.h), titled))
}

fn rect_logical(r: Rect) -> Rectangle<i32, Logical> {
    Rectangle::new((r.x, r.y).into(), (r.w, r.h).into())
}

/// Frame shader element for one window, reused between frames so damage stays small.
fn frame_element(
    look: &mut WindowLook,
    shaders: &Shaders,
    style: &Look,
    frame: &Frame,
    origin: Point<i32, Logical>,
    active: f32,
    time: f32,
    alpha: f32,
) -> PixelShaderElement {
    let area = frame.render_area();
    let outer = frame.outer();
    let theme = &style.theme;
    let (btn_x, btn_y) = frame
        .button_rect(Button::Minimize)
        .map(|r| ((r.x - area.x) as f32 + r.w as f32 / 2.0, (r.y - area.y) as f32 + r.h as f32 / 2.0))
        .unwrap_or((0.0, 0.0));
    let hover = match look.hover {
        Some(Button::Minimize) => 0.0f32,
        Some(Button::Maximize) => 1.0,
        Some(Button::Close) => 2.0,
        None => -1.0,
    };
    let uniforms = vec![
        Uniform::new(
            "ozi_rect",
            [(outer.x - area.x) as f32, (outer.y - area.y) as f32, outer.w as f32, outer.h as f32],
        ),
        Uniform::new("ozi_radius", style.corner_radius),
        Uniform::new("ozi_border", deco::BORDER),
        Uniform::new("ozi_title", frame.title_height() as f32),
        Uniform::new("ozi_active", active),
        Uniform::new("ozi_glow", style.glow),
        Uniform::new("ozi_time", time),
        Uniform::new("ozi_c1", theme.accent),
        Uniform::new("ozi_c2", theme.accent2),
        Uniform::new("ozi_bar", theme.raised),
        Uniform::new("ozi_muted", theme.muted),
        Uniform::new(
            "ozi_btn",
            [btn_x, btn_y, (deco::BUTTON + deco::BUTTON_GAP) as f32, deco::BUTTON as f32 / 2.0],
        ),
        Uniform::new("ozi_hover", hover),
    ];
    let mut area = rect_logical(area);
    area.loc -= origin;
    // Alpha is fixed when an element is made: while a window fades in, use a fresh one.
    if (alpha - 1.0).abs() > f32::EPSILON {
        return PixelShaderElement::new(shaders.frame.clone(), area, None, alpha, uniforms, Kind::Unspecified);
    }
    
    match look.frame.as_mut() {
        Some(element) => {
            element.resize(area, None);
            element.update_uniforms(uniforms);
            element.clone()
        }
        None => {
            let element = PixelShaderElement::new(shaders.frame.clone(), area, None, 1.0, uniforms, Kind::Unspecified);
            look.frame = Some(element.clone());
            element
        }
    }
}

fn title_element(
    look: &mut WindowLook,
    renderer: &mut GlesRenderer,
    font: Option<&ab_glyph::FontVec>,
    style: &Look,
    frame: &Frame,
    origin: Point<i32, Logical>,
    text: &str,
    active: bool,
    scale: f64,
    alpha: f32,
) -> Option<MemoryRenderBufferRenderElement<GlesRenderer>> {
    let font = font?;
    let bar = frame.title_bar()?;
    let buttons_width = 14 + 3 * deco::BUTTON + 2 * deco::BUTTON_GAP + 12;
    let room = (bar.w - 2 * buttons_width).max(0) as f32;
    let cached = look
        .title
        .as_ref()
        .is_some_and(|c| c.text == text && c.bar_width == bar.w && c.active == active);
    if !cached {
        let fitted = title::fit(font, title::TEXT_PX, text, room);
        let color = if active { style.theme.text } else { style.theme.muted };
        let rendered = title::render(font, &fitted, color, 1.0)?;
        let buffer = MemoryRenderBuffer::from_slice(
            &rendered.pixels,
            Fourcc::Argb8888,
            (rendered.width, rendered.height),
            1,
            Transform::Normal,
            None,
        );
        look.title = Some(CachedTitle {
            text: text.to_string(),
            bar_width: bar.w,
            active,
            size: (rendered.width, rendered.height),
            buffer,
        });
    }
    let cached = look.title.as_ref()?;
    let buffer = &cached.buffer;
    let size: Size<i32, Logical> = cached.size.into();
    let x = (bar.x - origin.x) as f64 + (bar.w - size.w) as f64 / 2.0;
    let y = (bar.y - origin.y) as f64 + (bar.h - size.h) as f64 / 2.0 + 0.5;
    let location = Point::<f64, Logical>::from((x.round(), y.round())).to_physical(scale);
    MemoryRenderBufferRenderElement::from_buffer(renderer, location, buffer, Some(alpha), None, None, Kind::Unspecified)
        .ok()
}

fn window_title(window: &Window) -> String {
    use smithay::wayland::{compositor::with_states, shell::xdg::XdgToplevelSurfaceData};
    window
        .toplevel()
        .and_then(|t| {
            with_states(t.wl_surface(), |states| {
                states
                    .data_map
                    .get::<XdgToplevelSurfaceData>()
                    .and_then(|d| d.lock().ok().and_then(|d| d.title.clone()))
            })
        })
        .unwrap_or_default()
}

/// Everything the windows contribute to a frame, top-most first.
pub fn window_elements(
    state: &mut OziWm,
    renderer: &mut GlesRenderer,
    shaders: &Shaders,
    origin: Point<i32, Logical>,
    scale: f64,
    now: Instant,
) -> (Vec<OziElement>, bool) {
    let time = now.duration_since(state.start_time).as_secs_f32();
    let focused = state.focused_window().map(|w| window_id(&w));
    let style = state.look.clone();
    let mut out = Vec::new();
    let mut animating = false;

    // Switching workspaces: the arriving windows slide in from the side and fade up.
    let (slide, slide_alpha) = match state.ws_switch {
        Some((start, dir)) if style.animation_speed > 0.0 => {
            let t = now.saturating_duration_since(start).as_secs_f64() / (0.28 / style.animation_speed);
            if t >= 1.0 {
                state.ws_switch = None;
                (0.0, 1.0)
            } else {
                let e = crate::anim::ease_out_cubic(t);
                animating = true;
                (dir as f64 * (1.0 - e) * 120.0, e as f32)
            }
        }
        _ => {
            state.ws_switch = None;
            (0.0, 1.0)
        }
    };

    let windows: Vec<Window> = state.space.elements().rev().cloned().collect();
    let live: Vec<u64> = windows.iter().map(window_id).collect();
    state.looks.retain(|id, _| live.contains(id));

    for window in windows {
        let id = window_id(&window);
        let Some(frame) = frame_of(state, &window) else {
            continue;
        };
        let look = state.looks.entry(id).or_insert_with(|| WindowLook::new(now));
        let speed = style.animation_speed;
        let fade_ms = if speed > 0.0 { (180.0 / speed) as u64 } else { 0 };
        look.active.set(
            if Some(id) == focused { 1.0 } else { 0.0 },
            std::time::Duration::from_millis(fade_ms),
            now,
        );
        let active = look.active.value_at(now) as f32;
        animating |= look.active.running(now);

        let opening = look.opening.and_then(|o| o.at(now, speed));
        if opening.is_none() {
            look.opening = None;
        }
        animating |= opening.is_some();
        let (zoom, alpha) = opening.unwrap_or((1.0, 1.0));
        let alpha = alpha as f32 * slide_alpha;

        let mut parts: Vec<WindowPart> = Vec::new();

        let text = window_title(&window);
        if let Some(t) = title_element(
            look,
            renderer,
            state.font.as_ref(),
            &style,
            &frame,
            origin,
            &text,
            Some(id) == focused,
            scale,
            alpha,
        ) {
            parts.push(WindowPart::Title(t));
        }

        let content = frame.content;
        let mut window_rect = rect_logical(content);
        window_rect.loc -= origin;
        let window_phys = window_rect.to_physical_precise_round(scale);
        let render_loc = (Point::<i32, Logical>::from((content.x, content.y)) - window.geometry().loc - origin)
            .to_physical_precise_round(scale);
        let surfaces: Vec<WaylandSurfaceRenderElement<GlesRenderer>> =
            window.render_elements(renderer, render_loc, Scale::from(scale), alpha);
        for surface in surfaces {
            parts.push(WindowPart::Surface(RoundedSurface {
                inner: surface,
                program: shaders.rounded.clone(),
                window: window_phys,
                radius: style.corner_radius * scale as f32,
                round_top: !frame.titled,
            }));
        }

        let glowing = active > 0.0 && style.glow > 0.0;
        animating |= glowing;
        parts.push(WindowPart::Frame(frame_element(look, shaders, &style, &frame, origin, active, time, alpha)));

        // How this window is moved and stretched this frame: flowing to a new
        // place (maximise, tiling), growing in as it opens, sliding with its workspace.
        let outer = frame.outer();
        let morph_len = 0.30 / speed.max(0.01);
        let morph = look.morph.and_then(|(from, start)| {
            let t = now.saturating_duration_since(start).as_secs_f64() / morph_len;
            (t < 1.0 && from != outer).then(|| crate::layout::lerp(from, outer, crate::anim::ease_out_cubic(t)))
        });
        if morph.is_none() {
            look.morph = None;
        }
        animating |= morph.is_some();
        let (mut origin_pt, mut sx, mut sy, mut dx, mut dy): (Point<i32, Logical>, f64, f64, f64, f64) = (
            Point::<i32, Logical>::from((outer.x + outer.w / 2, outer.y + outer.h / 2)),
            zoom,
            zoom,
            0.0,
            0.0,
        );
        if let Some((ix, iy, iw, ih)) = morph {
            origin_pt = (outer.x, outer.y).into();
            sx = iw / outer.w.max(1) as f64;
            sy = ih / outer.h.max(1) as f64;
            dx = ix - outer.x as f64;
            dy = iy - outer.y as f64;
        }
        dx += slide;
        let identity = (sx - 1.0).abs() < 1e-3 && (sy - 1.0).abs() < 1e-3 && dx.abs() < 0.5 && dy.abs() < 0.5;
        if identity {
            out.extend(parts.into_iter().map(OziElement::Part));
        } else {
            let o = (origin_pt - origin).to_physical_precise_round(scale);
            let offset = Point::<f64, Logical>::from((dx, dy)).to_physical(scale).to_i32_round();
            out.extend(parts.into_iter().map(|p| {
                OziElement::Moved(RelocateRenderElement::from_element(
                    RescaleRenderElement::from_element(p, o, Scale::from((sx, sy))),
                    offset,
                    Relocate::Relative,
                ))
            }));
        }
    }
    (out, animating)
}

/// Layer surfaces (bar, dock, wallpaper...) of the given layers, top-most first.
fn layer_elements(
    output: &smithay::output::Output,
    renderer: &mut GlesRenderer,
    scale: f64,
    layers: &[smithay::wayland::shell::wlr_layer::Layer],
) -> Vec<OziElement> {
    let map = smithay::desktop::layer_map_for_output(output);
    let mut out = Vec::new();
    for layer in layers {
        for surface in map.layers_on(*layer).rev() {
            let Some(geo) = map.layer_geometry(surface) else {
                continue;
            };
            // Layer geometry is already relative to its output.
            let loc = geo.loc.to_physical_precise_round(scale);
            let parts: Vec<WaylandSurfaceRenderElement<GlesRenderer>> =
                surface.render_elements(renderer, loc, Scale::from(scale), 1.0);
            out.extend(parts.into_iter().map(|p| OziElement::Part(WindowPart::Plain(p))));
        }
    }
    out
}

/// The whole picture for one output, top-most first. The flag says whether
/// something is moving, so the backend knows to keep drawing.
pub fn output_elements(
    state: &mut OziWm,
    renderer: &mut GlesRenderer,
    shaders: &Shaders,
    output: &smithay::output::Output,
    now: Instant,
) -> (Vec<OziElement>, bool) {
    use smithay::wayland::shell::wlr_layer::Layer;
    let scale = output.current_scale().fractional_scale();
    let geo = state.space.output_geometry(output).unwrap_or_default();
    let origin = geo.loc;
    if state.lock.is_some() {
        // Locked: nothing but the lock screen, which keeps moving gently.
        return (state.lock_elements(renderer, &shaders.lock, (geo.size.w, geo.size.h), scale, now), true);
    }
    let mut out = layer_elements(output, renderer, scale, &[Layer::Overlay, Layer::Top]);
    let (windows, animating) = window_elements(state, renderer, shaders, origin, scale, now);
    out.extend(windows);
    out.extend(layer_elements(output, renderer, scale, &[Layer::Bottom, Layer::Background]));
    (out, animating)
}
