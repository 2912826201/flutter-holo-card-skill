---
name: build-flutter-holo-card
description: Build and validate a two-layer Flutter holographic card from one raster card image. Use a repaired opaque background plus one source-faithful foreground containing every character, card UI element, frame, panel, and foreground effect, with white sketch contours across the complete foreground.
---

# Build Flutter Holo Card

Build one consistent two-layer effect:

1. `background.png`: complete opaque scenery with concealed regions repaired;
2. `foreground.png`: every character, foreground object/effect, title, number, symbol, panel, credit, and decorative frame, preserving the source stacking and source RGB.

The foreground moves as one plane above the background. Do not generate an independent character layer, split UI from characters, reconstruct hidden character anatomy, or introduce alternate effect modes.

Before running bundled Python scripts, install missing dependencies with `python -m pip install -r requirements.txt`. Use the bundled scripts rather than replacing them with ad-hoc extraction code.

## Select scope

- **asset-only:** prepare, align, review, validate, and clean the five runtime images; do not modify application code.
- **full (default):** complete the asset workflow, then integrate and test the Flutter component.

## Prepare resources

Read [references/resource-workflow.md](references/resource-workflow.md) before creating or repairing assets.

Keep every file on one full canvas and aspect ratio. Never independently crop, fit, recenter, stretch, or locally warp a layer.

The runtime contract is exactly five images:

- `source.png`: normalized supplied card with reviewed antialiased transparent card corners; its Alpha defines the static card shape;
- `background.png`: opaque, full-canvas scenery with the foreground and card interface removed and concealed areas repaired;
- `foreground.png`: source RGB for every non-background element, with transparent scenery;
- `foreground_contour.png`: opaque grayscale white sketch-line core for all visible foreground elements;
- `foreground_bloom.png`: opaque packed near/wide bloom for the same sketch lines.

Required workflow:

1. Inspect the supplied image at full resolution and classify scenery versus the combined foreground.
2. Normalize the source without cropping and establish its card-shape Alpha.
3. Generate and visually review only the repaired background color plate.
4. Create a reviewed full-canvas foreground Alpha mask, then build `foreground.png` from source pixels with `prepare_foreground.py`. Never repaint source-visible foreground RGB.
5. Generate white sketch line art on solid black from the accepted `foreground.png`. Include visible contours from every foreground element, including characters, typography, symbols, panels, foreground effects, and the decorative frame. Do not include scenery edges, filled white regions, shading, hatching, texture, or invented lines.
6. Normalize the registered line art, then build the contour and bloom maps.
7. Run `check_assets.py`. Fix deterministic errors and review every reported visual item.
8. After visual review passes, run `cleanup_assets.py`. Keep only the five runtime images.

Asset-only work stops after reporting the five paths, commands, deterministic results, and remaining visual caveats.

## Implement Flutter rendering

For full scope, read [references/rendering-contract.md](references/rendering-contract.md). Copy the templates under `assets/flutter/` into the nearest appropriate feature directory and adapt the existing project's image wrappers rather than adding a competing abstraction.

Preserve these behaviors:

- render and move only `background -> foreground`;
- sample foreground, contour, and bloom from the same UV at every signed depth;
- use a modest physical card tilt with a stronger, nonsaturating internal view response;
- let positive depth extend the combined foreground beyond the clipped background on a 160% transparent painter surface;
- keep the full card aspect ratio instead of stretching it to arbitrary parent constraints;
- retain a restrained idle foil effect, strengthen it during interaction, and allow `effectStrength == 0` to disable it completely;
- keep broad prismatic foil, fine diffraction, sparse glints, and glare readable rather than washing out the source art;
- render the sketch core as predominantly white light with a smaller spectral tint and a real two-scale halo;
- record touch-down as the zero-delta origin and animate release continuously.

Do not add normal, height, roughness, independent character, UI, or occlusion maps unless the user explicitly requests a different material model.

## Validate and hand off

Compare the flat `background + foreground` composite with `source.png` before enabling foil or glow. At signed depth `-2`, `0`, and `+2`, reject duplicated foreground content, background residue, holes, dirty matte, moving scenery, contour drift, illegible text, or clipped positive-depth foreground. Regenerate a shifted line-art result; do not warp individual contours into place.

For full scope:

1. Test all five resource and Shader loads.
2. Test bounded, narrow, wide, and one-axis-unbounded layouts without distortion or overflow exceptions.
3. Test touch-down, drag on both axes, continuous release, idle foil, full activation, and `effectStrength == 0`.
4. Run targeted formatting, analysis, Widget tests, and a debug build appropriate to the host application.

Report exact paths, commands run, unrun checks, and real-device status. Never claim user visual approval or real-device success unless the user supplied it.
