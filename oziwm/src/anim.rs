//! Motion curves. Pure: tested without a compositor.

use std::time::{Duration, Instant};

/// A critically under-damped spring from 0 to 1: a quick rise, a small
/// overshoot, then rest. `t` is seconds since the start.
pub fn spring(t: f64, stiffness: f64, damping_ratio: f64) -> f64 {
    if t <= 0.0 {
        return 0.0;
    }
    let omega = stiffness.sqrt();
    let zeta = damping_ratio.clamp(0.05, 0.999);
    let omega_d = omega * (1.0 - zeta * zeta).sqrt();
    let decay = (-zeta * omega * t).exp();
    1.0 - decay * ((omega_d * t).cos() + (zeta * omega / omega_d) * (omega_d * t).sin())
}

pub fn ease_out_cubic(x: f64) -> f64 {
    let x = x.clamp(0.0, 1.0);
    1.0 - (1.0 - x).powi(3)
}

/// A value moving towards a target over time, for things like the focus glow.
#[derive(Debug, Clone, Copy)]
pub struct Fade {
    from: f64,
    to: f64,
    start: Instant,
    duration: Duration,
}

impl Fade {
    pub fn new(value: f64) -> Self {
        Fade { from: value, to: value, start: Instant::now(), duration: Duration::ZERO }
    }

    pub fn value_at(&self, now: Instant) -> f64 {
        if self.duration.is_zero() {
            return self.to;
        }
        let x = now.saturating_duration_since(self.start).as_secs_f64() / self.duration.as_secs_f64();
        self.from + (self.to - self.from) * ease_out_cubic(x)
    }

    pub fn target(&self) -> f64 {
        self.to
    }

    pub fn set(&mut self, to: f64, duration: Duration, now: Instant) {
        if (to - self.to).abs() < f64::EPSILON {
            return;
        }
        self.from = self.value_at(now);
        self.to = to;
        self.start = now;
        self.duration = duration;
    }

    pub fn running(&self, now: Instant) -> bool {
        now.saturating_duration_since(self.start) < self.duration
    }
}

/// How a window arrives: grows from 90% with a small overshoot and fades in.
#[derive(Debug, Clone, Copy)]
pub struct Opening {
    pub start: Instant,
}

impl Opening {
    pub const LENGTH: Duration = Duration::from_millis(420);

    /// (scale, alpha), or None once finished.
    pub fn at(&self, now: Instant, speed: f64) -> Option<(f64, f64)> {
        if speed <= 0.0 {
            return None;
        }
        let t = now.saturating_duration_since(self.start).as_secs_f64() * speed;
        if t >= Self::LENGTH.as_secs_f64() {
            return None;
        }
        let s = spring(t, 260.0, 0.62);
        let scale = 0.90 + 0.10 * s;
        let alpha = ease_out_cubic(t / 0.18);
        Some((scale, alpha))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spring_starts_at_zero_and_settles_at_one() {
        assert_eq!(spring(0.0, 260.0, 0.62), 0.0);
        assert!((spring(2.0, 260.0, 0.62) - 1.0).abs() < 1e-3);
    }

    #[test]
    fn spring_overshoots_a_little() {
        let peak = (1..400).map(|i| spring(i as f64 / 1000.0, 260.0, 0.62)).fold(0.0, f64::max);
        assert!(peak > 1.0 && peak < 1.12, "peak {peak}");
    }

    #[test]
    fn opening_ends_and_can_be_turned_off() {
        let start = Instant::now();
        let o = Opening { start };
        let (scale, alpha) = o.at(start, 1.0).unwrap();
        assert!((scale - 0.90).abs() < 1e-9 && alpha == 0.0);
        assert!(o.at(start + Duration::from_secs(1), 1.0).is_none());
        assert!(o.at(start, 0.0).is_none());
    }

    #[test]
    fn fade_moves_and_stops() {
        let now = Instant::now();
        let mut f = Fade::new(0.0);
        f.set(1.0, Duration::from_millis(200), now);
        assert!(f.running(now));
        let mid = f.value_at(now + Duration::from_millis(100));
        assert!(mid > 0.5 && mid < 1.0);
        assert_eq!(f.value_at(now + Duration::from_secs(1)), 1.0);
        assert!(!f.running(now + Duration::from_secs(1)));
    }
}
