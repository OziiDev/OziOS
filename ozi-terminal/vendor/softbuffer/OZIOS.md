softbuffer 0.4.8 (MIT OR Apache-2.0, https://github.com/rust-windowing/softbuffer),
unchanged except one thing: on Wayland the buffer is Argb8888 instead of
Xrgb8888, so Ozi Terminal can be a little see-through. Callers must write
premultiplied alpha.
