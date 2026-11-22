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
    let (mut backend, winit) = winit::init::<GlesRenderer>()?;
    backend.window().set_title("OziOS (oziwm)");

    let mode = Mode {
        size: backend.window_size(),
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
    let shaders = Shaders::compile(backend.renderer())?;

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
            let size = backend.window_size();
            let age = backend.buffer_age().unwrap_or(0);
            let damage = match backend.bind() {
                Ok((renderer, mut framebuffer)) => {
                    let (elements, _animating) =
                        render::output_elements(state, renderer, &shaders, &output, Instant::now());
                    match damage_tracker.render_output(renderer, &mut framebuffer, age, &elements, BACKGROUND) {
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

            let elapsed = state.start_time.elapsed();
            for window in state.space.elements() {
                window.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
            }
            for layer in smithay::desktop::layer_map_for_output(&output).layers() {
                layer.send_frame(&output, elapsed, Some(Duration::ZERO), |_, _| Some(output.clone()));
            }
            state.space.refresh();
            state.popups.cleanup();
            let _ = state.display_handle.flush_clients();
            backend.window().request_redraw();
        }
        WinitEvent::CloseRequested => state.loop_signal.stop(),
        WinitEvent::Focus(_) => {}
    })?;

    Ok(())
}
