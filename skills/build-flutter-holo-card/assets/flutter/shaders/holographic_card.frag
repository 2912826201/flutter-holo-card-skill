#version 460 core
#include <flutter/runtime_effect.glsl>

uniform vec2 uSize;
uniform vec2 uView;
uniform float uDepth;
uniform float uContourBrightness;
uniform float uPower;
uniform sampler2D uBackground;
uniform sampler2D uForeground;
uniform sampler2D uStructure;
uniform sampler2D uStructureBloom;
uniform sampler2D uCardMask;

out vec4 fragColor;

vec3 unpremultiply(vec4 sampleColor) {
  return sampleColor.a > 0.001
    ? sampleColor.rgb / sampleColor.a
    : vec3(0.0);
}

float insideUnit(vec2 point) {
  return step(0.0, point.x)
    * step(point.x, 1.0)
    * step(0.0, point.y)
    * step(point.y, 1.0);
}

vec3 rainbow(float value) {
  return 0.52 + 0.48 * cos(
    6.28318 * (value + vec3(0.0, 0.33, 0.67))
  );
}

float hash(vec2 point) {
  return fract(sin(dot(point, vec2(127.1, 311.7))) * 43758.5453);
}

float broadPrism(vec2 point, vec2 view) {
  float field = (
    point.x * 0.62
    + point.y * 0.42
    + view.x * 1.72
    + view.y * 0.94
  );
  float ridge = 1.0 - abs(fract(field + 0.08) - 0.5) * 2.0;
  return smoothstep(0.18, 0.92, ridge);
}

float diffraction(vec2 point, vec2 view) {
  float phase = (
    point.x * 1.7
    - point.y * 1.15
    + view.x * 2.35
    - view.y * 1.25
  );
  return 0.5 + 0.5 * cos(6.28318 * phase);
}

void main() {
  vec2 outputPoint = FlutterFragCoord().xy / uSize;
  vec2 point = (outputPoint - vec2(0.5)) * 1.6 + vec2(0.5);
  float pointInside = insideUnit(point);
  float cardMask = texture(
    uCardMask,
    clamp(point, vec2(0.0), vec2(1.0))
  ).a * pointInside;

  float depthCoefficient = uDepth < 0.0 ? 0.055 : 0.075;
  vec2 foregroundUv = point - uView * depthCoefficient * uDepth;
  // Keep the neutral composite registered to the source. A small opposite
  // shift creates depth without the old 2x center crop.
  vec2 backgroundUv = point + uView * 0.04;
  float foregroundInside = insideUnit(foregroundUv);

  vec4 foreground = texture(
    uForeground,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  );
  vec4 background = texture(
    uBackground,
    clamp(backgroundUv, vec2(0.0), vec2(1.0))
  );
  vec3 foregroundColor = unpremultiply(foreground);
  vec3 backgroundColor = unpremultiply(background);

  float foregroundClip = uDepth > 0.0 ? 1.0 : cardMask;
  foreground.a *= foregroundInside * foregroundClip;
  // The validated background is opaque and full-bleed. Clamp sampling at the
  // canvas edge so a tilted card never exposes an empty strip.
  background.a *= cardMask;

  float foregroundAlpha = foreground.a;
  float backgroundAlpha = background.a;
  vec3 basePremultiplied = (
    foregroundColor * foregroundAlpha
    + backgroundColor * backgroundAlpha * (1.0 - foregroundAlpha)
  );
  float finalAlpha = (
    foregroundAlpha + backgroundAlpha * (1.0 - foregroundAlpha)
  );
  if (finalAlpha <= 0.001) {
    fragColor = vec4(0.0);
    return;
  }
  vec3 base = basePremultiplied / max(finalAlpha, 0.0001);
  vec3 linearBase = pow(clamp(base, 0.0, 1.0), vec3(2.2));
  float power = clamp(uPower, 0.0, 1.0);
  float viewEnergy = clamp(length(uView) * 1.45, 0.0, 1.0);

  float broad = broadPrism(point, uView);
  float fine = diffraction(point, uView);
  float phase = (
    point.x * 0.58
    + point.y * 0.34
    + uView.x * 1.82
    + uView.y * 0.86
  );
  vec3 spectrum = rainbow(phase * 2.15);

  vec3 prismTint = linearBase * (0.93 + spectrum * 0.13);
  vec3 prismLight = 1.0 - (
    (1.0 - linearBase)
    * (1.0 - spectrum * 0.11)
  );
  float foilWeight = power
    * (0.08 + broad * 0.34 + fine * 0.10)
    * (0.58 + viewEnergy * 0.42);
  vec3 foilColor = mix(prismTint, prismLight, 0.52);
  linearBase = mix(
    linearBase,
    foilColor,
    clamp(foilWeight, 0.0, 0.55)
  );

  vec2 cell = fract(point * vec2(31.0, 43.0)) - vec2(0.5);
  float seed = hash(floor(point * vec2(31.0, 43.0)));
  float star = (
    pow(max(0.0, 1.0 - abs(cell.x) * 20.0), 16.0)
      * pow(max(0.0, 1.0 - abs(cell.y) * 2.2), 7.0)
    + pow(max(0.0, 1.0 - abs(cell.y) * 20.0), 16.0)
      * pow(max(0.0, 1.0 - abs(cell.x) * 2.2), 7.0)
  );
  float sparkle = (
    star
    * step(0.984, seed)
    * broad
    * (0.35 + viewEnergy * 0.65)
  );
  linearBase += (spectrum * 0.55 + vec3(0.45))
    * sparkle
    * 0.15
    * power
    * cardMask;

  float glare = pow(
    max(
      0.0,
      1.0 - length(
        (point - vec2(0.5 + uView.x * 0.72, 0.58 + uView.y * 0.72))
          * vec2(1.0, 0.74)
      )
    ),
    6.0
  );
  linearBase += vec3(glare * 0.065 * power) * finalAlpha;

  float structure = texture(
    uStructure,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  ).r * foregroundInside;
  vec2 packedBloom = texture(
    uStructureBloom,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  ).rg * foregroundInside;
  float core = structure * foregroundAlpha;
  float contourEnvelope = 0.38 + broad * 0.62;
  vec3 highlightColor = mix(vec3(1.0), spectrum, 0.18);
  vec3 emission = (
    highlightColor
    * core
    * contourEnvelope
    * power
    * uContourBrightness
    * 4.0
  );
  vec3 halo = (
    highlightColor
    * (packedBloom.r * 0.62 + packedBloom.g * 0.30)
    * (0.45 + broad * 0.55)
    * power
    * uContourBrightness
    * 1.8
  );

  vec3 combined = 1.0 - (
    (1.0 - clamp(linearBase, 0.0, 1.0))
    * exp(-(emission * 0.68 + halo * 0.82))
  );
  vec3 displayColor = pow(
    clamp(combined, 0.0, 1.0),
    vec3(1.0 / 2.2)
  );
  fragColor = vec4(displayColor * finalAlpha, finalAlpha);
}
