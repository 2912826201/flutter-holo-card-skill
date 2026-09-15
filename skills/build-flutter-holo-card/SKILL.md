---
name: build-flutter-holo-card
description: Build and validate Flutter holographic cards from one raster card image. Uses a holo-card-compatible three-layer primary effect with repaired scenery, a continuous character, source-faithful UI/frame, signed parallax, contour glow, foil, and touch-safe tilt. Supports asset-only or full implementation plus auto, layered-3d, and merged-2d selection. In auto mode, keep repairing the primary route for technical or quality failures and use merged-2d only after an explicit image-provider safety or policy refusal of independent-character generation.
---

# Build Flutter Holo Card

Use the `$holo-card` composition as the primary standard:

1. repaired opaque scenery;
2. one continuous colored character and its structure glow;
3. complete typography, panels, symbols, credits, and decorative frame above the character, including UI segments originally hidden by it.

Keep the stacking order `background -> character -> UI` at every signed depth. A quality defect is a request to repair the current layer, never permission to change effect mode.

Before running bundled Python scripts, install missing dependencies with `python -m pip install -r requirements.txt`. Do not replace the scripts with ad-hoc extraction code.

## Select scope and effect

Select one scope:

- **asset-only:** Generate, prepare, align, validate, and clean runtime images only. Do not modify application code.
- **full:** Complete the resource workflow, then integrate the Flutter component and tests.

Select one effect:

- **effect=auto (default):** Start and remain on `layered-3d`. Switch to `merged-2d` only when the image provider explicitly returns a safety/policy refusal for the independent-character generation request.
- **effect=layered-3d:** Use the same primary route. An explicit safety/policy refusal may fall back unless the user also specifies `strict=true`; strict mode stops and reports the refusal.
- **effect=merged-2d:** Skip independent-character generation because the user explicitly selected the compatible two-layer effect.

Scope and effect are independent. Always report `requested_effect`, `effective_effect`, and the provider's exact `fallback_reason` when they differ.

## Classify outcomes before acting

Use these mutually exclusive outcomes:

| Outcome | Evidence | Required action |
|---|---|---|
| Explicit safety refusal | The image provider explicitly says the request violates safety, policy, legality, or content rules | Preserve the exact message. For a refused character request, follow the selected fallback rule. Do not evade or reword around the refusal. |
| Technical failure | Timeout, transport error, tool crash, missing Alpha, opaque matte, wrong file format, or interrupted generation without a policy refusal | Resume or retry the same primary stage. Never change effect mode. |
| Quality failure | Missing/shifted artwork, dirty matte, repeated scenery, bad spelling, wrong layer membership, alignment drift, or a failed visual review | Repair or regenerate only that layer and review it again. Never change effect mode. |
| Deterministic validation failure | A bundled script reports a canvas, Alpha, RGB, map-format, or alignment invariant | Fix the inputs or preparation step in the current mode, then rerun the check. Never change effect mode. |

Do not infer a safety refusal from words such as `failed`, `unusable`, `cannot isolate`, `review rejected`, or a non-zero script exit code. Only an explicit refusal payload returned by the image generation/edit provider for the independent-character request qualifies. The agent's own quality judgment is never refusal evidence. Preserve the provider message verbatim.

If a technical failure still cannot be recovered after reasonable retries, report that primary stage as blocked and retain its intermediates for diagnosis. Do not manufacture a policy reason and do not change effect mode.

If shared background generation is explicitly refused, stop and report it: `merged-2d` also requires that background and therefore cannot honestly bypass the refusal. If contour generation alone is explicitly refused, keep the selected effect mode and create the neutral contour/bloom pair; this is a line-effect fallback, not an effect-mode fallback.

## Establish the resource contract

Read [references/resource-workflow.md](references/resource-workflow.md) before generating or repairing images.

Preserve one full canvas and aspect ratio for every file. Never independently crop, fit, recenter, stretch, or locally warp a layer.

`layered-3d` delivers six runtime images:

- `source.png`: normalized supplied card with clean antialiased transparent corners; its Alpha is the static card-shape mask;
- `background.png`: complete scenery with concealed areas repaired;
- `character.png`: continuous colored character, transparent outside it;
- `foreground.png`: complete UI/frame and any intentionally upper subject-linked effect, with character-occluded UI continuity restored;
- `character_contour.png`: opaque grayscale structure core;
- `character_bloom.png`: opaque two-scale packed bloom.

`merged-2d` delivers the same set without `character.png`; `foreground.png` then contains the source-visible subject, its linked effects, UI, and frame.

Never retain the main subject in both `character.png` and `foreground.png`.

## Build and review resources

1. Normalize the source without cropping and establish its static card-shape Alpha:

```bash
python scripts/normalize_source.py --source input.png --output source.png --width 1000
```

Omit shape arguments only when the supplied image already has useful transparent card corners. For an opaque rectangular input, inspect the actual outline and pass either `--corner-radius-ratio 0.05` (replace `0.05` with the measured width-relative radius) or a reviewed full-canvas grayscale `--card-mask card-shape-mask.png`. Never accept opaque corner pixels in `source.png`.

2. Generate the colored primary layers using the exact prompts and review loop in the resource workflow. Treat generated color and Alpha preparation as separate stages.
3. When a character or UI result contains an opaque matte, prepare one reviewed, full-canvas grayscale Alpha mask for the actual returned image. Do not globally remove a color from artwork. Normalize the character with:

```bash
python scripts/prepare_generated_character.py \
  --source source.png \
  --character character-generated.png \
  --alpha-mask character-alpha-mask.png \
  --visible-subject-mask character-visible-mask.png \
  --output-character character.png \
  --output-visible-subject-mask foreground-opaque-subject-mask.png \
  --output-black-preview character-on-black.png \
  --output-white-preview character-on-white.png \
  --output-overlay character-alignment-overlay.png \
  --output-report character-report.json
```

Omit `--alpha-mask` only when the returned file has genuine useful Alpha. The visible-subject mask is an independently reviewed source-space mask; it guarantees that every source-visible subject pixel is Alpha 255 but must not hide missing generated artwork.

4. Inspect every character/UI crossing before preparing `foreground.png`. In `layered-3d`, always normalize the final order to `character -> complete UI`, even where the source character was painted over the UI. Preserve source pixels for visible UI and generate only the concealed continuation needed to complete an interrupted frame, panel, information bar, or UI stroke. Pass that generated completion and its exact hidden-region mask through `prepare_foreground.py`; never leave a transparent notch around the character. Use the three-state material branch only when the source visibly contains translucent UI through which scenery is visible. Machine checks verify file invariants; the user or reviewer decides semantic membership and visual quality.
5. Generate structure from `character.png` in `layered-3d` or `foreground.png` in `merged-2d`. Contour is provenance-based, not position-based: retain source-visible silhouettes, overlaps, and defining internal lines, but add no absent line, shading, hatching, or texture synthesis.
6. Normalize, globally calibrate when needed, and build the contour/bloom maps. A calibration or density warning requests review or regeneration; it never changes the selected effect.
7. Run `scripts/check_assets.py`. Treat its `errors` as deterministic invariants to fix in the current mode. Treat `warnings` and `required_visual_review` as review items, not automatic rejection or fallback triggers.
8. After the current mode passes review, run `cleanup_assets.py --effect-mode <effective mode>`. Retain only the five or six runtime images.

If an asset-only request was selected, report the runtime paths and checks, then stop.

## Implement Flutter rendering

Read [references/rendering-contract.md](references/rendering-contract.md). Copy the templates under `assets/flutter/` into the nearest appropriate feature directory and adapt existing project image wrappers rather than creating a competing abstraction.

Preserve these behaviors:

- optional character input selects `layered-3d`; absence selects `merged-2d` in the same component;
- use one amplified view vector for all parallax and material motion while keeping physical card tilt small;
- use the holo-card UV coefficients for background, character, and UI;
- in `layered-3d`, paint on an unclipped 160% transparent surface so positive depth can extend character/UI outside the clipped background;
- the complete UI always covers character, contour emission, and bloom, regardless of the mixed overlap order in the supplied flat image;
- keep the foil sweep oriented lower-left to upper-right;
- keep static state free of foil/glare, record touch-down as the zero-delta origin, and animate release continuously;
- use neutral black contour/bloom maps to disable refused line generation without a Shader branch.

Do not add normal, height, or roughness maps unless the user asks for a different material model.

## Validate and hand off

For resources, inspect each actual layer at full canvas and compare the flat composite before enabling glow. In `layered-3d`, also test signed depth `-3`, `0`, and `+3`; reject duplicated subjects, holes, moving text, dirty matte, contour drift, or any exposed break where a moving character crosses a frame/panel/UI stroke. A source crossing may intentionally change only where the completed UI is moved above a character that originally covered it.

For full implementation:

1. Test resource and Shader loading for six-image and five-image contracts.
2. Test default, narrow, and wide constraints.
3. Test touch-down with zero view, drag response on both axes, continuous release, and increased internal sensitivity without increased physical rotation.
4. Run targeted formatting, analysis, Widget tests, and a debug bundle build.

Report exact paths, commands run, unrun checks, real-device status, reused project components, and each modified `Stack` relationship. Never claim user visual approval or real-device success unless the user supplied it.
