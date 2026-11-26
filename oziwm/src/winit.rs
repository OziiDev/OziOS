//! Nested backend: oziwm runs as a window inside the current desktop.

use std::time::{Duration, Instant};

use smithay::{
    backend::{
        renderer::{
            damage::OutputDamageTracker,
            gles::GlesRenderer,
        },
        winit::{self, WinitEvent},
    },
    output::{Mode, Output, PhysicalProperties, Subpixel},
    reexports::calloop::EventLoop,
    utils::Transform,
};

use crate::{
    render::{self, Shaders},
    OziWm,
};

/// OziOS ink, `#080B10`.
const BACKGROUND: [f32; 4] = [0.031, 0.043, 0.063, 1.0];

pub fn init_winit(
    event_loop: &mut EventLoop<'static, OziWm>,
    state: &mut OziWm,
) -> Result<(), Box<dyn std::error::Error>> {
    // OZIWM_NESTED_SIZE=1600x900 opens the window at that size (screenshots, videos).
    let size = std::env::var("OZIWM_NESTED_SIZE").ok().and_then(|s| {
        let (w, h) = s.split_once('x')?;
        Some((w.trim().parse::<f64>().ok()?, h.trim().parse::<f64>().ok()?))
    });
    let (backend, winit) = match size {
        Some((w, h)) => winit::init_from_attributes::<GlesRenderer>(
            smithay::reexports::winit::window::WindowAttributes::default()
                .with_inner_size(smithay::reexports::winit::dpi::LogicalSize::new(w, h))
                .with_title("oziwm")
                .with_visible(true),
        )?,
        None => winit::init::<GlesRenderer>()?,
    };
    let backend = std::rc::Rc::new(std::cell::RefCell::new(backend));
    state.winit = Some(backend.clone());
    let mut backend_ref = backend.borrow_mut();
    backend_ref.window().set_title("OziOS (oziwm)");

    let mode = Mode {
        size: backend_ref.window_size(),
        refresh: 60_000,
    };
    let output = Output::new(
        "winit".to_string(),
        PhysicalProperties {
            size: (0, 0).into(),
            subpixel: Subpixel::Unknown,
            make: "OziOS".into(),
            model: "nested".into(),
        },
    );
    let _global = output.create_global::<OziWm>(&state.display_handle);
    output.change_current_state(Some(mode), Some(Transform::Flipped180), None, Some((0, 0).into()));
    output.set_preferred(mode);
    state.space.map_output(&output, (0, 0));
    state.nested = true;

    let mut damage_tracker = OutputDamageTracker::from_output(&output);
    let shaders = Shaders::compile(backend_ref.renderer())?;
    // Like on real hardware: GPU clients hand over their buffers as dmabufs.
    {
        use smithay::backend::renderer::ImportDma;
        let formats = backend_ref.renderer().dmabuf_formats();
        state.dmabuf_state.create_global::<OziWm>(&state.display_handle, formats);
    }
    drop(backend_ref);

    event_loop.handle().insert_source(winit, move |event, _, state| match event {
        WinitEvent::Resized { size, .. } => {
            let mode = Mode { size, refresh: 60_000 };
            output.change_current_state(Some(mode), None, None, None);
            output.set_preferred(mode);
            state.space.map_output(&output, (0, 0));
            smithay::desktop::layer_map_for_output(&output).arrange();
        }
        WinitEvent::Input(event) => state.process_input_event(event),
        WinitEvent::Redraw => {
            let mut backend = backend.borrow_mut();
            let size = backend.window_size();
            let age = backend.buffer_age().unwrap_or(0);
            let started = Instant::now();
            let mut drawn = Vec::new();
            let damage = match backend.bind() {
                Ok((renderer, mut framebuffer)) => {
                    let (elements, _animating) =
                        render::output_elements(state, renderer, &shaders, &output, Instant::now());
                    let result = damage_tracker.render_output(renderer, &mut framebuffer, age, &elements, BACKGROUND);
                    drawn = elements;
                    match result {
                        Ok(result) => result.damage.cloned(),
                        Err(err) => {
                            tracing::warn!(?err, "rendering failed");
                            None
                        }
                    }
                }
                Err(err) => {
                    tracing::warn!(?err, "could not bind the window");
                    None
                }
            };
            let full = [smithay::utils::Rectangle::from_size(size)];
            let submit = match &damage {
                Some(rects) if !rects.is_empty() => backend.submit(Some(rects)),
                // Nothing changed; still swap so the host keeps pacing us at its refresh rate.
                _ => backend.submit(Some(&full)),
            };
            if let Err(err) = submit {
                tracing::warn!(?err, "could not show the frame");
            }
            state.stats.record(started.elapsed().as_secs_f32() * 1000.0);
            if let Some(shot) = state.pending_shot.take() {
                let scale = output.current_scale().fractional_scale();
                let result = crate::shot::capture(backend.renderer(), &drawn, size, scale);
                state.finish_screenshot(shot, result, (size.w as u32, size.h as u32));
            }
            drop(drawn);

            let elapsed = state.start_time.elapsed();
            for window in state.space.elements() {
                window.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
            }
            for layer in smithay::desktop::layer_map_for_output(&output).layers() {
                layer.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
            }
            state.space.refresh();
            smithay::desktop::layer_map_for_output(&output).cleanup();
            state.popups.cleanup();
            let _ = state.display_handle.flush_clients();
            backend.window().request_redraw();
        }
        WinitEvent::CloseRequested => state.loop_signal.stop(),
        WinitEvent::Focus(_) => {}
    })?;

    Ok(())
}
