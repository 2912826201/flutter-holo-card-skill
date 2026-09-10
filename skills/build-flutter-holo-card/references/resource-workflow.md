# Resource workflow

## Layer contract

| Asset | Required content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete scenery only, including repaired concealed regions | Opaque inside the card boundary; exterior rounded corners may stay transparent |
| Foreground | Original source pixels for character, typography, symbols, panels, credits, and frame | Transparent only where scenery was removed |
| Structure | Actually visible character contours and selected form lines, white on black | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0 | Opaque |

The character and card interface intentionally share one runtime depth. A temporary subject or UI selection mask may be used while preparing resources, but do not expose another moving character layer.

## Background generation prompt

Use the source as the only geometry reference:

> Reconstruct a complete scenery-only plate on the exact original full-card canvas. Keep it opaque throughout the visible card boundary while preserving any transparent exterior rounded corners. Remove the main illustrated subject, all typography, numbers, symbols, panels, logos, credits, and the decorative card frame. Continue surrounding colors, shapes, clouds, stars, strokes, and lighting naturally through every concealed region. Provide enough coherent surrounding scenery for a two-times moving crop. Preserve the source aspect ratio and coordinate system; do not crop, recenter, add a new subject, leave silhouettes, or retain glyph fragments.

Reject a result containing a faint subject, empty silhouette, text ghost, frame fragment, or unrelated redesign.

## Foreground selection plate

Ask the image model for a selection aid, not replacement artwork:

> Preserve the supplied card exactly. Replace scenery-only pixels with one flat saturated chroma matte. Retain the character and every foreground card-interface pixel: header, title, rules text, symbols, panels, credits, logos, edge decorations, and complete frame. Do not redraw, sharpen, recolor, move, crop, or reconstruct retained pixels. Keep the entire original canvas and positions.

Convert only inspected matte-connected regions to alpha. Copy RGB from the normalized source, never from the generated selection plate. Preserve pale clothing, skin, white highlights, dark ink, enclosed gaps, detached decorations, and antialiased edges. Inspect the result over black and white.

## Visible-only structure prompt

Generate from the accepted foreground or a temporary character-only view at the identical canvas:

> Create a strictly registered semantic character structure map. Keep the exact full-card canvas, aspect ratio, framing, scale, pose, and pixel positions. On pure black, draw clean thin continuous white antialiased lines only for character segments actually visible in the accepted foreground: visible silhouette, face and eyes, hair, hands and fingers, clothing seams, and meaningful folds. Wherever text, a panel, symbol, border, frame, logo, or other foreground graphic covers the character, leave those covered pixels pure black and stop the line at the visible occlusion edge. Do not reconstruct hidden anatomy. Do not trace typography, panels, frame, scenery, stars, foil texture, print noise, shading, or halftone. No filled regions, gray shading, color, or glow.

A comparison image may define line quality, but never copy it into project assets. Generate the structure from the current card.

## Alignment

The source, foreground, structure, and bloom always occupy the same full canvas. Never align independently cropped bounding boxes.

1. Create a red structure overlay on the foreground with `prepare_structure_maps.py --output-overlay`.
2. Check eyes, fingers, face outline, long outer silhouettes, and UI crossings.
3. Prefer rejection and regeneration when the model changes anatomy.
4. Use a single global affine correction only for uniform framing drift. Record the six forward coefficients and recheck the overlay.
5. Apply a UI occlusion mask after registration so the transformation cannot move hidden lines onto text or frame pixels.

An occlusion mask is a full-canvas grayscale image: `255` blocks contour emission and `0` permits it. Keep a safety margin around small text when exact per-glyph masking is unreliable.

## Map preparation

`prepare_structure_maps.py` performs full-canvas normalization, optional affine registration, foreground-alpha clipping, optional UI occlusion, and two-scale bloom generation. It deliberately does not discover anatomy, infer an occlusion mask, or auto-fit bounding boxes.

For a 1000 px wide canvas, start with near radius `7` and wide radius `20`; the script scales both radii with canvas width. The contour file stays RGB-equivalent black/white. The bloom file stores near/wide luminance in R/G for two sampler-friendly scales.
