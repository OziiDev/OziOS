//! OziOS window frames: geometry and hit testing. Pure: tested without a compositor.
//!
//! A framed window is its content plus a title bar above it. Windows that draw
//! their own title bar (GTK) get no bar, only the border, glow and shadow.

use crate::grabs::resize_grab::Edges;

/// Logical pixels.
pub const TITLE_HEIGHT: i32 = 34;
pub const RADIUS: f32 = 12.0;
pub const BORDER: f32 = 2.0;
/// Room around the frame for the glow and the shadow.
pub const MARGIN: i32 = 44;
/// How far outside the frame the pointer can grab an edge.
pub const GRIP: i32 = 8;
pub const BUTTON: i32 = 14;
pub const BUTTON_GAP: i32 = 10;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub w: i32,
    pub h: i32,
}

impl Rect {
    pub const fn new(x: i32, y: i32, w: i32, h: i32) -> Self {
        Rect { x, y, w, h }
    }

    pub fn contains(&self, px: f64, py: f64) -> bool {
        px >= self.x as f64
            && py >= self.y as f64
            && px < (self.x + self.w) as f64
            && py < (self.y + self.h) as f64
    }

    pub fn grow(&self, by: i32) -> Rect {
        Rect::new(self.x - by, self.y - by, self.w + 2 * by, self.h + 2 * by)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Button {
    Minimize,
    Maximize,
    Close,
}

pub const BUTTONS: [Button; 3] = [Button::Minimize, Button::Maximize, Button::Close];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hit {
    Title,
    Button(Button),
    Edge(Edges),
}

/// Everything the frame occupies, from the window's content rectangle.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Frame {
    pub content: Rect,
    pub titled: bool,
}

impl Frame {
    pub fn new(content: Rect, titled: bool) -> Self {
        Frame { content, titled }
    }

    pub fn title_height(&self) -> i32 {
        if self.titled { TITLE_HEIGHT } else { 0 }
    }

    /// Content plus title bar: the rounded shape the border follows.
    pub fn outer(&self) -> Rect {
        let t = self.title_height();
        Rect::new(self.content.x, self.content.y - t, self.content.w, self.content.h + t)
    }

    pub fn title_bar(&self) -> Option<Rect> {
        self.titled
            .then(|| Rect::new(self.content.x, self.content.y - TITLE_HEIGHT, self.content.w, TITLE_HEIGHT))
    }

    /// Buttons sit on the right, close last, vertically centred in the bar.
    pub fn button_rect(&self, button: Button) -> Option<Rect> {
        let bar = self.title_bar()?;
        let index = BUTTONS.iter().position(|b| *b == button)? as i32;
        let from_right = BUTTONS.len() as i32 - 1 - index;
        let x = bar.x + bar.w - 14 - BUTTON - from_right * (BUTTON + BUTTON_GAP);
        let y = bar.y + (TITLE_HEIGHT - BUTTON) / 2;
        Some(Rect::new(x, y, BUTTON, BUTTON))
    }

    /// The area the shader element covers.
    pub fn render_area(&self) -> Rect {
        self.outer().grow(MARGIN)
    }

    /// What is under the pointer, outside the client's own surfaces.
    pub fn hit(&self, px: f64, py: f64) -> Option<Hit> {
        let outer = self.outer();
        if !outer.grow(GRIP).contains(px, py) {
            return None;
        }
        if let Some(bar) = self.title_bar()
            && bar.contains(px, py) {
                for button in BUTTONS {
                    // A little larger than drawn, so it is easy to hit.
                    if self.button_rect(button).is_some_and(|r| r.grow(4).contains(px, py)) {
                        return Some(Hit::Button(button));
                    }
                }
                // The top few pixels of the bar still resize, like any edge.
                if py >= (bar.y + 3) as f64 {
                    return Some(Hit::Title);
                }
            }
        let edges = Edges {
            left: px < outer.x as f64 + 3.0,
            right: px >= (outer.x + outer.w) as f64 - 3.0,
            top: py < outer.y as f64 + 3.0,
            bottom: py >= (outer.y + outer.h) as f64 - 3.0,
        };
        if edges != Edges::default() {
            return Some(Hit::Edge(edges));
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame() -> Frame {
        Frame::new(Rect::new(100, 100, 800, 600), true)
    }

    #[test]
    fn title_bar_sits_above_the_content() {
        assert_eq!(frame().title_bar(), Some(Rect::new(100, 66, 800, 34)));
        assert_eq!(frame().outer(), Rect::new(100, 66, 800, 634));
        assert_eq!(Frame::new(Rect::new(0, 0, 10, 10), false).title_bar(), None);
    }

    #[test]
    fn close_is_rightmost() {
        let f = frame();
        let close = f.button_rect(Button::Close).unwrap();
        let max = f.button_rect(Button::Maximize).unwrap();
        let min = f.button_rect(Button::Minimize).unwrap();
        assert!(min.x < max.x && max.x < close.x);
        assert_eq!(close.x + close.w, 900 - 14);
    }

    #[test]
    fn hits() {
        let f = frame();
        let c = f.button_rect(Button::Close).unwrap();
        assert_eq!(f.hit(c.x as f64 + 7.0, c.y as f64 + 7.0), Some(Hit::Button(Button::Close)));
        assert_eq!(f.hit(300.0, 80.0), Some(Hit::Title));
        assert_eq!(f.hit(500.0, 400.0), None, "content belongs to the client");
        assert_eq!(f.hit(2000.0, 80.0), None);
        let left = Edges { left: true, ..Default::default() };
        assert_eq!(f.hit(95.0, 400.0), Some(Hit::Edge(left)));
        let corner = Edges { right: true, bottom: true, ..Default::default() };
        assert_eq!(f.hit(905.0, 705.0), Some(Hit::Edge(corner)));
        let top = Edges { top: true, ..Default::default() };
        assert_eq!(f.hit(300.0, 67.0), Some(Hit::Edge(top)));
    }

    #[test]
    fn untitled_windows_only_have_edges() {
        let f = Frame::new(Rect::new(100, 100, 800, 600), false);
        assert_eq!(f.hit(300.0, 80.0), None);
        let top = Edges { top: true, ..Default::default() };
        assert_eq!(f.hit(300.0, 97.0), Some(Hit::Edge(top)));
    }
}
