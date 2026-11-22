// OziOS window frame: shadow, flowing two-colour glow, border, title bar and
// its buttons, in one pass. Output is premultiplied alpha.
precision mediump float;

uniform float alpha;
uniform vec2 size;
varying vec2 v_coords;

uniform vec4 ozi_rect;     // frame (content + title bar) inside this element: x, y, w, h
uniform float ozi_radius;
uniform float ozi_border;
uniform float ozi_title;   // title bar height, 0 when the client draws its own
uniform float ozi_active;  // 0..1, animated
uniform float ozi_glow;    // 0..2
uniform float ozi_time;    // seconds
uniform vec3 ozi_c1;
uniform vec3 ozi_c2;
uniform vec3 ozi_bar;
uniform vec3 ozi_muted;
uniform vec4 ozi_btn;      // first button centre x, centre y, spacing, radius
uniform float ozi_hover;   // -1 none, 0 minimise, 1 maximise, 2 close

float sd_round_box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

vec4 over(vec4 top, vec4 bottom) {
    return top + bottom * (1.0 - top.a);
}

void main() {
    vec2 p = v_coords * size;
    vec2 half_size = ozi_rect.zw * 0.5;
    vec2 centre = ozi_rect.xy + half_size;
    float d = sd_round_box(p - centre, half_size, ozi_radius);
    float outside = smoothstep(-0.5, 0.5, d);

    // The colours travel slowly around the window.
    float angle = atan(p.y - centre.y, p.x - centre.x);
    float wave = 0.5 + 0.5 * sin(angle + ozi_time * 0.7);
    vec3 flow = mix(ozi_c1, ozi_c2, wave);
    vec3 edge = mix(ozi_muted * 0.45, flow, ozi_active);

    // Shadow, a little lower than the window, deeper when active.
    float ds = sd_round_box(p - centre - vec2(0.0, 7.0), half_size, ozi_radius);
    float spread = mix(16.0, 30.0, ozi_active);
    float shadow_a = (1.0 - smoothstep(-ozi_radius * 0.5, spread, ds)) * mix(0.30, 0.50, ozi_active) * outside;
    vec4 col = vec4(0.0, 0.0, 0.0, shadow_a);

    // Glow: only the active window, breathing very gently.
    float breath = 0.88 + 0.12 * sin(ozi_time * 1.6);
    float glow_a = exp(-max(d, 0.0) / 10.0) * ozi_active * ozi_glow * 0.42 * breath * outside;
    col = over(vec4(flow * glow_a, glow_a), col);

    // Border ring just outside the content.
    float ring = smoothstep(-0.5, 0.5, d) * (1.0 - smoothstep(ozi_border - 0.5, ozi_border + 0.5, d));
    col = over(vec4(edge * ring, ring), col);

    // Title bar.
    float inside = 1.0 - outside;
    float in_bar = inside * (1.0 - step(ozi_rect.y + ozi_title, p.y));
    if (ozi_title > 0.0 && in_bar > 0.0) {
        float y = (p.y - ozi_rect.y) / ozi_title;
        vec3 bar = ozi_bar + flow * (0.10 * ozi_active) * (1.0 - y);
        // A hairline of the flow colour at the very top of the bar.
        float top_line = (1.0 - smoothstep(0.0, 1.5, p.y - ozi_rect.y)) * 0.5 * ozi_active;
        bar = mix(bar, flow, top_line);
        vec4 bar_col = vec4(bar, 1.0) * in_bar;

        // Buttons: minimise, maximise, close.
        vec3 tones[3];
        tones[0] = vec3(1.0, 0.745, 0.353);
        tones[1] = vec3(0.235, 0.902, 0.627);
        tones[2] = vec3(1.0, 0.333, 0.431);
        for (int i = 0; i < 3; i++) {
            vec2 bc = vec2(ozi_btn.x + float(i) * ozi_btn.z, ozi_btn.y);
            float bd = length(p - bc) - ozi_btn.w;
            float hovered = 1.0 - step(0.5, abs(ozi_hover - float(i)));
            vec3 tone = mix(ozi_muted * 0.7, tones[i], max(ozi_active, hovered));
            float disc = 1.0 - smoothstep(-0.6, 0.6, bd);
            float halo = exp(-max(bd, 0.0) / 4.0) * hovered * 0.6;
            vec3 face = tone * (1.0 + 0.25 * hovered);
            bar_col = over(vec4(face * disc, disc), bar_col);
            bar_col = over(vec4(tone * halo * (1.0 - disc), halo * (1.0 - disc)), bar_col);
        }
        col = over(bar_col, col);
    }

    gl_FragColor = col * alpha;
}
