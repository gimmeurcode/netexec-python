"""
crt_gl.py — NETEXEC
====================
GPU CRT post-processing via ModernGL.

The whole composited frame (chrome + bezel + game) is rendered to an offscreen
pygame.Surface, uploaded to a GL texture with a zero-copy BGRA buffer view, and
drawn to the window through a fullscreen-quad GLSL fragment shader that applies
barrel curvature, edge-weighted chromatic aberration, scanlines, vignette and
sRGB-correct gamma — the render-to-texture pattern from the CRT research guides.

If ModernGL or a GL context is unavailable, ``create_gl_presenter`` returns
None and the caller falls back to the pure-pygame / numpy CRT path. The shaders
are embedded as strings (no external files) so the frozen build needs no data.
"""

import struct

import pygame


_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 uv;
void main() {
    uv = in_uv;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

_FRAG = """
#version 330
uniform sampler2D tex;
uniform vec2  resolution;   // output (window) resolution in pixels
uniform float time;         // seconds, for a subtle rolling flicker
uniform bool  crt_on;       // master toggle for the analog effect
// Per-effect intensities, driven by the Settings sliders. Each is already
// scaled to its working range by the presenter; 0 = that effect fully off.
uniform float u_curve;      // barrel-distortion coefficient (0 = perfectly flat)
uniform float u_scan;       // scanline darkness depth        (0 = off)
uniform float u_aber;       // chromatic-aberration strength  (0 = off)
uniform float u_vig;        // vignette strength              (0 = off)
in  vec2 uv;
out vec4 fragColor;

// Barrel distortion: push UVs outward near the edges (Babylon/Lottes form).
// u_curve is a strength coefficient — 0 yields no displacement (flat screen).
vec2 curve(vec2 p) {
    p = p * 2.0 - 1.0;
    vec2 off = abs(p.yx) * u_curve;
    p = p + p * off * off;
    return p * 0.5 + 0.5;
}

void main() {
    // Passthrough when the CRT filter is disabled.
    if (!crt_on) {
        fragColor = texture(tex, uv);
        return;
    }

    vec2 c = curve(uv);
    // Outside the curved tube -> black bezel/frame.
    if (c.x < 0.0 || c.x > 1.0 || c.y < 0.0 || c.y > 1.0) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    // Edge-weighted chromatic aberration: R/B separate toward the borders.
    vec2 d = c - 0.5;
    vec2 ca = d * u_aber * (1.0 + 2.0 * dot(d, d));
    vec3 col;
    col.r = texture(tex, c + ca).r;
    col.g = texture(tex, c).g;
    col.b = texture(tex, c - ca).b;

    // Work in linear light so the scanline/vignette darkening stays vivid.
    col = pow(col, vec3(2.2));

    // Scanlines locked to a virtual line count derived from the output height.
    float lines = resolution.y * 0.5;
    float s = sin(c.y * lines * 3.14159265 * 2.0);
    s = 0.5 * s + 0.5;
    col *= 1.0 - u_scan * (1.0 - s);

    // Slight global flicker (very subtle).
    col *= 1.0 + 0.012 * sin(time * 6.2831);

    // Vignette: darken toward the curved corners.
    float v = length(d);
    col *= 1.0 - smoothstep(0.45, 0.95, v) * u_vig;

    // Back to sRGB for the display.
    col = pow(col, vec3(1.0 / 2.2));
    fragColor = vec4(col, 1.0);
}
"""


class GLPostProcessor:
    """Presents an offscreen pygame.Surface to the GL window via a CRT shader."""

    def __init__(self):
        import moderngl   # imported lazily so the game runs without it
        self.ctx = moderngl.create_context()
        self._moderngl = moderngl
        self.prog = self.ctx.program(vertex_shader=_VERT, fragment_shader=_FRAG)

        # Fullscreen quad (TRIANGLE_STRIP). UV v is flipped so the top-left of
        # the pygame surface maps to the top of the screen.
        quad = [
            -1.0, -1.0, 0.0, 1.0,
             1.0, -1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 0.0,
             1.0,  1.0, 1.0, 0.0,
        ]
        self.vbo = self.ctx.buffer(struct.pack("16f", *quad))
        self.vao = self.ctx.vertex_array(
            self.prog, [(self.vbo, "2f 2f", "in_pos", "in_uv")]
        )
        self.tex = None
        self._tex_size = None

    def _ensure_texture(self, w: int, h: int):
        if self._tex_size != (w, h):
            if self.tex is not None:
                self.tex.release()
            self.tex = self.ctx.texture((w, h), 4)
            # LINEAR so the curved resample of UI text stays smooth, not jagged.
            self.tex.filter = (self._moderngl.LINEAR, self._moderngl.LINEAR)
            self.tex.swizzle = "BGRA"   # pygame stores BGRA; swizzle is free
            self._tex_size = (w, h)

    def present(self, surface: pygame.Surface, crt_on: bool, time_s: float,
                params: dict | None = None):
        """Upload ``surface`` and draw it through the CRT shader, then flip.

        ``params`` holds normalized [0,1] slider values (curvature, scanline,
        aberration, vignette); they are mapped to the shader's working ranges.
        """
        w, h = surface.get_size()
        self._ensure_texture(w, h)
        # Zero-copy upload of the raw surface buffer (BGRA swizzle handles order).
        self.tex.write(surface.get_view("1"))

        p = params or {}
        # Sliders are normalized 0..1. Each maps LINEARLY to its working range:
        # 0 = that effect completely off, 1 = a reasonable maximum.
        curv = max(0.0, min(1.0, float(p.get("curvature",  0.45))))
        scan = max(0.0, min(1.0, float(p.get("scanline",   0.40))))
        aber = max(0.0, min(1.0, float(p.get("aberration", 0.40))))
        vig  = max(0.0, min(1.0, float(p.get("vignette",   0.55))))

        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0)
        self.tex.use(0)
        self.prog["tex"].value = 0
        self.prog["resolution"].value = (float(w), float(h))
        self.prog["time"].value = float(time_s)
        self.prog["crt_on"].value = bool(crt_on)
        self.prog["u_curve"].value = curv * 0.22    # 0 = flat, max = gentle bulge
        self.prog["u_scan"].value  = scan * 0.40    # 0 = none, max = 40% darkening
        self.prog["u_aber"].value  = aber * 0.0035  # 0 = none, max = mild fringing
        self.prog["u_vig"].value   = vig * 0.80     # 0 = none, max = strong corners
        self.vao.render(self._moderngl.TRIANGLE_STRIP)
        pygame.display.flip()

    def resize(self, w: int, h: int):
        """Match the GL viewport to a new window size."""
        try:
            self.ctx.viewport = (0, 0, w, h)
        except Exception:
            pass


def create_gl_presenter():
    """Return a GLPostProcessor, or None if ModernGL/GL context is unavailable.

    The caller must already have created the display with the OPENGL flag.
    """
    try:
        return GLPostProcessor()
    except Exception as exc:        # pragma: no cover - hardware/dep dependent
        print(f"[crt_gl] GPU CRT unavailable, using CPU fallback: {exc}")
        return None
