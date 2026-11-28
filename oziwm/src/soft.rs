//! A screen without a GPU driver: the "safe graphics" boot entry (nomodeset,
//! simpledrm) or a virtual machine's plain VGA (bochs).
//!
//! GL then runs on the processor (llvmpipe). Drawing straight into the scanout
//! buffers, as on a real GPU, is very slow there: on bochs they sit in video
//! memory, which the processor reads at a crawl, and llvmpipe reads every tile
//! it blends. A frame took 250-800 ms and the desktop seemed to hang.
//!
//! So the frame is drawn into a texture in ordinary memory, and only the parts
//! that changed are copied into one of two dumb buffers, which is then flipped
//! onto the screen.

use smithay::{
    backend::{
        allocator::Fourcc,
        drm::{DrmSurface, PlaneConfig, PlaneDamageClips, PlaneState},
        renderer::{
            damage::OutputDamageTracker,
            element::RenderElement,
            gles::{ffi, GlesRenderer, GlesTexture},
            Bind, Frame, Offscreen, Renderer,
        },
    },
    output::Output,
    reexports::drm::{
        buffer::Buffer as _,
        control::{dumbbuffer::DumbBuffer, framebuffer, Device as ControlDevice},
    },
    utils::{Buffer as BufferCoords, Physical, Rectangle, Size, Transform},
};

/// More changed rectangles than this are copied as their bounding box: one
/// read back is cheaper than many small ones.
const MAX_RECTS: usize = 8;

struct Scanout {
    dumb: DumbBuffer,
    fb: framebuffer::Handle,
    /// Mapped once for the buffer's whole life: mapping it again every frame
    /// faulted every page of video memory in again, which cost up to 300 ms.
    map: *mut u8,
    len: usize,
    /// What changed on screen since this buffer was last filled.
    damage: Vec<Rectangle<i32, Physical>>,
    /// Fill all of it (new, or the screen came back from another console).
    full: bool,
}

pub struct SoftScreen {
    surface: DrmSurface,
    size: Size<i32, Physical>,
    /// Two, so one is on screen while the other is filled.
    buffers: Vec<Scanout>,
    /// The buffer that is not on screen, to fill next.
    back: usize,
    canvas: GlesTexture,
    /// The canvas's layout as read back: `Argb8888` is the scanout layout,
    /// `Abgr8888` needs red and blue swapped.
    read_format: Fourcc,
    tracker: OutputDamageTracker,
    /// The first frame, or one after a console switch, sets the mode.
    modeset: bool,
}

#[derive(Debug)]
pub enum Shown {
    /// A frame went to the screen; a vblank event follows.
    Queued,
    /// Nothing changed.
    Nothing,
}

impl SoftScreen {
    pub fn new(
        surface: DrmSurface,
        renderer: &mut GlesRenderer,
        output: &Output,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let (w, h) = surface.pending_mode().size();
        let size = Size::<i32, Physical>::from((w as i32, h as i32));
        let mut buffers = Vec::with_capacity(2);
        for _ in 0..2 {
            let dumb = surface.create_dumb_buffer((w as u32, h as u32), Fourcc::Xrgb8888, 32)?;
            let mut dumb = dumb;
            let fb = surface.add_framebuffer(&dumb, 24, 32)?;
            let mut mapping = surface.map_dumb_buffer(&mut dumb)?;
            let (map, len) = (mapping.as_mut_ptr(), mapping.len());
            // Keep it mapped; Drop for SoftScreen unmaps it.
            std::mem::forget(mapping);
            buffers.push(Scanout { dumb, fb, map, len, damage: Vec::new(), full: true });
        }

        let buffer_size = Size::<i32, BufferCoords>::from((size.w, size.h));
        // The scanout layout, if llvmpipe draws into it; else plain RGBA.
        let (canvas, read_format) = match renderer.create_buffer(Fourcc::Argb8888, buffer_size) {
            Ok(texture) => (texture, Fourcc::Argb8888),
            Err(_) => (renderer.create_buffer(Fourcc::Abgr8888, buffer_size)?, Fourcc::Abgr8888),
        };

        Ok(SoftScreen {
            surface,
            size,
            buffers,
            back: 0,
            canvas,
            read_format,
            tracker: OutputDamageTracker::from_output(output),
            modeset: true,
        })
    }

    /// After a console switch the screen holds someone else's picture.
    pub fn reset(&mut self) {
        let _ = self.surface.reset_state();
        for buffer in &mut self.buffers {
            buffer.full = true;
            buffer.damage.clear();
        }
        self.modeset = true;
    }

    /// Draw `elements` (topmost first) and put the result on the screen.
    pub fn render<E: RenderElement<GlesRenderer>>(
        &mut self,
        renderer: &mut GlesRenderer,
        elements: &[E],
        background: [f32; 4],
    ) -> Result<Shown, Box<dyn std::error::Error>> {
        let mut target = renderer.bind(&mut self.canvas)?;
        // The canvas keeps its picture, so it is always one frame old.
        let result = self.tracker.render_output(renderer, &mut target, 1, elements, background)?;
        if let Some(damage) = result.damage {
            for buffer in &mut self.buffers {
                if !buffer.full {
                    buffer.damage.extend(damage.iter().copied());
                }
            }
        }

        let screen = Rectangle::from_size(self.size);
        let back = &mut self.buffers[self.back];
        let rects: Vec<Rectangle<i32, Physical>> = if back.full {
            vec![screen]
        } else {
            let rects: Vec<_> = back.damage.iter().filter_map(|r| r.intersection(screen)).collect();
            if rects.len() > MAX_RECTS {
                let bbox = rects.iter().skip(1).fold(rects[0], |a, b| a.merge(*b));
                vec![bbox]
            } else {
                rects
            }
        };
        if rects.is_empty() && !self.modeset {
            return Ok(Shown::Nothing);
        }

        let pitch = back.dumb.pitch() as usize;
        let swap = self.read_format == Fourcc::Abgr8888;
        {
            // SAFETY: mapped in `new` with this length, unmapped only in Drop.
            let map = unsafe { std::slice::from_raw_parts_mut(back.map, back.len) };
            // Read straight into the scanout buffer. Smithay's read back goes
            // through a pixel buffer object, which llvmpipe fills with a shader:
            // a whole screen took 250-350 ms that way, a few ms like this.
            let mut frame = renderer.render(&mut target, self.size, Transform::Normal)?;
            let error = frame.with_context(|gl| unsafe {
                gl.PixelStorei(ffi::PACK_ALIGNMENT, 4);
                if !swap {
                    gl.PixelStorei(ffi::PACK_ROW_LENGTH, (pitch / 4) as i32);
                }
                let mut rgba = Vec::new();
                for rect in &rects {
                    let (x, y, w, h) = (rect.loc.x, rect.loc.y, rect.size.w, rect.size.h);
                    if swap {
                        rgba.resize(w as usize * h as usize * 4, 0);
                        gl.ReadPixels(x, y, w, h, ffi::RGBA, ffi::UNSIGNED_BYTE, rgba.as_mut_ptr().cast());
                        copy_rect(map, pitch, &rgba, *rect, true);
                    } else {
                        let at = y as usize * pitch + x as usize * 4;
                        gl.ReadPixels(x, y, w, h, ffi::BGRA_EXT, ffi::UNSIGNED_BYTE, map[at..].as_mut_ptr().cast());
                    }
                }
                gl.PixelStorei(ffi::PACK_ROW_LENGTH, 0);
                gl.GetError()
            })?;
            let _ = frame.finish()?;
            if error != ffi::NO_ERROR {
                return Err(format!("reading the frame back failed: GL error {error:#x}").into());
            }
        }

        let src = Rectangle::<f64, BufferCoords>::from_size((self.size.w as f64, self.size.h as f64).into());
        let clips = PlaneDamageClips::from_damage(self.surface.device_fd(), src, screen, rects.iter().copied())
            .ok()
            .flatten();
        let plane = PlaneState {
            handle: self.surface.plane(),
            config: Some(PlaneConfig {
                src,
                dst: screen,
                transform: Transform::Normal,
                alpha: 1.0,
                damage_clips: clips.as_ref().map(|c| c.blob()),
                fb: back.fb,
                fence: None,
            }),
        };
        if self.modeset || self.surface.commit_pending() {
            self.surface.commit([plane], true)?;
            self.modeset = false;
        } else {
            self.surface.page_flip([plane], true)?;
        }
        let back = &mut self.buffers[self.back];
        back.full = false;
        back.damage.clear();
        self.back ^= 1;
        Ok(Shown::Queued)
    }
}

impl Drop for SoftScreen {
    fn drop(&mut self) {
        for buffer in self.buffers.drain(..) {
            // SAFETY: the mapping made in `new`; nothing uses it any more.
            unsafe { libc::munmap(buffer.map.cast(), buffer.len) };
            let _ = self.surface.destroy_framebuffer(buffer.fb);
            let _ = self.surface.destroy_dumb_buffer(buffer.dumb);
        }
    }
}

/// Copy tightly packed rows of `rect` into a mapped XRGB8888 buffer.
fn copy_rect(dst: &mut [u8], pitch: usize, src: &[u8], rect: Rectangle<i32, Physical>, swap_rb: bool) {
    let (x, y) = (rect.loc.x as usize, rect.loc.y as usize);
    let (w, h) = (rect.size.w as usize, rect.size.h as usize);
    let row = w * 4;
    for r in 0..h {
        let from = &src[r * row..(r + 1) * row];
        let at = (y + r) * pitch + x * 4;
        let to = &mut dst[at..at + row];
        if swap_rb {
            for (d, s) in to.chunks_exact_mut(4).zip(from.chunks_exact(4)) {
                d[0] = s[2];
                d[1] = s[1];
                d[2] = s[0];
                d[3] = 0xff;
            }
        } else {
            to.copy_from_slice(from);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn copies_a_rectangle_into_place() {
        // A 4x3 buffer with a pitch of 20 bytes (one pixel of padding per row).
        let mut dst = vec![0u8; 20 * 3];
        let src: Vec<u8> = (0..2 * 2 * 4).map(|i| i as u8 + 1).collect();
        copy_rect(&mut dst, 20, &src, Rectangle::new((1, 1).into(), (2, 2).into()), false);
        assert_eq!(&dst[0..20], &[0u8; 20]);
        assert_eq!(&dst[20 + 4..20 + 12], &src[0..8]);
        assert_eq!(&dst[40 + 4..40 + 12], &src[8..16]);
        assert_eq!(&dst[20..24], &[0u8; 4]);
    }

    #[test]
    fn swaps_red_and_blue_for_rgba() {
        let mut dst = vec![0u8; 4];
        copy_rect(&mut dst, 4, &[10, 20, 30, 40], Rectangle::new((0, 0).into(), (1, 1).into()), true);
        assert_eq!(dst, [30, 20, 10, 0xff]);
    }
}
