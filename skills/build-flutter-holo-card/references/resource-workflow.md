# Resource workflow

## Contents

- [Primary contract](#primary-contract)
- [Primary review loop](#primary-review-loop)
- [Colored layer prompts](#colored-layer-prompts)
- [Alpha preparation](#alpha-preparation)
- [Merged fallback](#merged-fallback)
- [Contour and bloom](#contour-and-bloom)
- [Deterministic checks](#deterministic-checks)

## Primary contract

Follow the same four visual roles as `$holo-card`:

| Role | Runtime file | Content |
|---|---|---|
| Character | `character.png` | One continuous colored main illustrated subject. Keep attached hair, fur, tails, clothing, handheld objects, and accessories. |
| Background | `background.png` | Complete opaque scenery, including areas concealed by character and UI. No subject, typography, panel, or frame residue. |
| UI | `foreground.png` | Combined original typography, numbers, symbols, information panels, credits, editorial insets, and entire decorative frame. |
| Structure | `character_contour.png` plus `character_bloom.png` | Thin source-visible character contours and their two-scale bloom. No UI or scenery lines. |

Subject-linked rings, auras, magic trails, and similar effects belong to the layer whose motion and occlusion they visually share. Never duplicate one effect in character and UI. Keep stacking fixed as `background -> character -> UI`.

Keep every layer on the source canvas. Generated layers may have another resolution only when their aspect ratio and full-canvas framing match; resize the entire canvas once and never fit a content bounding box.

## Primary review loop

Review each layer independently:

1. Generate or edit one layer.
2. Compare its visible artwork with the source at full canvas.
3. Prepare Alpha separately when required.
4. Inspect the transparent result over black and white.
5. Accept it, or repair/regenerate that same layer and repeat.

Missing Alpha, checkerboard residue, spelling drift, dirty boundaries, semantic contamination, geometry drift, and script failures all stay in this loop. They never select `merged-2d`.

Only an explicit provider safety/policy refusal of the independent-character request may leave this loop for the merged fallback. Preserve the actual refusal message. A vague failure, tool exception, timeout, or reviewer rejection is not a safety refusal.

## Colored layer prompts

Use the supplied card as the geometry reference. Keep prompts factual and limited to compositing.

### Character

> Prepare one continuous colored illustrated foreground layer for parallax compositing. Preserve every visible feature, color, texture, contour, pose, position, overlap, and scale without redrawing, simplifying, or omitting it. Keep attached hair, fur, tails, clothing, handheld objects, and accessories. Keep scenery, the decorative card frame, printed text, symbols, credits, legal marks, editorial inset portraits, and unrelated decorative subjects outside this layer. At small card-interface crossings, maintain only the local continuity already indicated by adjacent outlines, colors, shading, and texture so the foreground works as one coherent layer. Add no unrelated content and alter no visible artwork. Keep eyes, mouth interiors, dark ink, pale highlights, and shadows opaque. Preserve the complete canvas. Use genuine transparency when available; otherwise use one regular neutral checkerboard matte only outside the character.

Reject changed visible artwork, omitted visible parts, disconnected pieces, broad speculative additions, scenery/UI contamination, or independent fitting. Repair or regenerate the character; do not switch modes for these quality defects.

### Background

> Prepare a complete opaque color scenery-only plate covering the exact full-card canvas, including beneath the decorative border. Match visible scenery alignment and continue surrounding colors, shapes, directional strokes, and lighting through areas occupied by the illustrated subject and card interface. Keep subjects, printed text, symbols, panels, logos, credits, and the decorative frame outside this layer. Leave no transparent gaps, empty silhouettes, glyph fragments, or frame residue. Do not substitute an enlarged, blurred, darkened, or dimmed source image. Preserve the source aspect ratio and coordinate system.

Reject repeated subjects, empty silhouettes, text ghosts, frame fragments, holes, or unrelated redesign. Repair or regenerate the background in the same mode.

### UI

Keep final UI RGB from `source.png` for legibility and exact alignment. When the retained UI is opaque, ask the image model for a registered Alpha-selection aid, not repainted final UI:

> Produce a full-canvas grayscale Alpha mask registered exactly to the supplied card. White retains the source-visible typography, numerals, symbols, information bars and their actual backing panels, credits, editorial inset panels, and the entire decorative border/card frame. Black removes the main illustrated subject and independently moving scenery. Preserve antialiased boundaries as intermediate gray only where the source edge is genuinely partial. Keep frame and typography at one depth. Do not move, redraw, simplify, invent, or remove a panel, and do not include unrelated scenery islands.

When text has a source-visible backing, retain that actual backing. When it has none, do not invent one. When a translucent panel reveals scenery, retain only the panel material in UI; the scenery seen through it remains in background.

## Alpha preparation

Treat the generated color result and its Alpha as separate artifacts.

- Preserve genuine useful Alpha.
- For an opaque checkerboard/matte result, create one exact, registered grayscale mask for the actual returned image: `0` removes confirmed matte, `255` retains artwork, intermediate values preserve antialiased coverage.
- Build the mask only from inspected matte regions. Never globally remove green, gray, white, brightness, or saturation from the full canvas; those colors may belong to the character or UI.
- Include enclosed matte gaps between limbs, hair, clothes, accessories, and detached effects.
- A local Alpha repair may not change RGB, pose, geometry, or spelling.

For character normalization, use `prepare_generated_character.py --alpha-mask`. Also supply an independently reviewed source-space visible-subject mask. The tool must report zero missing visible coverage before it applies the Alpha-255 lock; otherwise repair the generated character or its mask and rerun.

For source-pixel UI or merged foreground, use `prepare_foreground.py --alpha-mask`. In merged mode, also supply the visible-subject mask so every accepted subject pixel is forced to Alpha 255.

Opaque layered UI:

```bash
python scripts/prepare_foreground.py \
  --source source.png \
  --alpha-mask foreground-alpha-mask.png \
  --layer-role interface \
  --output-foreground foreground.png \
  --output-mask foreground-alpha.png \
  --output-black-preview foreground-on-black.png \
  --output-white-preview foreground-on-white.png \
  --output-overlay foreground-alignment-overlay.png \
  --output-report foreground-report.json
```

Merged foreground uses the same command with `--layer-role merged`,
`--opaque-subject-mask foreground-visible-subject-mask.png`, and
`--output-opaque-subject-mask foreground-opaque-subject-mask.png`.

Use the three-state UI-material branch only when the source actually contains translucent material:

- black: independently moving scenery;
- middle gray: translucent UI material;
- white: opaque UI, text, strokes, and frame material.

Pass the three-state plate with `--opacity-selection` and a separately reviewed
grayscale `--presence-mask` that marks every retained UI pixel. This branch may
decontaminate scenery detail from translucent UI RGB. It must preserve opaque
source RGB exactly.

For the three-state branch, replace `--alpha-mask` in the command above with
`--opacity-selection foreground-opacity-selection.png --presence-mask
foreground-presence-mask.png`. Keep the merged-mode subject-mask arguments when
the subject belongs to `foreground.png`.

## Merged fallback

Enter this branch only when:

1. the user explicitly selected `effect=merged-2d`; or
2. the provider explicitly refused the independent-character generation request for safety/policy reasons and the selected mode permits fallback.

The merged foreground contains original source pixels for:

- the complete source-visible main subject, fully opaque;
- subject-linked effects that orbit, surround, frame, overlap, or are emitted or controlled by it;
- card UI, typography, panels, credits, editorial insets, and decorative frame.

Exclude independently moving scenery. Use a reviewed full-canvas Alpha mask; do not use a global chroma key. A quality defect in the primary character is not a reason to enter this branch.

## Contour and bloom

Use `character.png` as the contour owner in `layered-3d`, or `foreground.png` in `merged-2d`.

> Convert the accepted visible contour owner into thin, smooth white source-faithful line art on black or genuine transparency. Preserve lines visibly present in the owner: outer silhouettes, overlap and separation boundaries, and defining internal contours such as visible eyes, mouth lines, facial markings, fingers, hair or fur locks, garment seams or folds, and existing graphic pattern boundaries. Preserve the full canvas, position, scale, and overlaps. Add no line absent from the owner and no hidden completion, filled region, shading, hatching, halftone, noise, glow blur, material texture, paper texture, shadow, or watermark.

Internal source-visible contours are valid. Contour does not mean only the outer silhouette. A density measurement is diagnostic, not an automatic rejection.

Normalize and align:

```bash
python scripts/prepare_generated_lineart.py \
  --reference character.png \
  --lineart structure-lineart-generated-raw.png \
  --output-structure structure-generated.png \
  --output-transparent structure-generated-transparent.png \
  --output-report structure-generated-report.json

python scripts/calibrate_structure.py \
  --reference character.png \
  --structure structure-generated.png \
  --output-structure structure-aligned.png \
  --output-report structure-affine.json

python scripts/prepare_structure_maps.py \
  --foreground character.png \
  --structure structure-aligned.png \
  --output-contour character_contour.png \
  --output-bloom character_bloom.png \
  --output-overlay alignment-overlay.png
```

Replace `character.png` with `foreground.png` for `merged-2d`.

If line quality is wrong, regenerate the line art or correct one safe global affine. Never locally redraw contours. If the provider explicitly safety-refuses only this line-generation request, keep the current effect mode and create neutral maps with `prepare_structure_maps.py --disable-contour`.

## Deterministic checks

`check_assets.py` verifies only machine-observable invariants:

- matching full canvases;
- background opacity across the source card shape;
- useful transparent regions in movable layers;
- full opacity of source-visible subject pixels;
- source RGB preservation for opaque source-pixel foreground;
- grayscale opaque contour, packed opaque bloom, and contour-owner clipping.

Coverage and line-density values are diagnostics. They cannot determine whether a large character, sparse UI, translucent frame, or detailed contour is semantically correct and therefore must not select fallback or fail an otherwise valid file by themselves.

The user/reviewer decides whether subject, scenery, UI, transparency, and contour membership are visually correct. Keep temporary overlays until that review passes, then run cleanup.
