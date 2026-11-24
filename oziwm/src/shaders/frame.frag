// OziOS window frame: a soft shadow, a hairline border, the title bar and its
// buttons, in one pass. Quiet on purpose: depth comes from the shadow, not
// from colour. Output is premultiplied alpha.
precision mediump float;

uniform float alpha;
uniform vec2 size;
varying vec2 v_coords;

uniform vec4 ozi_rect;     // frame (content + title bar) inside this element: x, y, w, h
uniform float ozi_radius;
uniform float ozi_border;
uniform float ozi_title;   // title bar height, 0 when the client draws its own
uniform float ozi_active;  // 0..1, animated
uniform float ozi_glow;    // 0..2: how much of the accent the focused border takes
uniform float ozi_time;    // unused: the frame does not move
uniform vec3 ozi_c1;       // accent
uniform vec3 ozi_c2;       // unused
uniform vec3 ozi_bar;
uniform vec3 ozi_muted;
uniform vec4 ozi_btn;      // first button centre x, centre y, spacing, radius
uniform float ozi_hover;   // -1 none, 0 minimise, 1 maximise, 2 close

float sd_round_box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

float sd_segment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
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

    float lum = dot(ozi_bar, vec3(0.299, 0.587, 0.114));
    bool dark = lum < 0.5;
    // Text-coloured ink for lines and glyphs: light on dark bars, dark on light ones.
    vec3 ink = dark ? vec3(1.0) : vec3(0.0);

    // Shadow: wide and soft, a little below the window; the focused window floats higher.
    float lift = mix(3.0, 8.0, ozi_active);
    float spread = mix(14.0, 28.0, ozi_active);
    float ds = sd_round_box(p - centre - vec2(0.0, lift), half_size - vec2(2.0), ozi_radius);
    float fall = 1.0 - smoothstep(-spread * 0.4, spread, ds);
    float shadow_a = fall * fall * mix(0.22, 0.42, ozi_active) * outside;
    vec4 col = vec4(0.0, 0.0, 0.0, shadow_a);

    // Hairline border, on the inside edge so it never thickens the window.
    float ring = (1.0 - outside) * (1.0 - smoothstep(-ozi_border - 0.5, -ozi_border + 0.5, d));
    float tint = clamp(ozi_glow, 0.0, 1.0) * 0.6 * ozi_active;
    vec3 edge = mix(ink, ozi_c1, tint);
    float edge_a = mix(dark ? 0.10 : 0.14, dark ? 0.16 : 0.20, ozi_active);
    edge_a = mix(edge_a, 0.45, tint);
    col = over(vec4(edge * ring * edge_a, ring * edge_a), col);

    // Title bar: flat; an unfocused window's bar sinks back a little.
    float inside = 1.0 - outside;
    float in_bar = inside * (1.0 - step(ozi_rect.y + ozi_title, p.y)) * (1.0 - ring * edge_a);
    if (ozi_title > 0.0 && in_bar > 0.0) {
        vec3 bar = mix(ozi_bar * (dark ? 0.86 : 0.97), ozi_bar, ozi_active);
        vec4 bar_col = vec4(bar, 1.0) * in_bar;
        // A hairline between the bar and the window's content.
        float sep = in_bar * (1.0 - smoothstep(0.0, 1.0, abs(p.y - (ozi_rect.y + ozi_title - 0.5))));
        bar_col = over(vec4(ink * sep * 0.08, sep * 0.08), bar_col);

        // Buttons: minimise, maximise, close. Line glyphs; a rounded square
        // shows under the pointer, red for close.
        float r = ozi_btn.w;
        for (int i = 0; i < 3; i++) {
            vec2 bc = vec2(ozi_btn.x + float(i) * ozi_btn.z, ozi_btn.y);
            vec2 q = p - bc;
            float hovered = 1.0 - step(0.5, abs(ozi_hover - float(i)));
            bool close = i == 2;

            float pad = sd_round_box(q, vec2(r * 1.55), r * 0.55);
            float pad_a = (1.0 - smoothstep(-0.6, 0.6, pad)) * hovered;
            vec3 pad_c = close ? vec3(0.87, 0.24, 0.27) : ink;
            float pad_o = close ? 1.0 : (dark ? 0.12 : 0.09);
            bar_col = over(vec4(pad_c * pad_a * pad_o, pad_a * pad_o), bar_col);

            float s = r * 0.62;
            float g;
            if (i == 0) {
                g = sd_segment(q, vec2(-s, 0.0), vec2(s, 0.0));
            } else if (i == 1) {
                g = abs(sd_round_box(q, vec2(s * 0.9), 1.5));
            } else {
                g = min(sd_segment(q, vec2(-s * 0.85), vec2(s * 0.85)), sd_segment(q, vec2(-s * 0.85, s * 0.85), vec2(s * 0.85, -s * 0.85)));
            }
            float line = 1.0 - smoothstep(0.55, 1.35, g);
            vec3 glyph_c = (close && hovered > 0.5) ? vec3(1.0) : ink;
            float glyph_o = mix(0.45, 0.85, max(ozi_active, hovered));
            bar_col = over(vec4(glyph_c * line * glyph_o, line * glyph_o), bar_col);
        }
        col = over(bar_col, col);
    }

    gl_FragColor = col * alpha;
}
