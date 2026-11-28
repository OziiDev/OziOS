//! Real hardware: DRM/KMS on the primary GPU, a libseat session, libinput.
//!
//! On a laptop with two GPUs (Intel + NVIDIA) the screen hangs off the primary
//! one and everything is drawn there; the other GPU stays free for games.

use std::{
    collections::HashMap,
    path::Path,
    time::{Duration, Instant},
};

use smithay::{
    backend::{
        allocator::{
            gbm::{GbmAllocator, GbmBufferFlags, GbmDevice},
            Fourcc,
        },
        drm::{
            compositor::{DrmCompositor, FrameFlags},
            exporter::gbm::GbmFramebufferExporter,
            DrmDevice, DrmDeviceFd, DrmEvent, DrmNode,
        },
        egl::{EGLContext, EGLDisplay},
        input::InputEvent,
        libinput::{LibinputInputBackend, LibinputSessionInterface},
        renderer::{
            gles::{ffi, GlesRenderer},
            ImportDma,
        },
        session::{libseat::LibSeatSession, Event as SessionEvent, Session},
        udev::{primary_gpu, UdevBackend, UdevEvent},
    },
    output::{Mode as WlMode, Output, PhysicalProperties, Subpixel},
    reexports::{
        calloop::{
            timer::{TimeoutAction, Timer},
            EventLoop,
        },
        drm::control::{connector, crtc, Device as ControlDevice, ModeTypeFlags},
        input::{self as libinput, Libinput},
        rustix::fs::OFlags,
    },
    utils::{DeviceFd, Transform},
    wayland::dmabuf::DmabufFeedbackBuilder,
};

use crate::{
    cursor::Cursor,
    render::{self, Shaders},
    soft::{Shown, SoftScreen},
    OziWm,
};

/// OziOS ink, `#080B10`.
const BACKGROUND: [f32; 4] = [0.031, 0.043, 0.063, 1.0];

type Compositor =
    DrmCompositor<GbmAllocator<DrmDeviceFd>, GbmFramebufferExporter<DrmDeviceFd>, (), DrmDeviceFd>;

/// How frames reach a screen.
enum Scanout {
    /// A GPU draws straight into the buffers it shows.
    Gpu(Box<Compositor>),
    /// No GPU driver: drawn in memory, the changes copied to the screen.
    Soft(Box<SoftScreen>),
}

/// Without a vblank for this long, the last frame is taken as shown.
const VBLANK_TIMEOUT: Duration = Duration::from_millis(1000);

struct Screen {
    output: Output,
    connector: connector::Handle,
    scanout: Scanout,
    /// A frame is on its way to the screen; wait for its vblank.
    waiting: bool,
    /// When the frame we wait for was queued, to notice a vblank that never came.
    queued_at: Option<Instant>,
}

pub struct Tty {
    session: LibSeatSession,
    libinput: Libinput,
    drm: DrmDevice,
    gbm: GbmDevice<DrmDeviceFd>,
    node: DrmNode,
    renderer: GlesRenderer,
    /// GL runs on the processor (no GPU driver): see `soft`.
    software: bool,
    shaders: Shaders,
    cursor: Cursor,
    screens: HashMap<crtc::Handle, Screen>,
    /// Keyboards, to light their Caps/Num/Scroll Lock lights.
    keyboards: Vec<libinput::Device>,
}

pub fn init_tty(
    event_loop: &mut EventLoop<'static, OziWm>,
    state: &mut OziWm,
) -> Result<(), Box<dyn std::error::Error>> {
    let (session, notifier) = LibSeatSession::new()
        .map_err(|e| format!("no seat session (start oziwm from a login, not from a terminal inside another desktop): {e}"))?;
    let seat_name = session.seat();

    let path = primary_gpu(&seat_name)?
        .ok_or("no GPU found")?;
    tracing::info!(gpu = %path.display(), "primary GPU");
    let (drm, gbm, node, drm_notifier) = open_gpu(&session, &path)?;

    // SAFETY: the GBM device outlives the display: both are owned by Tty.
    let display = unsafe { EGLDisplay::new(gbm.clone())? };
    let context = EGLContext::new(&display)?;
    // SAFETY: the context is current on this thread only; the renderer owns it.
    let mut renderer = unsafe { GlesRenderer::new(context)? };
    let shaders = Shaders::compile(&mut renderer)?;
    let gl_name = renderer
        .with_context(|gl| unsafe {
            let name = gl.GetString(ffi::RENDERER);
            if name.is_null() {
                String::new()
            } else {
                std::ffi::CStr::from_ptr(name as *const _).to_string_lossy().into_owned()
            }
        })
        .unwrap_or_default();
    let software = match std::env::var("OZIWM_RENDER").as_deref() {
        Ok("software") => true,
        Ok("gpu") => false,
        _ => !node.has_render() || is_software_gl(&gl_name),
    };
    tracing::info!(gl = %gl_name, software, "renderer");

    // GPU-rendered clients (browsers, games, Qt Quick) share buffers through
    // linux-dmabuf. Without a GPU they draw on the processor and hand over
    // plain memory; their dmabufs would live in video memory, which llvmpipe
    // reads very slowly.
    if !software {
        let formats = renderer.dmabuf_formats();
        let feedback = DmabufFeedbackBuilder::new(node.dev_id(), formats.clone()).build()?;
        state
            .dmabuf_state
            .create_global_with_default_feedback::<OziWm>(&state.display_handle, &feedback);
    }

    let mut libinput = Libinput::new_with_udev(LibinputSessionInterface::from(session.clone()));
    libinput
        .udev_assign_seat(&seat_name)
        .map_err(|_| "libinput could not take the seat")?;
    let input_backend = LibinputInputBackend::new(libinput.clone());

    state.nested = false;
    state.session = Some(session.clone());

    let mut tty = Tty {
        session,
        libinput,
        drm,
        gbm,
        node,
        renderer,
        software,
        shaders,
        cursor: Cursor::load(),
        screens: HashMap::new(),
        keyboards: Vec::new(),
    };
    tty.scan_connectors(state);
    if tty.screens.is_empty() {
        return Err("no connected screen".into());
    }
    state.tty = Some(tty);

    let handle = event_loop.handle();

    handle.insert_source(input_backend, |mut event, _, state| {
        match &mut event {
            InputEvent::DeviceAdded { device } => {
                configure_device(device);
                if device.has_capability(libinput::DeviceCapability::Touch)
                    || device.has_capability(libinput::DeviceCapability::TabletTool)
                {
                    state.touch_device_added();
                }
                if device.has_capability(libinput::DeviceCapability::Keyboard) {
                    if let Some(tty) = state.tty.as_mut() {
                        tty.keyboards.push(device.clone());
                    }
                    state.update_leds();
                }
            }
            InputEvent::DeviceRemoved { device } => {
                if let Some(tty) = state.tty.as_mut() {
                    tty.keyboards.retain(|k| k != device);
                }
            }
            _ => {}
        }
        state.process_input_event(event);
        state.needs_redraw = true;
    })?;

    handle.insert_source(notifier, |event, _, state| match event {
        SessionEvent::PauseSession => {
            tracing::info!("session paused (switched away)");
            if let Some(tty) = state.tty.as_mut() {
                tty.libinput.suspend();
                tty.drm.pause();
            }
        }
        SessionEvent::ActivateSession => {
            tracing::info!("session active again");
            if let Some(tty) = state.tty.as_mut() {
                if tty.libinput.resume().is_err() {
                    tracing::warn!("libinput did not resume");
                }
                if let Err(err) = tty.drm.activate(false) {
                    tracing::warn!(?err, "DRM did not come back");
                }
                for screen in tty.screens.values_mut() {
                    match &mut screen.scanout {
                        Scanout::Gpu(compositor) => {
                            let _ = compositor.reset_state();
                        }
                        Scanout::Soft(soft) => soft.reset(),
                    }
                    screen.waiting = false;
                }
            }
            state.needs_redraw = true;
            render_all(state);
        }
    })?;

    handle.insert_source(drm_notifier, |event, _, state| match event {
        DrmEvent::VBlank(crtc) => {
            if let Some(tty) = state.tty.as_mut()
                && let Some(screen) = tty.screens.get_mut(&crtc) {
                    screen.waiting = false;
                    screen.queued_at = None;
                    if let Scanout::Gpu(compositor) = &mut screen.scanout
                        && let Err(err) = compositor.frame_submitted() {
                            tracing::warn!(?err, "frame_submitted failed");
                        }
                }
            if state.needs_redraw {
                render_all(state);
            }
        }
        DrmEvent::Error(err) => tracing::warn!(?err, "DRM error"),
    })?;

    // Screens plugged in or out.
    let udev = UdevBackend::new(&seat_name)?;
    handle.insert_source(udev, move |event, _, state| {
        if let UdevEvent::Changed { device_id } = event {
            let Some(mut tty) = state.tty.take() else {
                return;
            };
            if tty.node.dev_id() == device_id {
                tty.scan_connectors(state);
            }
            state.tty = Some(tty);
            state.needs_redraw = true;
        }
    })?;

    // Idle-friendly pacing: look ~60 times a second, draw only when something changed.
    handle.insert_source(Timer::from_duration(Duration::from_millis(16)), |_, _, state| {
        if state.needs_redraw {
            render_all(state);
        }
        TimeoutAction::ToDuration(Duration::from_millis(16))
    })?;

    state.needs_redraw = true;
    Ok(())
}

fn open_gpu(
    session: &LibSeatSession,
    path: &Path,
) -> Result<
    (DrmDevice, GbmDevice<DrmDeviceFd>, DrmNode, smithay::backend::drm::DrmDeviceNotifier),
    Box<dyn std::error::Error>,
> {
    let mut session = session.clone();
    let fd = session.open(
        path,
        OFlags::RDWR | OFlags::CLOEXEC | OFlags::NOCTTY | OFlags::NONBLOCK,
    )?;
    let fd = DrmDeviceFd::new(DeviceFd::from(fd));
    let node = DrmNode::from_file(fd.clone())?;
    let (drm, notifier) = DrmDevice::new(fd.clone(), true)?;
    let gbm = GbmDevice::new(fd)?;
    Ok((drm, gbm, node, notifier))
}

/// Mesa's renderers that run on the processor.
fn is_software_gl(name: &str) -> bool {
    let name = name.to_ascii_lowercase();
    ["llvmpipe", "softpipe", "swrast", "software rasterizer"].iter().any(|s| name.contains(s))
}

/// Tap to click and natural feel on touchpads: what people coming from a phone expect.
fn configure_device(device: &mut libinput::Device) {
    if device.config_tap_finger_count() > 0 {
        let _ = device.config_tap_set_enabled(true);
        let _ = device.config_tap_set_drag_enabled(true);
        let _ = device.config_dwt_set_enabled(true);
    }
    if device.config_scroll_has_natural_scroll() && device.config_tap_finger_count() > 0 {
        let _ = device.config_scroll_set_natural_scroll_enabled(true);
    }
}

impl Tty {
    /// Show the lock states on every keyboard's lights.
    pub fn set_leds(&mut self, leds: libinput::Led) {
        for keyboard in &mut self.keyboards {
            keyboard.led_update(leds);
        }
    }

    /// Light up every connected screen that has no output yet, and drop the
    /// ones that were unplugged. Screens are placed left to right.
    fn scan_connectors(&mut self, state: &mut OziWm) {
        let Ok(resources) = self.drm.resource_handles() else {
            tracing::warn!("could not read DRM resources");
            return;
        };

        // Unplugged screens.
        let gone: Vec<crtc::Handle> = self
            .screens
            .iter()
            .filter(|(_, s)| {
                self.drm
                    .get_connector(s.connector, false)
                    .map(|c| c.state() != connector::State::Connected)
                    .unwrap_or(true)
            })
            .map(|(c, _)| *c)
            .collect();
        for crtc in gone {
            if let Some(screen) = self.screens.remove(&crtc) {
                tracing::info!(output = %screen.output.name(), "screen unplugged");
                state.space.unmap_output(&screen.output);
            }
        }

        for &handle in resources.connectors() {
            if self.screens.values().any(|s| s.connector == handle) {
                continue;
            }
            let Ok(info) = self.drm.get_connector(handle, false) else {
                continue;
            };
            if info.state() != connector::State::Connected {
                continue;
            }
            let Some(&mode) = info
                .modes()
                .iter()
                .find(|m| m.mode_type().contains(ModeTypeFlags::PREFERRED))
                .or_else(|| info.modes().first())
            else {
                continue;
            };
            let used: Vec<crtc::Handle> = self.screens.keys().copied().collect();
            let Some(crtc) = info
                .encoders()
                .iter()
                .filter_map(|e| self.drm.get_encoder(*e).ok())
                .flat_map(|enc| resources.filter_crtcs(enc.possible_crtcs()))
                .find(|c| !used.contains(c))
            else {
                tracing::warn!("no free CRTC for a connector");
                continue;
            };
            let name = format!("{}-{}", info.interface().as_str(), info.interface_id());
            match self.light_up(state, handle, crtc, mode, &name, info.size()) {
                Ok(screen) => {
                    tracing::info!(output = %name, w = mode.size().0, h = mode.size().1, "screen on");
                    self.screens.insert(crtc, screen);
                }
                Err(err) => tracing::warn!(output = %name, %err, "could not use screen"),
            }
        }
    }

    fn light_up(
        &mut self,
        state: &mut OziWm,
        connector: connector::Handle,
        crtc: crtc::Handle,
        mode: smithay::reexports::drm::control::Mode,
        name: &str,
        size_mm: Option<(u32, u32)>,
    ) -> Result<Screen, Box<dyn std::error::Error>> {
        let surface = self.drm.create_surface(crtc, mode, &[connector])?;
        let (w_mm, h_mm) = size_mm.unwrap_or((0, 0));
        let output = Output::new(
            name.to_string(),
            PhysicalProperties {
                size: (w_mm as i32, h_mm as i32).into(),
                subpixel: Subpixel::Unknown,
                make: "OziOS".into(),
                model: name.to_string(),
            },
        );
        let wl_mode = WlMode::from(mode);
        // Next to the screens already in use.
        let x = state
            .space
            .outputs()
            .filter_map(|o| state.space.output_geometry(o))
            .map(|g| g.loc.x + g.size.w)
            .max()
            .unwrap_or(0);
        output.change_current_state(Some(wl_mode), Some(Transform::Normal), None, Some((x, 0).into()));
        output.set_preferred(wl_mode);
        let _global = output.create_global::<OziWm>(&state.display_handle);
        state.space.map_output(&output, (x, 0));

        if self.software {
            let soft = SoftScreen::new(surface, &mut self.renderer, &output)?;
            return Ok(Screen { output, connector, scanout: Scanout::Soft(Box::new(soft)), waiting: false, queued_at: None });
        }
        let allocator = GbmAllocator::new(self.gbm.clone(), GbmBufferFlags::RENDERING | GbmBufferFlags::SCANOUT);
        let exporter = GbmFramebufferExporter::new(self.gbm.clone(), Some(self.node));
        let compositor = DrmCompositor::new(
            &output,
            surface,
            None,
            allocator,
            exporter,
            [Fourcc::Argb8888, Fourcc::Xrgb8888],
            self.renderer.dmabuf_formats(),
            self.drm.cursor_size(),
            Some(self.gbm.clone()),
        )?;
        Ok(Screen { output, connector, scanout: Scanout::Gpu(Box::new(compositor)), waiting: false, queued_at: None })
    }

    pub fn import_dmabuf(&mut self, dmabuf: &smithay::backend::allocator::dmabuf::Dmabuf) -> bool {
        self.renderer.import_dmabuf(dmabuf, None).is_ok()
    }

    pub fn change_vt(&mut self, vt: i32) {
        if let Err(err) = self.session.change_vt(vt) {
            tracing::warn!(?err, vt, "could not switch to that console");
        }
    }
}

/// Draw every screen that is not still waiting for its previous frame.
pub fn render_all(state: &mut OziWm) {
    let Some(mut tty) = state.tty.take() else {
        return;
    };
    if !tty.session.is_active() {
        state.tty = Some(tty);
        return;
    }
    let now = Instant::now();
    let mut still_moving = false;
    let crtcs: Vec<crtc::Handle> = tty.screens.keys().copied().collect();
    for crtc in crtcs {
        let Some(screen) = tty.screens.get(&crtc) else {
            continue;
        };
        // A vblank that never arrives must not freeze the screen until the pointer moves.
        // Not too eager: a slow machine delivers the event late, and drawing
        // over a flip the kernel still holds fails with "busy".
        if screen.waiting && screen.queued_at.is_some_and(|t| now.duration_since(t) > VBLANK_TIMEOUT) {
            tracing::warn!(output = %screen.output.name(), "no vblank for the last frame; drawing again");
            if let Some(screen) = tty.screens.get_mut(&crtc) {
                screen.waiting = false;
                screen.queued_at = None;
                if let Scanout::Gpu(compositor) = &mut screen.scanout {
                    let _ = compositor.frame_submitted();
                }
            }
        }
        let Some(screen) = tty.screens.get(&crtc) else {
            continue;
        };
        if screen.waiting {
            still_moving = true;
            continue;
        }
        let output = screen.output.clone();
        let origin = state.space.output_geometry(&output).map(|g| g.loc).unwrap_or_default();
        let scale = output.current_scale().fractional_scale();

        let pointer = state.seat.get_pointer().map(|p| p.current_location()).unwrap_or_default();
        let on_this_screen = state
            .space
            .output_geometry(&output)
            .is_some_and(|g| g.to_f64().contains(pointer));
        let mut elements = if on_this_screen {
            tty.cursor
                .elements(&mut tty.renderer, &state.cursor_status, pointer - origin.to_f64(), scale)
        } else {
            Vec::new()
        };
        let (scene, animating) = render::output_elements(state, &mut tty.renderer, &tty.shaders, &output, now);
        still_moving |= animating;
        let cursor_count = elements.len();
        elements.extend(scene);
        let started = Instant::now();

        let Some(screen) = tty.screens.get_mut(&crtc) else {
            continue;
        };
        match &mut screen.scanout {
            Scanout::Gpu(compositor) => {
                match compositor.render_frame(&mut tty.renderer, &elements, BACKGROUND, FrameFlags::DEFAULT) {
                    Ok(result) if !result.is_empty => match compositor.queue_frame(()) {
                        Ok(()) => {
                            screen.waiting = true;
                            screen.queued_at = Some(Instant::now());
                        }
                        Err(err) => tracing::warn!(?err, "could not queue frame"),
                    },
                    Ok(_) => {}
                    Err(err) => tracing::warn!(?err, "rendering failed"),
                }
            }
            Scanout::Soft(soft) => match soft.render(&mut tty.renderer, &elements, BACKGROUND) {
                Ok(Shown::Queued) => {
                    screen.waiting = true;
                    screen.queued_at = Some(Instant::now());
                }
                Ok(Shown::Nothing) => {}
                Err(err) => {
                    // Most likely the previous flip is still pending; try again shortly.
                    tracing::warn!(%err, "software frame not shown");
                    still_moving = true;
                }
            },
        }
        let took = started.elapsed().as_secs_f32() * 1000.0;
        state.stats.record(took);
        // On the processor a frame takes longer; only warn about the stalls.
        if took > if tty.software { 150.0 } else { 20.0 } {
            tracing::warn!(output = %output.name(), ms = took, "slow frame");
        }
        // A screenshot of this screen without the pointer.
        if let Some(shot) = state.pending_shot.take() {
            let size = output.current_mode().map(|m| m.size).unwrap_or_default();
            let result = crate::shot::capture(&mut tty.renderer, &elements[cursor_count..], size, scale);
            state.finish_screenshot(shot, result, (size.w as u32, size.h as u32));
        }

        let elapsed = state.start_time.elapsed();
        for window in state.space.elements() {
            window.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
        }
        for layer in smithay::desktop::layer_map_for_output(&output).layers() {
            layer.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
        }
    }
    state.space.refresh();
    for output in state.space.outputs() {
        smithay::desktop::layer_map_for_output(output).cleanup();
    }
    state.popups.cleanup();
    let _ = state.display_handle.flush_clients();
    state.needs_redraw = still_moving;
    state.tty = Some(tty);
}

#[cfg(test)]
mod tests {
    use super::is_software_gl;

    #[test]
    fn tells_processor_gl_from_a_gpu() {
        assert!(is_software_gl("llvmpipe (LLVM 22.1.8, 256 bits)"));
        assert!(is_software_gl("softpipe"));
        assert!(!is_software_gl("Mesa Intel(R) UHD Graphics 620 (KBL GT2)"));
        assert!(!is_software_gl("AMD Radeon RX 6600 (radeonsi, navi23, LLVM 20.1.0)"));
    }
}
