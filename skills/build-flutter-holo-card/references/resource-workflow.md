# Resource workflow

## Effect selection and layer contracts

Use layered-3d first for auto. It keeps six runtime images:

| Asset | Layered-3d content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete repaired scenery only | Opaque inside the card boundary |
| Character | One continuous colored main subject with attached details; include subject-linked effects only when they move compositionally with the subject | Transparent outside character/effects; every source-visible subject pixel is Alpha 255 |
| Foreground | Original source pixels for interface, text, panels, frame, and subject-linked effects not assigned to character | Transparent outside retained upper-layer material |
| Structure | Source-faithful contours derived only from character | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0 | Opaque |

Merged-2d is the five-image fallback:

| Asset | Merged-2d content | Required transparency |
|---|---|---|
| Source | Supplied card, normalized without cropping | Preserve source |
| Background | Complete repaired scenery only | Opaque inside the card boundary |
| Foreground | Original source pixels for the fully opaque visible subject, subject-linked effects, interface, panels, and frame | Transparent where scenery remains independently moving |
| Structure | Source-faithful contours derived from merged foreground | Opaque black canvas |
| Bloom | Near blur in R, wide blur in G, B=0 | Opaque |

Never retain the main subject in both character.png and foreground.png. That duplicates it as soon as parallax begins.

## Background generation prompt

Use the source as the only geometry reference:

> Reconstruct a complete scenery-only plate on the exact original full-card canvas. Keep it opaque throughout the visible card boundary while preserving any transparent exterior rounded corners. Remove the main illustrated subject, all typography, numbers, symbols, panels, logos, credits, and the decorative card frame. Continue surrounding colors, shapes, clouds, stars, strokes, and lighting naturally through every concealed region. Provide enough coherent surrounding scenery for a two-times moving crop. Preserve the source aspect ratio and coordinate system; do not crop, recenter, add a new subject, leave silhouettes, or retain glyph fragments.

Reject a result containing a faint subject, empty silhouette, text ghost, frame fragment, or unrelated redesign.

## Layered-3d character

Use the source as the geometry reference and generate one colored character plate:

> Prepare one continuous colored illustrated character layer on the exact full-card canvas for parallax compositing. Preserve every source-visible feature, color, texture, contour, pose, position, overlap, and scale. Keep attached hair, fur, tails, clothes, handheld objects, and accessories. Keep a subject-linked ring, aura, emitted effect, or subject-dedicated visual element with the character only when it must share the character's motion; otherwise assign it to the upper foreground. Exclude scenery, typography, numbers, panels, logos, credits, decorative card frame, and editorial inset portraits. Where a small interface crossing interrupts the character, continue only the local shape and color continuity already established by immediately adjacent visible artwork so the layer does not split during parallax. Do not infer identity, reconstruct broad hidden anatomy, add unrelated content, redesign visible artwork, crop, recenter, rotate, or rescale. Place only the character layer over genuine transparency or one uniform chroma-green matte.

This branch has a stricter visual gate than the fallback. Reject any changed visible face, hand, limb, clothing, accessory, effect, pose, line, color, or scale. Reject missing fragments, broad invented hidden content, scenery/UI/frame contamination, or inconsistent geometry across an interface crossing.

Generate character-visible-selection.png from the source:

> Produce a strictly registered pure black-and-white source-visible main-subject selection on the complete source canvas. White covers every visible pixel of the main illustrated subject and any subject-linked effect assigned to the character layer. Black covers scenery, interface, text, panels, frame, and every hidden or merely inferred region. Do not feather, shade, add gray, crop, recenter, or complete concealed anatomy.

If the colored character has no useful Alpha, also generate character-selection.png from the colored result, not from a different composition:

> Keep the generated character artwork and exact canvas unchanged. Replace only its outside matte with one flat saturated chroma green. Keep every character and assigned effect pixel non-green, including enclosed gaps and detached effect fragments. Do not repaint, shift, simplify, crop, or add content.

Normalize it with prepare_generated_character.py. A non-zero missing-visible coverage fails the branch; do not use the hard opacity lock to disguise missing generated artwork. Inspect the color result, black/white composites, and edge overlay before accepting it.

## Layered-3d upper foreground

Build foreground.png from source pixels only. Include interface, typography, numbers, panels, logos, credits, decorative card frame, editorial inset portraits, and subject-linked effects assigned above the character. Exclude the main character, every effect already assigned to character.png, and all scenery.

Generate the same chroma presence and optional three-state opacity plates described below, but target only this upper foreground. Run prepare_foreground.py with --layer-role interface and without the opaque-subject arguments. Opaque output pixels must remain exact source RGB. Translucent interface material may use the existing three-state decontamination branch.

Accept the primary split only when the flat composite exactly restores the source-visible card and tilted review shows no duplicated subject, missing UI, or scenery attached to the upper foreground. If either character or upper foreground fails, delete the failed primary outputs, record the reason, and continue with merged-2d.

## Merged-2d fallback foreground selection plates

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

For layered-3d upper foreground, override the character clause above: make the character black because it belongs to character.png, and make white only the opaque effects, interface, panels, information, and frame assigned to foreground.png. For merged-2d, keep the character white.

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

Use character.png as the edit target in layered-3d and foreground.png in merged-2d. Contour-only is a provenance and rendering rule: keep lines visibly present in the accepted owner and omit filled shading or synthesized texture. It is not a positional rule and never means external silhouette only. A line must not be rejected merely because it lies inside the subject.

Generate one source-faithful line transformation rather than asking the model to identify, isolate, beautify, or reconstruct a character:

> Convert the visible non-transparent contour owner into a pure luminous source-faithful line drawing. Preserve contours already visibly present in that owner: outer silhouettes; visible overlap and separation boundaries; and internal defining contours such as eyes, mouths, facial or cheek markings, fingers, hair or fur locks, garment seams and folds, existing pattern outlines, typography, numbers, symbols, subject-linked effect lines, information-panel borders, logos, subject-frame details, and card-frame details when those elements actually belong to the selected owner. These source-visible internal contours are valid and must not be removed or rejected merely because they are internal, facial, anatomical, textile, decorative, or part of the interface. Preserve the complete original canvas, aspect ratio, framing, scale, positions, overlaps, and transparent negative spaces. Use only thin, smooth, continuous white antialiased lines on a genuinely transparent background. Never create a line absent from the owner, infer a line behind an occlusion, invent anatomy or features, add eyelashes or fur strokes, add garment folds or patterns, or introduce shading, cross-hatching, halftone, noise, highlight texture, material texture, filled regions, gray shading, paper texture, glow blur, shadows, or a watermark. Do not crop, recenter, rotate, stretch, rearrange, add content, complete concealed shapes, or reconstruct hidden anatomy.

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

The neutral files preserve the selected five- or six-asset runtime contract. Existing Flutter and Shader code keeps loading and sampling them; all contour and bloom samples evaluate to zero.

Keep the accepted normalized original as source.png; it is the runtime fallback and static card-shape Alpha mask. All other source copies, selection plates, subject-opacity masks, per-stage previews, alignment overlays, aligned structures, and JSON reports are temporary. After the final checker passes, use cleanup_assets.py with the effective mode; leave six runtime images for layered-3d or five for merged-2d.

## Alignment

The source, selected contour owner, structure, and bloom always occupy the same full canvas. Never align independently cropped bounding boxes.

1. Create a red structure overlay on character in layered-3d or foreground in merged-2d with prepare_structure_maps.py --output-overlay.
2. Check the owner silhouette and source-visible internal defining contours. In layered-3d, structure must not include UI, panels, text, or frame. Accept registered internal contours; reject missing, displaced, wrong-owner, hidden-completion, or model-invented lines and added shading or texture strokes.
3. Run `calibrate_structure.py` to estimate one safe full-canvas affine from the generated contour drawing to original source edges. Record its six forward coefficients and correlation report.
4. Prefer rejection and regeneration when local geometry changes. Automatic or manual affine is only for uniform framing drift.
5. Do not bake a separate UI occlusion mask into the contour file. In layered-3d, the shader masks character emission with live foreground Alpha; in merged-2d, interface and subject already share the contour owner.

## Map preparation

`prepare_structure_maps.py` performs full-canvas normalization, optional affine registration, foreground-alpha clipping, and two-scale bloom generation. With `--disable-contour`, it emits matching neutral-black contour and bloom maps instead.

For a 1000 px wide canvas, start with near radius `7` and wide radius `20`; the script scales both radii with canvas width. The contour file stays RGB-equivalent black/white. The bloom file stores near/wide luminance in R/G for two sampler-friendly scales.
