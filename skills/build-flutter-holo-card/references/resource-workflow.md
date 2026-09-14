# Resource workflow

## Layer contract

| Asset | Required content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete scenery only, including repaired concealed regions | Opaque inside the card boundary; exterior rounded corners may stay transparent |
| Foreground | Original source pixels for the fully opaque main subject, subject-linked visual elements, the subject-specific frame, card interface, and card frame; low-frequency color field plus partial Alpha only for actually translucent non-subject material | Transparent where unrelated scenery remains independently moving, including scenery visible through translucent UI material |
| Structure | Model-generated smooth white source-faithful contours for the accepted foreground, including visible internal defining lines but excluding lines absent from the source and added shading or texture strokes; neutral black when disabled | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0; neutral black when disabled | Opaque |

The character and card interface intentionally share one runtime depth. A temporary subject or UI selection mask may be used while preparing resources, but do not expose another moving character layer.

## Background generation prompt

Use the source as the only geometry reference:

> Reconstruct a complete scenery-only plate on the exact original full-card canvas. Keep it opaque throughout the visible card boundary while preserving any transparent exterior rounded corners. Remove the main illustrated subject, all typography, numbers, symbols, panels, logos, credits, and the decorative card frame. Continue surrounding colors, shapes, clouds, stars, strokes, and lighting naturally through every concealed region. Provide enough coherent surrounding scenery for a two-times moving crop. Preserve the source aspect ratio and coordinate system; do not crop, recenter, add a new subject, leave silhouettes, or retain glyph fragments.

Reject a result containing a faint subject, empty silhouette, text ghost, frame fragment, or unrelated redesign.

## Foreground selection plates

The foreground is a semantic composition, not every decorative pixel above the scenery. Include:

- the complete source-visible main subject;
- subject-linked visual elements that orbit, surround, frame, overlap, or are emitted or controlled by the subject, such as a star ring, energy ring, aura, magic trail, or subject-dedicated portrait frame; direct pixel contact is not required;
- the card frame and all source-visible information, typography, numbers, symbols, logos, credits, and their actual panel material.

Exclude ambient stars, clouds, foliage, distant lights, scenery texture, and unrelated decorative streaks. Similar color or style does not make an element subject-linked. Never include a patch of background simply because it sits in a difficult gap between the subject and the frame.

For example, when a star ring or energy ring wraps around the subject and crosses in front of or behind it, keep every source-visible arc of that ring in foreground even if some arcs are detached from the subject by transparent gaps. Keep the scenery visible between those arcs in background.

Ask the image model for a full-color selection aid, not final artwork:

> Keep the supplied full-card canvas, aspect ratio, framing, scale, silhouette, and overlap positions. Replace every unrelated scenery pixel with one flat saturated chroma green matte. Keep non-green the complete source-visible main subject; every visual element compositionally linked to it by orbiting, surrounding, framing, overlapping, or being emitted or controlled by it, including detached portions of the same ring or aura; any frame dedicated to the subject artwork; and every card-interface region including header, title, rules text, symbols, actual panel material, credits, logos, edge decoration, and card frame. Direct contact with the subject is not required for a linked element. Exclude ambient stars, clouds, foliage, distant lights, scenery textures, and unrelated decorative streaks even when their colors or shapes resemble subject-linked effects. When the source visibly places text on an opaque colored, textured, or framed panel, keep that complete panel non-green together with its text; never retain only the glyphs and replace their original opaque panel with green. When source text is intentionally printed directly over artwork with no backing, preserve that relationship and do not create a new panel. Keep dark ink, pale highlights, holes between limbs, and detached subject-linked marks correctly classified. Do not crop, recenter, rotate, reconstruct hidden anatomy, add background pockets, or leave unrelated scenery islands inside foreground regions. If any retained frame or panel is translucent, use this chroma result as the presence plate for the three-state workflow below instead of treating its Alpha as final.

The model may repaint retained colors or spell glyphs incorrectly. That is acceptable in this temporary plate because only the green/non-green semantic boundary is consumed. It is not acceptable for the model to move a silhouette, omit a visible subject-linked element, merge a scenery hole, retain an unrelated scenery island, or classify glyphs as foreground while turning an opaque source-visible supporting panel green. It is equally wrong to invent a new panel behind text that has no backing in the source.

Generate a second, independent opacity-lock plate:

> Produce a strictly registered pure black-and-white main-subject selection on the complete source canvas. Use pure white for every source-visible pixel of the main illustrated subject, including dark linework, pale highlights, limbs, clothing, hair or fur, and visible parts interrupted by foreground overlaps. Use pure black for subject-linked effects, rings, auras, subject frames, card interface, text, panels, card frame, and all scenery. Do not feather, shade, add gray, crop, recenter, complete concealed anatomy, infer hidden geometry, or include anything other than the visible main subject.

Save it as `foreground-opaque-subject-selection.png`. This plate does not create a separately moving layer. It only guarantees that subject pixels within the accepted foreground have Alpha 255.

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
  --opaque-subject-selection foreground-opaque-subject-selection.png \
  --output-foreground foreground.png \
  --output-opaque-subject-mask foreground-opaque-subject-mask.png \
  --output-mask foreground-alpha.png \
  --output-black-preview foreground-on-black.png \
  --output-white-preview foreground-on-white.png \
  --output-overlay foreground-alignment-overlay.png \
  --output-report foreground-report.json
```

The chroma presence plate remains authoritative for whether a source pixel belongs to foreground, so black subject pixels, dark text strokes, and effect linework cannot disappear merely because the three-state model rendered them black. The independent subject plate is then applied as a hard Alpha-255 lock. Within the remaining foreground, the script quantizes mid-gray to Alpha 144 and keeps other present pixels opaque before edge feathering. Opaque RGB comes exactly from `source.png`; inside mid-gray non-subject material it replaces scene-contaminated detail with a normalized low-frequency color field sampled only from that material class. Tune `--translucent-alpha` only when the source clearly indicates a different material opacity, and tune `--material-color-radius` only when background motifs remain in the translucent tint. Require `selection_mode: three_state_opacity`, `presence_selection_used: true`, non-zero `translucent_material_coverage`, `opaque_source_rgb_preserved: true`, `translucent_rgb_decontaminated: true`, `subject_fully_opaque: true`, and zero `opaque_subject_missing_coverage`. Full-image `source_rgb_preserved` is expected to be false only because partial-alpha material was cleaned. Compare black and white previews: the main subject must never fade, scenery must remain visible through translucent non-subject material, opaque text and dark linework must not fade, and no background motif may move with the frame or panel.

## Ambiguous boundaries

When the cut around a limb, garment, hair or fur strand, subject-linked effect, or frame junction is ambiguous, regenerate the selection aids with a more explicit semantic prompt. Never fill the gap with scenery, bridge an enclosed background pocket into foreground, synthesize the subject, or repaint retained pixels. The independent subject plate must still cover every source-visible main-subject pixel, and the foreground-presence plate must still exclude unrelated scenery.

## Source-faithful contour highlight

Use the accepted transparent `foreground.png` as the edit target. `Contour-only` is a provenance and rendering rule: keep lines that are visibly present in the source and omit filled shading or synthesized texture. It is not a positional rule and never means external silhouette only. A line must not be rejected merely because it lies inside the subject.

Generate one source-faithful line transformation rather than asking the model to identify, isolate, beautify, or reconstruct a character:

> Convert the visible non-transparent foreground into a pure luminous source-faithful line drawing. Preserve contours already visibly present in the supplied foreground: outer silhouettes; visible overlap and separation boundaries; and internal defining contours such as eyes, mouths, facial or cheek markings, fingers, hair or fur locks, garment seams and folds, existing pattern outlines, typography, numbers, symbols, subject-linked effect lines, information-panel borders, logos, subject-frame details, and card-frame details. These source-visible internal contours are valid and must not be removed or rejected merely because they are internal, facial, anatomical, textile, decorative, or part of the interface. Preserve the complete original canvas, aspect ratio, framing, scale, positions, overlaps, and transparent negative spaces. Use only thin, smooth, continuous white antialiased lines on a genuinely transparent background. Never create a line absent from the source, infer a line behind an occlusion, invent anatomy or features, add eyelashes or fur strokes, add garment folds or patterns, or introduce shading, cross-hatching, halftone, noise, highlight texture, material texture, filled regions, gray shading, paper texture, glow blur, shadows, or a watermark. Do not crop, recenter, rotate, stretch, rearrange, add content, complete concealed shapes, or reconstruct hidden anatomy.

Positive examples are a visible eye rim, mouth line, cheek-mark boundary, finger separation, garment seam, or printed pattern outline already present in the source. Negative examples are a new eyelash, a reconstructed hidden finger, extra fur strands, an invented clothing fold, or hatching added to suggest volume.

Generate this as a style transformation of the supplied foreground, not as hidden-content completion. A comparison image may define line quality, but never copy it into project assets.

Some image services display transparency correctly but save an opaque checkerboard in RGB. Normalize either form with the bundled script; it only removes the generated backdrop and never re-detects source-image edges:

```bash
python scripts/prepare_generated_lineart.py \
  --reference foreground.png \
  --lineart structure-lineart-generated-raw.png \
  --output-structure structure-generated.png \
  --output-transparent structure-generated-transparent.png \
  --output-report structure-generated-report.json
```

Inspect the transparent preview against the source at full size. Accept source-visible internal defining contours and never reject them solely for being inside the subject. Reject strokes absent from the source, inferred hidden geometry, invented facial or anatomical features, extra hair, fur, fabric, pattern, or decorative marks, and any shading, hatching, noise, highlight texture, or material texture. Also reject filled regions, broad glow, missing major foreground groups or defining contours, background lines in transparent foreground regions, and local geometry changes. Text spelling inside this temporary highlight map is less important than contour registration because its RGB is never shown, but line placement must still follow the source foreground.

If the image service refuses, fails, or cannot produce a usable line drawing, do not retry with evasive wording and do not use local pixel-edge extraction. Continue the card without line emission by creating neutral maps:

```bash
python scripts/prepare_structure_maps.py \
  --foreground foreground.png \
  --disable-contour \
  --output-contour character_contour.png \
  --output-bloom character_bloom.png
```

The neutral files preserve the fixed five-asset runtime contract. Existing Flutter and Shader code can keep loading and sampling them; all contour and bloom samples evaluate to zero.

Keep the accepted normalized original as `source.png`; it is the runtime fallback and static card-shape Alpha mask. All other source copies, selection plates, subject-opacity masks, per-stage previews, alignment overlays, aligned structures, and JSON reports are temporary. After the final checker passes, use `cleanup_assets.py`; leave exactly `source.png` plus the four derived runtime images.

## Alignment

The source, foreground, structure, and bloom always occupy the same full canvas. Never align independently cropped bounding boxes.

1. Create a red structure overlay on the foreground with `prepare_structure_maps.py --output-overlay`.
2. Check the subject silhouette, source-visible internal defining contours, subject-linked effects, typography, panels, and long frame runs. Accept registered internal contours; reject only missing, displaced, hidden-completion, or model-invented lines and added shading or texture strokes.
3. Run `calibrate_structure.py` to estimate one safe full-canvas affine from the generated contour drawing to original source edges. Record its six forward coefficients and correlation report.
4. Prefer rejection and regeneration when local geometry changes. Automatic or manual affine is only for uniform framing drift.
5. Do not apply a UI occlusion mask: UI, text, panels, effects, and frame are intentionally part of this highlight layer.

## Map preparation

`prepare_structure_maps.py` performs full-canvas normalization, optional affine registration, foreground-alpha clipping, and two-scale bloom generation. With `--disable-contour`, it emits matching neutral-black contour and bloom maps instead.

For a 1000 px wide canvas, start with near radius `7` and wide radius `20`; the script scales both radii with canvas width. The contour file stays RGB-equivalent black/white. The bloom file stores near/wide luminance in R/G for two sampler-friendly scales.
