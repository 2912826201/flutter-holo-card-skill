# Flutter two-layer rendering contract

## Composition and parallax

Render exactly `background -> foreground`. The combined foreground owns every character and card-interface element, so its source overlap order remains intact.

Use `source.png` Alpha as the static card shape. Keep `background.png` opaque and full-canvas; clip its display with the static card shape, but sample enough interior bleed for view motion. Sample `foreground.png`, `foreground_contour.png`, and `foreground_bloom.png` from one identical UV.

Paint on a centered 160% transparent surface and map output coordinates with:

```glsl
vec2 p = (outputUv - 0.5) * 1.6 + 0.5;
vec2 foregroundUv = p - view * (depth < 0.0 ? 0.055 : 0.075) * depth;
vec2 backgroundUv = p + view * 0.04;
```

At zero view, both layers use the source coordinate system exactly; do not center-crop or enlarge the background. A small opposite background shift creates separation during tilt, with clamped full-bleed sampling preventing empty strips. Negative and zero depth remain inside the static card shape. Positive depth may extend foreground pixels beyond the clipped background, while the foreground's own moved Alpha preserves its rounded boundary.

Keep physical rotation modest. Use one amplified view vector for parallax and material motion, with defaults selected so the vector approaches but does not spend a large part of the drag range clamped:

```text
view.x = sin(rotateY) * 0.65 * sensitivity
view.y = sin(rotateX) * 0.65 * sensitivity
```

The primary component defaults are `depth = 1`, `viewSensitivity = 3`, and `maxTiltRadians = 0.24`.

## Foil material

Apply foil after the two color layers are composited. Preserve readable source color and contrast:

- one broad lower-left-to-upper-right prism band follows view;
- a lower-amplitude secondary diffraction wave prevents a flat single-gradient look;
- sparse micro-glints add texture without covering faces or text;
- a restrained moving glare adds specular response;
- idle state retains a low-strength foil field, interaction eases it to full requested strength;
- `effectStrength == 0` disables foil, glints, glare, contour emission, and bloom.

Do not use a high-opacity rainbow replacement that washes the card toward white. Compose light in linear space and apply display mapping only after contour emission and bloom.

## White sketch highlight

`foreground_contour.png` contains the grayscale sketch core. `foreground_bloom.png` packs near blur in R and wide blur in G.

Sample all three maps with `foregroundUv`. Multiply the core by foreground Alpha. Keep its emission predominantly white with a small spectral tint. The two bloom channels form a genuine halo and therefore must not be multiplied back down to only the one-pixel line core.

The complete foreground receives sketch highlights: character silhouettes and internal features, foreground effects and objects, glyphs, symbols, panels, insets, logos, and decorative frame strokes. Scenery receives none.

## Sizing and interaction

Preserve the loaded source aspect ratio. Under bounded width and height, fit the card inside the available rectangle and center it. Under one-axis-unbounded constraints, derive the missing dimension from the image aspect ratio. Do not stretch the Shader surface.

Keep normalized interaction state as `(yaw, pitch)`:

- mouse hover may map both axes from absolute card position;
- pointer down records the current position and tilt without changing either axis;
- drag maps displacement from that origin;
- release animates continuously from the current value to zero;
- effect activation eases in on hover/down and returns to the configured idle strength on exit/up.

## Required tests

- The five images and Shader load, and the Shader compiles without an independent-character branch.
- The renderer preserves the source aspect ratio in matching, narrow, wide, and one-axis-unbounded constraints.
- The painter surface is centered at 160% on every card.
- Touch-down and a horizontal-only first drag leave pitch unchanged; a later upward drag makes pitch positive.
- Release is continuous and ends centered.
- Idle strength is nonzero by default, interaction increases it, and `effectStrength == 0` remains zero.
- The primary defaults are `depth == 1`, `viewSensitivity == 3`, and `maxTiltRadians == 0.24`.
- Resource tests reject changed foreground RGB, opaque/checkerboard line-art matte, canvas mismatches, contour outside foreground, transparent background, and map-format errors.
