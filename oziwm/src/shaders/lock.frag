// OziOS lock screen background and password field. Premultiplied output.
precision mediump float;

uniform float alpha;
uniform vec2 size;
varying vec2 v_coords;

uniform float ozi_time;
uniform vec3 ozi_ink;
uniform vec3 ozi_c1;
uniform vec3 ozi_c2;
uniform vec4 ozi_field;    // password field: x, y, w, h (pixels)
uniform float ozi_state;   // 0 typing, 1 checking, 2 wrong
uniform float ozi_shake;   // 0..1, how far into the wrong-password shake

float sd_round_box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main() {
    vec2 p = v_coords * size;
    vec2 uv = v_coords;

    // Two slow lights over ink.
    vec2 l1 = vec2(0.30 + 0.08 * sin(ozi_time * 0.11), 0.35 + 0.07 * cos(ozi_time * 0.09));
    vec2 l2 = vec2(0.72 + 0.07 * cos(ozi_time * 0.08), 0.65 + 0.08 * sin(ozi_time * 0.12));
    float aspect = size.x / max(size.y, 1.0);
    vec2 a = vec2(aspect, 1.0);
    float g1 = exp(-pow(length((uv - l1) * a) / 0.45, 2.0));
    float g2 = exp(-pow(length((uv - l2) * a) / 0.40, 2.0));
    vec3 col = ozi_ink + ozi_c1 * g1 * 0.30 + ozi_c2 * g2 * 0.26;
    // A faint vignette.
    col *= 1.0 - 0.35 * pow(length((uv - 0.5) * a * 0.9), 2.0);

    // Password field, shaking sideways after a wrong password.
    vec2 c = ozi_field.xy + ozi_field.zw * 0.5;
    c.x += sin(ozi_shake * 31.4) * 14.0 * (1.0 - ozi_shake) * step(0.001, ozi_shake);
    float d = sd_round_box(p - c, ozi_field.zw * 0.5, ozi_field.w * 0.5);
    vec3 edge = ozi_state > 1.5 ? vec3(1.0, 0.333, 0.431) : mix(ozi_c1, ozi_c2, 0.5 + 0.5 * sin(ozi_time * 1.5));
    float inside = 1.0 - smoothstep(-0.5, 0.5, d);
    float ring = smoothstep(-2.5, -1.5, d) * (1.0 - smoothstep(-0.5, 0.5, d));
    float glow = exp(-max(d, 0.0) / 12.0) * (1.0 - inside) * (ozi_state > 0.5 ? 0.6 : 0.35);
    col = mix(col, ozi_ink * 1.6 + 0.02, inside * 0.85);
    col = mix(col, edge, ring);
    col += edge * glow;

    gl_FragColor = vec4(col, 1.0) * alpha;
}
