// Window content with rounded corners. Coordinates arrive as texture
// coordinates; the uniforms say where the window's corners are in them.
//_DEFINES_

#if defined(EXTERNAL)
#extension GL_OES_EGL_image_external : require
#endif

precision mediump float;
#if defined(EXTERNAL)
uniform samplerExternalOES tex;
#else
uniform sampler2D tex;
#endif

uniform float alpha;
varying vec2 v_coords;

#if defined(DEBUG_FLAGS)
uniform float tint;
#endif

uniform vec2 ozi_origin;    // window top-left, in texture coordinates
uniform vec2 ozi_tex_size;  // window size, in texture coordinates
uniform vec2 ozi_px_size;   // window size, in pixels
uniform float ozi_radius;
uniform float ozi_round_top; // 0 when a title bar covers the top corners

float sd_round_box(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main() {
    vec4 color = texture2D(tex, v_coords);

#if defined(NO_ALPHA)
    color = vec4(color.rgb, 1.0) * alpha;
#else
    color = color * alpha;
#endif

    vec2 px = (v_coords - ozi_origin) / ozi_tex_size * ozi_px_size;
    vec2 half_size = ozi_px_size * 0.5;
    // Only cut inside the window; popups that reach outside stay whole.
    bool within = px.x >= 0.0 && px.y >= 0.0 && px.x <= ozi_px_size.x && px.y <= ozi_px_size.y;
    bool top_half = px.y < half_size.y;
    if (within && (ozi_round_top > 0.5 || !top_half)) {
        float d = sd_round_box(px - half_size, half_size, ozi_radius);
        color *= 1.0 - smoothstep(-0.5, 0.5, d);
    }

#if defined(DEBUG_FLAGS)
    if (tint == 1.0)
        color = vec4(0.0, 0.2, 0.0, 0.2) + color * 0.8;
#endif

    gl_FragColor = color;
}
