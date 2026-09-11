# Flutter rendering contract

## Layer order and UVs

Render `background -> merged foreground -> view-dependent material and contour emission`. Apply foil to the composed base, sparse stars where foreground alpha is absent, and contour emission only where the visible structure and foreground alpha overlap. The foreground already contains character, typography, panels, and frame; the structure map stays black beneath its non-character UI pixels.

Load the supplied source card as a fifth static sampler and use only its Alpha as the final card-shape mask. The repaired background is intentionally opaque for parallax sampling and must never define the outer silhouette. Multiply the final premultiplied color and Alpha by the static source mask so the background, shifted foreground, foil, glare, stars, contour, and bloom all share the exact antialiased card corners.

Use one normalized view vector for every internal effect:

```text
view.x = sin(rotateY) * 0.65 * sensitivity
view.y = sin(rotateX) * 0.65 * sensitivity
```

Clamp only after applying sensitivity. A useful default for small Flutter tilt is `2.4`, independently adjustable from physical rotation.

```glsl
vec2 foregroundUv = p - view * (depth < 0.0 ? 0.06 : 0.08) * depth;
vec2 backgroundUv = (p - 0.5) * 0.5 + 0.5 - view * 0.25;
```

Sample foreground, contour, and bloom at exactly `foregroundUv`. Never fit or offset contour separately.

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

```glsl
float line = structure * foregroundAlpha;
float envelope = smoothstep(0.025, 0.42, light);
vec3 emissionColor = spectrum * 0.85 + 0.15;
vec3 emission = emissionColor * line * envelope * power * 40.0 * contourStrength;
vec3 bloom = emissionColor * (nearBloom * 0.55 + wideBloom * 0.8)
  * line * envelope * power * 40.0 * contourStrength;
```

Multiplying blurred bloom by `line` is intentional: it prevents halo spill into scenery, flat subject interiors, text, and frame pixels.

Compose in linear space and apply exponential display mapping after emission and bloom:

```glsl
vec3 linear = pow(clamp(base, 0.0, 1.0), vec3(2.2));
vec3 combined = 1.0 - (1.0 - linear) * exp(-(emission * 0.38 + bloom * 0.85));
vec3 display = pow(clamp(combined, 0.0, 1.0), vec3(1.0 / 2.2));
```

## Touch interaction

Keep normalized state as `(yaw, pitch)`:

- mouse hover may map both axes from absolute pointer position;
- touch down maps horizontal position to yaw but preserves current pitch;
- touch update maps yaw from horizontal position and pitch from vertical displacement since drag start;
- touch release animates the current value to zero with an ease-out curve.

This prevents a lower-half touch from immediately pitching the card before the user drags.

## Required tests

- Shader and all five runtime images load: source card mask plus four derived images.
- Default, narrow, and wide layouts do not overflow.
- Drag changes both transform and shader view.
- Release is continuous before reaching center.
- Horizontal drag beginning in the lower half leaves `view.y == 0`.
- Subsequent upward drag makes `view.y > 0`.
- A stronger sensitivity changes the internal view without increasing physical card rotation.
