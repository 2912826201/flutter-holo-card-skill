# Resource workflow

## Layer contract

| Asset | Required content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete scenery only, including repaired concealed regions | Opaque inside the card boundary; exterior rounded corners may stay transparent |
| Foreground | Original source pixels for opaque character, typography, symbols, credits, frame strokes, and opaque panels; low-frequency color field plus partial Alpha for actually translucent UI material; optionally one or more bounded source-pixel depth-lock patches | Transparent where scenery remains independently moving, including scenery visible through translucent UI material |
| Structure | Model-generated smooth white sketch lines for the complete accepted foreground; neutral black when disabled | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0; neutral black when disabled | Opaque |

The character and card interface intentionally share one runtime depth. A temporary subject or UI selection mask may be used while preparing resources, but do not expose another moving character layer.

## Background generation prompt

Use the source as the only geometry reference:

> Reconstruct a complete scenery-only plate on the exact original full-card canvas. Keep it opaque throughout the visible card boundary while preserving any transparent exterior rounded corners. Remove the main illustrated subject, all typography, numbers, symbols, panels, logos, credits, and the decorative card frame. Continue surrounding colors, shapes, clouds, stars, strokes, and lighting naturally through every concealed region. Provide enough coherent surrounding scenery for a two-times moving crop. Preserve the source aspect ratio and coordinate system; do not crop, recenter, add a new subject, leave silhouettes, or retain glyph fragments.

Reject a result containing a faint subject, empty silhouette, text ghost, frame fragment, or unrelated redesign.

## Foreground selection plate

Ask the image model for a full-color selection aid, not final artwork:

> Keep the supplied full-card canvas, aspect ratio, framing, scale, silhouette, and overlap positions. Replace every scenery-only pixel with one flat saturated chroma green matte. Keep non-green all character pixels and every foreground card-interface region: header, title, rules text, symbols, panel material, credits, logos, edge decorations, and complete frame material, whether that material is opaque or translucent. When the source visibly places text on an opaque colored, textured, or framed panel, keep that complete panel non-green together with its text; never retain only the glyphs and replace their original opaque panel with green. When source text is intentionally printed directly over artwork with no backing, preserve that relationship and do not create a new panel. Keep dark ink, pale highlights, holes between limbs, and detached foreground marks correctly classified. Do not crop, recenter, rotate, reconstruct hidden anatomy, or leave scenery islands inside foreground regions. If any retained frame or panel is translucent, use this chroma result as the presence plate for the three-state workflow below instead of treating its Alpha as final.

The model may repaint retained colors or spell glyphs incorrectly. That is acceptable in this temporary plate because only the green/non-green semantic boundary is consumed. It is not acceptable for the model to move a silhouette, omit a visible element, merge a scenery hole, retain a scenery island, or classify glyphs as foreground while turning an opaque source-visible supporting panel green. It is equally wrong to invent a new panel behind text that has no backing in the source.

Run `prepare_foreground.py`. It converts chroma green to alpha and copies all RGB from the normalized source. Inspect the temporary `foreground-on-black.png`, `foreground-on-white.png`, and `foreground-alignment-overlay.png`. Require `source_rgb_preserved: true` in `foreground-report.json`, then remove these intermediates during final cleanup.

## Translucent frames and information panels

Use this branch only when the source visibly shows scenery through a transparent or translucent frame, glass panel, foil panel, or information backing. Do not mistake a merely textured opaque panel for transparency. If the classification is uncertain, preserve the visible source relationship for review instead of assigning the scenery to the frame.

Generate one flat three-state opacity plate at the exact source canvas:

> Produce a strictly registered three-tone foreground-opacity plate on the complete source canvas. Use pure black for independently moving scenery, including every scenery pixel visibly seen through a transparent frame or translucent information panel. Use uniform middle gray (#808080) only for the translucent UI material itself. Use pure white for opaque foreground pixels: the character, opaque effects, typography, symbols, logos, credits, opaque panel parts, and opaque frame strokes. When text sits on an opaque panel, make both white. When text has no backing, keep the text white and its surrounding scenery black. When text sits on translucent material, make the text and opaque strokes white, the material gray, and the scenery visible through it black. Preserve exact canvas, positions, silhouettes, overlaps, and layer order. Do not copy scenery colors into the mask, invent panels, flatten transparent material to white, or use gradients, shading, glow, texture, color, crop, or recentering.

Run:

```bash
python scripts/prepare_foreground.py \
  --source source.png \
  --opacity-selection foreground-opacity-selection.png \
  --presence-selection foreground-selection.png \
  --output-foreground foreground.png \
  --output-mask foreground-alpha.png \
  --output-black-preview foreground-on-black.png \
  --output-white-preview foreground-on-white.png \
  --output-overlay foreground-alignment-overlay.png \
  --output-report foreground-report.json
```

The chroma presence plate remains authoritative for whether a source pixel belongs to foreground, so black character ink, dark text strokes, and effect linework cannot become transparent merely because the three-state model rendered them black. Within that foreground, the script quantizes mid-gray to Alpha 144 and keeps all other present pixels opaque before edge feathering. Opaque RGB comes exactly from `source.png`; inside mid-gray material it replaces scene-contaminated detail with a normalized low-frequency color field sampled only from that material class. Tune `--translucent-alpha` only when the source clearly indicates a different material opacity, and tune `--material-color-radius` only when background motifs remain in the translucent tint. Require `selection_mode: three_state_opacity`, `presence_selection_used: true`, non-zero `translucent_material_coverage`, `opaque_source_rgb_preserved: true`, and `translucent_rgb_decontaminated: true`. Full-image `source_rgb_preserved` is expected to be false only because partial-alpha material was cleaned. Compare black and white previews: scenery must remain visible through the material, opaque text and dark linework must not fade, and no background motif may move with the frame or panel.

## Ambiguous enclosed scenery pockets

Do not force a pixel-perfect cut through a complex subject when the selection leaves several scenery fragments inside or beside a narrow limb, garment, hair strand, or frame junction. If those fragments surround one enclosed transparent pocket, assign that entire pocket to foreground depth as a single source-pixel patch. This trades a small amount of local parallax for a continuous undistorted subject and prevents neighboring copies of the same scenery from sliding against each other.

Use `bridge_foreground.py` with a seed inside the reviewed transparent pocket. The script fills the connected component only when it stays away from the canvas edge and remains under the configured coverage limit. It always rebuilds RGB from the normalized source. Review its red overlay and black/white previews before accepting it.

Do not use a depth-lock patch when the component opens into the main scenery, when a boundary would cut through a salient background shape, or when the total patch is large enough to erase useful depth. In those cases regenerate the selection plate. Never synthesize or repaint the subject for this correction.

## Full-foreground sketch highlight

Use the accepted transparent `foreground.png` as the edit target. Generate one complete line-style transformation rather than asking the model to identify, isolate, or reconstruct a character:

> Transform all visible non-transparent foreground content into a pure luminous line drawing. Trace the whole foreground, including the visible subject, energy effects, existing typography, numbers, symbols, information panels, logos, and decorative frame. Preserve the complete original canvas, aspect ratio, framing, scale, positions, overlaps, and transparent negative spaces. Use only thin, smooth, continuous white antialiased lines on a genuinely transparent background. Do not crop, recenter, rotate, stretch, rearrange, add content, complete concealed shapes, or reconstruct hidden anatomy. Do not use color, filled regions, gray shading, hatching, halftone, paper texture, glow blur, shadows, or a watermark.

Generate this as a style transformation of the supplied foreground, not as hidden-content completion. A comparison image may define line quality, but never copy it into project assets.

Some image services display transparency correctly but save an opaque checkerboard in RGB. Normalize either form with the bundled script; it only removes the generated backdrop and never re-detects source-image edges:

```bash
python scripts/prepare_generated_lineart.py \
  --reference foreground.png \
  --lineart structure-sketch-generated-raw.png \
  --output-structure structure-generated.png \
  --output-transparent structure-generated-transparent.png \
  --output-report structure-generated-report.json
```

Inspect the transparent preview. Reject filled regions, shaded areas, broad glow, missing major foreground groups, invented elements, or local geometry changes. Text spelling inside this temporary highlight map is less important than edge registration because its RGB is never shown, but the line placement must still follow the source foreground.

If the image service refuses, fails, or cannot produce a usable line drawing, do not retry with evasive wording and do not use local pixel-edge extraction. Continue the card without line emission by creating neutral maps:

```bash
python scripts/prepare_structure_maps.py \
  --foreground foreground.png \
  --disable-contour \
  --output-contour character_contour.png \
  --output-bloom character_bloom.png
```

The neutral files preserve the fixed five-asset runtime contract. Existing Flutter and Shader code can keep loading and sampling them; all contour and bloom samples evaluate to zero.

Keep the accepted normalized original as `source.png`; it is the runtime fallback and static card-shape Alpha mask. All other source copies, selection plates, masks, depth-lock overlays, per-stage previews, alignment overlays, aligned structures, and JSON reports are temporary. After the final checker passes, use `cleanup_assets.py`; leave exactly `source.png` plus the four derived runtime images.

## Alignment

The source, foreground, structure, and bloom always occupy the same full canvas. Never align independently cropped bounding boxes.

1. Create a red structure overlay on the foreground with `prepare_structure_maps.py --output-overlay`.
2. Check the subject silhouette, energy effects, typography, panels, and long frame runs.
3. Run `calibrate_structure.py` to estimate one safe full-canvas affine from the generated sketch to original source edges. Record its six forward coefficients and correlation report.
4. Prefer rejection and regeneration when local geometry changes. Automatic or manual affine is only for uniform framing drift.
5. Do not apply a UI occlusion mask: UI, text, panels, effects, and frame are intentionally part of this highlight layer.

## Map preparation

`prepare_structure_maps.py` performs full-canvas normalization, optional affine registration, foreground-alpha clipping, and two-scale bloom generation. With `--disable-contour`, it emits matching neutral-black contour and bloom maps instead.

For a 1000 px wide canvas, start with near radius `7` and wide radius `20`; the script scales both radii with canvas width. The contour file stays RGB-equivalent black/white. The bloom file stores near/wide luminance in R/G for two sampler-friendly scales.
