# Resource workflow

## Layer contract

| Asset | Required content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete scenery only, including repaired concealed regions | Opaque inside the card boundary; exterior rounded corners may stay transparent |
| Foreground | Original source pixels for character, typography, symbols, panels, credits, and frame; optionally one or more bounded source-pixel depth-lock patches | Transparent where scenery remains independently moving |
| Structure | Actually visible character contours and selected form lines, white on black | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0 | Opaque |

The character and card interface intentionally share one runtime depth. A temporary subject or UI selection mask may be used while preparing resources, but do not expose another moving character layer.

## Background generation prompt

Use the source as the only geometry reference:

> Reconstruct a complete scenery-only plate on the exact original full-card canvas. Keep it opaque throughout the visible card boundary while preserving any transparent exterior rounded corners. Remove the main illustrated subject, all typography, numbers, symbols, panels, logos, credits, and the decorative card frame. Continue surrounding colors, shapes, clouds, stars, strokes, and lighting naturally through every concealed region. Provide enough coherent surrounding scenery for a two-times moving crop. Preserve the source aspect ratio and coordinate system; do not crop, recenter, add a new subject, leave silhouettes, or retain glyph fragments.

Reject a result containing a faint subject, empty silhouette, text ghost, frame fragment, or unrelated redesign.

## Foreground selection plate

Ask the image model for a full-color selection aid, not final artwork:

> Keep the supplied full-card canvas, aspect ratio, framing, scale, silhouette, and overlap positions. Replace every scenery-only pixel with one flat saturated chroma green matte. Keep non-green all character pixels and every foreground card-interface region: header, title, rules text, symbols, panels, credits, logos, edge decorations, and complete frame. Keep dark ink, pale highlights, holes between limbs, and detached foreground marks correctly classified. Do not crop, recenter, rotate, reconstruct hidden anatomy, or leave scenery islands inside foreground regions.

The model may repaint retained colors or spell glyphs incorrectly. That is acceptable in this temporary plate because only the green/non-green semantic boundary is consumed. It is not acceptable for the model to move a silhouette, omit a visible element, merge a scenery hole, or retain a scenery island.

Run `prepare_foreground.py`. It converts chroma green to alpha and copies all RGB from the normalized source. Inspect the temporary `foreground-on-black.png`, `foreground-on-white.png`, and `foreground-alignment-overlay.png`. Require `source_rgb_preserved: true` in `foreground-report.json`, then remove these intermediates during final cleanup.

## Ambiguous enclosed scenery pockets

Do not force a pixel-perfect cut through a complex subject when the selection leaves several scenery fragments inside or beside a narrow limb, garment, hair strand, or frame junction. If those fragments surround one enclosed transparent pocket, assign that entire pocket to foreground depth as a single source-pixel patch. This trades a small amount of local parallax for a continuous undistorted subject and prevents neighboring copies of the same scenery from sliding against each other.

Use `bridge_foreground.py` with a seed inside the reviewed transparent pocket. The script fills the connected component only when it stays away from the canvas edge and remains under the configured coverage limit. It always rebuilds RGB from the normalized source. Review its red overlay and black/white previews before accepting it.

Do not use a depth-lock patch when the component opens into the main scenery, when a boundary would cut through a salient background shape, or when the total patch is large enough to erase useful depth. In those cases regenerate the selection plate. Never synthesize or repaint the subject for this correction.

## Visible-only structure prompt

Generate from the accepted foreground or a temporary character-only view at the identical canvas:

> Create a strictly registered semantic character structure map. Keep the exact full-card canvas, aspect ratio, framing, scale, pose, and pixel positions. On pure black, draw clean thin continuous white antialiased lines only for character segments actually visible in the accepted foreground: visible silhouette, face and eyes, hair, hands and fingers, clothing seams, and meaningful folds. Wherever text, a panel, symbol, border, frame, logo, or other foreground graphic covers the character, leave those covered pixels pure black and stop the line at the visible occlusion edge. Do not reconstruct hidden anatomy. Do not trace typography, panels, frame, scenery, stars, foil texture, print noise, shading, or halftone. No filled regions, gray shading, color, or glow.

A comparison image may define line quality, but never copy it into project assets. Generate the structure from the current card.

## Local contour fallback after a safety refusal

When an image service refuses or safety-blocks semantic line-art generation, accept the refusal and switch paths. Do not retry with euphemisms, prompt obfuscation, or requests to reconstruct hidden anatomy. The fallback must use only local deterministic processing of accepted source pixels.

First define a coarse visible-character scope on the normalized full canvas. Use one or more reviewed rectangles or polygons; subtract trainer portraits, text, panels, symbols, scenery, and frame regions. The shape need not trace the silhouette because the extractor also intersects it with the accepted foreground Alpha:

```bash
python scripts/prepare_local_character_mask.py \
  --reference source.png \
  --foreground foreground.png \
  --include-polygon "x1,y1;x2,y2;x3,y3" \
  --exclude-rect x0,y0,x1,y1 \
  --output-mask character-region-mask.png \
  --output-overlay character-region-overlay.png \
  --output-report character-region-report.json
```

Inspect the green overlay, then extract native source edges:

```bash
python scripts/extract_local_structure.py \
  --source source.png \
  --foreground foreground.png \
  --character-mask character-region-mask.png \
  --occlusion-mask ui-occlusion.png \
  --output-structure structure-local.png \
  --output-overlay structure-local-overlay.png \
  --output-report structure-local-report.json
```

The extractor applies bilateral noise suppression, multi-channel Canny edges, tiny-component rejection, foreground-Alpha clipping, character-region clipping, and UI occlusion locally. It never calls an image model, invents lines, or reconstructs concealed content. Use `structure-local.png` directly with `prepare_structure_maps.py`; skip `calibrate_structure.py` because the local result is already pixel-aligned.

Review the red overlay. Raise `--edge-quantile` when print grain or foil texture is too dense; lower it only when important visible source lines are missing. This fallback intentionally favors exact registration and policy reliability over semantic cleanliness. Reject it if local texture cannot be separated from meaningful visible structure without tracing UI or scenery.

## Visible-pixel occlusion prompt

Generate this after accepting the foreground. It is a temporary safety mask, not a runtime depth layer:

> Produce a conservative black-and-white mask on the exact complete source canvas. White means a visible card-interface or non-character pixel that must block character contour light; black means an actually visible character pixel. Make the outer frame, typography, numbers, symbols, logos, credits, footer marks, solid information panels, and continuous safety ribbons around rules-text lines white. Visible character pixels take priority and stay black where the character overlaps the geometric bounds of a header, title panel, or border. Where text or a panel visibly covers the character, keep the covering region white and do not reconstruct the hidden character. Preserve the original canvas, scale, positions, and layer order. Use flat black and white only; no line art, scenery texture, gradients, glow, or transparency.

Normalize it with:

```bash
python scripts/prepare_occlusion_mask.py \
  --reference source.png \
  --selection ui-occlusion-selection.png \
  --output-mask ui-occlusion.png \
  --output-overlay ui-occlusion-overlay.png
```

The white area may be wider than a text glyph but must not remove important visible character contours. Inspect the overlay before preparing bloom.

Keep the accepted normalized original as `source.png`; it is the runtime fallback and static card-shape Alpha mask. All other source copies, selection plates, masks, depth-lock overlays, per-stage previews, alignment overlays, aligned structures, and JSON reports are temporary. After the final checker passes, use `cleanup_assets.py`; leave exactly `source.png` plus the four derived runtime images.

## Alignment

The source, foreground, structure, and bloom always occupy the same full canvas. Never align independently cropped bounding boxes.

1. Create a red structure overlay on the foreground with `prepare_structure_maps.py --output-overlay`.
2. Check eyes, fingers, face outline, long outer silhouettes, and UI crossings.
3. Run `calibrate_structure.py` to estimate a safe full-canvas affine from generated semantic lines to original source edges. Record its six forward coefficients and correlation report.
4. Prefer rejection and regeneration when the model changes anatomy. Automatic or manual affine is only for uniform framing drift.
5. Apply the visible-pixel occlusion mask after registration so transformed lines cannot move onto text, panels, scenery, or frame pixels.

An occlusion mask is a full-canvas grayscale image: `255` blocks contour emission and `0` permits it. Keep a safety margin around small text when exact per-glyph masking is unreliable.

## Map preparation

`prepare_structure_maps.py` performs full-canvas normalization, optional affine registration, foreground-alpha clipping, optional UI occlusion, and two-scale bloom generation. It deliberately does not discover anatomy, infer an occlusion mask, or auto-fit bounding boxes.

For a 1000 px wide canvas, start with near radius `7` and wide radius `20`; the script scales both radii with canvas width. The contour file stays RGB-equivalent black/white. The bloom file stores near/wide luminance in R/G for two sampler-friendly scales.
