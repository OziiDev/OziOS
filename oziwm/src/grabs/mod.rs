mod move_grab;
pub mod resize_grab;

pub use move_grab::MoveSurfaceGrab;
pub use resize_grab::ResizeSurfaceGrab;

/// Linux input code of the left mouse button.
pub const BTN_LEFT: u32 = 0x110;
