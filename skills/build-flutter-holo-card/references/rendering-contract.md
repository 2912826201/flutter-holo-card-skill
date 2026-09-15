# Flutter rendering contract

## Layer order and UVs

Support both contracts:

- layered-3d: render background -> character -> complete interface/frame foreground. Apply contour and bloom to character before interface compositing so interface Alpha occludes both. This fixed order overrides any mixed overlap in the flat source: UI that was partly hidden by the character must already be restored in `foreground.png`.
- merged-2d: render background -> merged foreground and apply contour/bloom to that foreground.

Load the validated antialiased `source.png` Alpha as the static card shape. Its four outer corners must be transparent even when the supplied raster was opaque. It clips background in both modes and clips the complete merged-2d result. In layered-3d, a 160% transparent painter surface maps output coordinates through p=(uv-.5)*1.6+.5; only positive-depth character and interface pixels may move beyond the static mask. Never let repaired-background Alpha define the card shape or clip the full-bleed background asset itself, because shifted sampling needs scenery beyond the rounded boundary.

Use one normalized view vector for every internal effect:

```text
view.x = sin(rotateY) * 0.65 * sensitivity
view.y = sin(rotateX) * 0.65 * sensitivity
```

Clamp only after applying sensitivity. The Flutter component uses a small physical
rotation, so its primary preset uses `viewSensitivity = 4.0` and clamps the final
view to the holo-card renderer's practical `[-0.5, 0.5]` range. This recreates the
internal response of the reference's much larger drag angles without making the
Widget itself rotate excessively.

```glsl
vec2 characterUv = p - view * (depth < 0.0 ? 0.06 : 0.08) * depth;
vec2 interfaceUv = p - view * 0.14 * max(depth, 0.0);
vec2 backgroundUv = (p - 0.5) * 0.5 + 0.5 - view * 0.25;
```

In layered-3d, sample character, contour, and bloom at characterUv and foreground at interfaceUv. In merged-2d, sample foreground, contour, and bloom at characterUv. Never fit or offset contour separately.

Do not solve character-over-UI crossings in the Shader. The resource workflow must provide a continuous UI Alpha/RGB plate through every concealed crossing. Live foreground Alpha then covers both the character and its contour/bloom, preventing gaps at all signed depths.

Keep `depth = 0` as the neutral default from holo-card and preserve its full
`-3...+3` range. Integrations may select a signed non-zero depth for their intended
presentation. Depth changes UV displacement only; it never changes layer order or
scales artwork.

## Foil and sweep

Retain the source illustration while adding a colored light field:

```glsl
float field = p.x * 0.65 + p.y * 0.4 + view.x * 1.9 + view.y * 0.85;
float light = pow(max(0.0, 1.0 - abs(fract(field + 0.16) - 0.5) * 2.0), 3.0);
vec3 spectrum = 0.52 + 0.48 * cos(6.28318 * (phase + vec3(0.0, 0.33, 0.67)));
vec3 foil = base * (0.64 + spectrum * 0.7) + spectrum * 0.07 * alpha;
base = mix(base, foil, light * 0.48 * power);
```

With screen Y increasing downward, positive X and Y coefficients produce constant-value bands visually oriented from lower-left to upper-right. Keep pointer and rotation signs consistent with the component template.

## Contour emission

The contour sampler contains only white line core. The bloom sampler contains near blur in R and wide blur in G.

When line generation is unavailable, both files are opaque neutral-black maps. Keep loading and sampling them normally; they disable emission without a shader branch or a different resource contract.

```glsl
float ownerAlpha = layered ? characterAlpha : foregroundAlpha;
float uiOcclusion = layered ? 1.0 - foregroundAlpha : 1.0;
float line = structure * ownerAlpha * uiOcclusion;
float envelope = smoothstep(0.025, 0.42, light);
vec3 emissionColor = spectrum * 0.85 + 0.15;
vec3 emission = emissionColor * line * envelope * power * 40.0 * contourStrength;
vec3 bloom = emissionColor * (nearBloom * 0.55 + wideBloom * 0.8)
  * line * envelope * power * 40.0 * contourStrength;
```

Multiplying blurred bloom by `line` is intentional: it keeps the strong emission confined to generated foreground strokes instead of washing across scenery or flat interiors.

Compose in linear space and apply exponential display mapping after emission and bloom:

```glsl
vec3 linear = pow(clamp(base, 0.0, 1.0), vec3(2.2));
vec3 combined = 1.0 - (1.0 - linear) * exp(-(emission * 0.38 + bloom * 0.85));
vec3 display = pow(clamp(combined, 0.0, 1.0), vec3(1.0 / 2.2));
```

## Touch interaction

Keep normalized state as `(yaw, pitch)`:

- mouse hover may map both axes from absolute pointer position;
- touch down changes neither axis and records the drag origin;
- touch update maps both axes from displacement since drag start;
- touch release animates the current value to zero with an ease-out curve.

This prevents a lower-half touch from immediately pitching the card before the user drags.

## Required tests

- Shader loads with six layered-3d runtime images and five merged-2d images.
- Source card-shape Alpha has four transparent corners; foreground and character contain no source-space Alpha outside it, while background stays full-bleed.
- Optional character input selects layered-3d; its absence selects merged-2d without a second component.
- Layered-3d uses a 160% unclipped painter surface while merged-2d stays at card bounds.
- Layered-3d resources explicitly declare whether character-over-UI crossings are absent or completed; a completed foreground stays continuous over the moving character.
- Default, narrow, and wide layouts do not overflow.
- Drag changes both transform and shader view.
- Release is continuous before reaching center.
- Horizontal drag beginning in the lower half leaves `view.y == 0`.
- Subsequent upward drag makes `view.y > 0`.
- A stronger sensitivity changes the internal view without increasing physical card rotation.
- The primary defaults are `depth == 0` and `viewSensitivity == 4.0`.
