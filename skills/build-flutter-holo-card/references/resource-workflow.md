# Two-layer resource workflow

## Visual ownership

Classify the complete source into two visual planes:

| Plane | Runtime file | Content |
|---|---|---|
| Background | `background.png` | Scenery only, fully repaired beneath every foreground object and the card interface. |
| Foreground | `foreground.png` | Every character, foreground object/effect, title, number, symbol, panel, credit, inset, and decorative frame, preserving the source overlap order. |

Do not split the character from the card interface. A subject-linked ring, aura, trail, weapon, or accessory belongs in foreground. Ordinary sky, architecture, landscape, fog, particles, and texture belong in background unless they clearly sit in front of the subject or interface.

Keep every image on the source canvas. A generated background may use another resolution only when its aspect ratio and full-canvas framing match; resize the entire canvas once, never a content bounding box.

The rectangular PNG canvas is not the card shape. `source.png` must have a reviewed antialiased card-shape Alpha with transparent outer corners. `foreground.png` is clipped to that Alpha. `background.png` stays opaque and full-bleed so shifted sampling never exposes an empty edge.

## 1. Normalize the source

```bash
python scripts/normalize_source.py --source input.png --output source.png --width 1000
```

Omit shape arguments only when the supplied file already has useful card-shaped transparency. For an opaque rectangular card, measure the visible corner radius and pass `--corner-radius-ratio`; for a nonstandard outline, pass a reviewed full-canvas grayscale `--card-mask`.

Never chroma-key the source corners. The same colors may be part of the artwork.

## 2. Repair the background

Use `source.png` as the geometry reference:

> Produce a complete opaque scenery-only plate on the exact full card canvas. Preserve the visible scenery's composition, perspective, color, directional strokes, texture scale, and lighting, and continue it coherently through every region occupied by characters, foreground objects, typography, panels, symbols, credits, and the decorative frame. Remove all foreground and interface residue, including silhouettes, glyph fragments, borders, and shadows belonging to those elements. Do not crop, recenter, enlarge, blur, dim, or redesign the source. Keep the exact canvas and aspect ratio and fill every pixel opaquely.

Review at full size. Reject repeated subjects, silhouettes, text ghosts, frame fragments, holes, obvious cloning, or a shifted composition. Repair the background itself; there is no alternate effect route.

## 3. Build the combined foreground

Create one registered full-canvas grayscale Alpha mask for the supplied source:

> Produce a full-canvas grayscale Alpha mask registered exactly to the supplied card. White retains every non-background element: all characters and attached details, foreground objects and effects, typography, numerals, symbols, panels and their backing material, credits, insets, logos, and the entire decorative frame. Black removes independently moving scenery. Use intermediate gray only for genuine antialiased boundaries. Preserve the exact canvas, position, scale, and overlap order. Do not move, redraw, simplify, invent, or omit any element.

Build the foreground from source RGB rather than generated color:

```bash
python scripts/prepare_foreground.py \
  --source source.png \
  --alpha-mask foreground-alpha-mask.png \
  --output-foreground foreground.png \
  --output-mask foreground-alpha.png \
  --output-black-preview foreground-on-black.png \
  --output-white-preview foreground-on-white.png \
  --output-overlay foreground-alignment-overlay.png \
  --output-report foreground-report.json
```

The mask must include enclosed gaps correctly and must not retain scenery islands. Treat translucent-looking source elements as source-faithful foreground pixels unless the user explicitly asks for a more complex transmissive material model; guessed transparency usually double-composites baked scenery and is less stable than an opaque source pixel.

Inspect foreground over black and white. The two-layer flat composite at neutral UV must reproduce the source within the repaired-background regions hidden by foreground.

## 4. Generate sketch contours for the whole foreground

Use `foreground.png`, not the flat source, as the line-art reference:

> Convert every visible element in this accepted foreground layer into thin, smooth white sketch line art on a uniform solid-black background. Preserve the exact full canvas, position, scale, and overlap order. Include source-visible silhouettes and defining internal contours from all characters, hair, faces, clothing, objects, foreground effects, typography, numerals, symbols, panels, credits, logos, insets, and the decorative frame. Keep small text legible as simplified contour strokes without filling its glyph interiors. Add no hidden completion, scenery edge, filled white region, shading, hatching, halftone, material texture, paper texture, shadow, glow blur, or watermark.

An opaque result must use a solid black matte. Do not accept a checkerboard preview as line art; the normalizer rejects bright matte outside the foreground owner.

Normalize and build maps:

```bash
python scripts/prepare_generated_lineart.py \
  --reference foreground.png \
  --lineart structure-lineart-generated-raw.png \
  --output-structure structure-generated.png \
  --output-transparent structure-generated-transparent.png \
  --output-report structure-generated-report.json

python scripts/prepare_structure_maps.py \
  --foreground foreground.png \
  --structure structure-generated.png \
  --output-contour foreground_contour.png \
  --output-bloom foreground_bloom.png \
  --output-overlay alignment-overlay.png
```

Regenerate line art whenever its full-canvas registration or local geometry is wrong. Do not use global or local warping to force a mismatched result into place.

## 5. Validate and clean

```bash
python scripts/check_assets.py \
  --source source.png \
  --background background.png \
  --foreground foreground.png \
  --contour foreground_contour.png \
  --bloom foreground_bloom.png \
  --output-report check-report.json
```

The checker verifies canvas, Alpha, source-RGB, map-format, and alignment invariants. It cannot decide whether the foreground mask includes every intended element, whether repaired scenery is plausible, or whether the generated sketch lines faithfully cover every foreground element. Those remain mandatory visual reviews.

After deterministic and visual review pass:

```bash
python scripts/cleanup_assets.py --output-dir .
```

Keep only `source.png`, `background.png`, `foreground.png`, `foreground_contour.png`, and `foreground_bloom.png`.
