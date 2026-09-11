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

float band(vec2 point, vec2 view) {
  // Flutter screen Y grows downward. These positive coefficients orient the
  // constant-value bands from lower-left to upper-right.
  float field = (
    point.x * 0.65
    + point.y * 0.4
    + view.x * 1.9
    + view.y * 0.85
  );
  return pow(
    max(0.0, 1.0 - abs(fract(field + 0.16) - 0.5) * 2.0),
    3.0
  );
}

void main() {
  vec2 point = FlutterFragCoord().xy / uSize;
  float cardMask = texture(uCardMask, point).a;
  if (cardMask <= 0.001) {
    fragColor = vec4(0.0);
    return;
  }

  float depthCoefficient = uDepth < 0.0 ? 0.06 : 0.08;
  vec2 foregroundUv = point - uView * depthCoefficient * uDepth;
  vec2 backgroundUv = (
    (point - vec2(0.5)) * 0.5
    + vec2(0.5)
    - uView * 0.25
  );

  vec4 foreground = texture(
    uForeground,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  );
  foreground.a *= insideUnit(foregroundUv);
  vec4 background = texture(
    uBackground,
    clamp(backgroundUv, vec2(0.0), vec2(1.0))
  );
  background.a *= insideUnit(backgroundUv);

  float foregroundAlpha = foreground.a;
  float finalAlpha = cardMask;
  vec3 foregroundColor = unpremultiply(foreground);
  vec3 backgroundColor = unpremultiply(background);
  vec3 base = mix(backgroundColor, foregroundColor, foregroundAlpha);

  float phase = (
    point.x * 0.62
    + point.y * 0.36
    + uView.x * 1.9
    + uView.y * 0.8
  );
  vec3 spectrum = rainbow(phase * 2.2);
  float light = band(point, uView);
  float micro = pow(hash(floor(point * vec2(620.0, 868.0))), 28.0);

  vec3 foil = (
    base * (0.64 + spectrum * 0.7)
    + spectrum * 0.07 * finalAlpha
  );
  base = mix(base, foil, light * 0.48 * uPower);

  vec2 cell = fract(point * vec2(24.0, 34.0)) - vec2(0.5);
  float seed = hash(floor(point * vec2(24.0, 34.0)));
  float star = (
    pow(max(0.0, 1.0 - abs(cell.x) * 18.0), 14.0)
      * pow(max(0.0, 1.0 - abs(cell.y) * 2.0), 6.0)
    + pow(max(0.0, 1.0 - abs(cell.y) * 18.0), 14.0)
      * pow(max(0.0, 1.0 - abs(cell.x) * 2.0), 6.0)
  );
  base += spectrum * (
    star * step(0.965, seed) * light * 0.65
    + micro * light * 0.12
  ) * uPower * (1.0 - foregroundAlpha) * cardMask;

  float glare = pow(
    max(
      0.0,
      1.0 - length(
        (point - vec2(0.5 + uView.x, 0.6 + uView.y))
          * vec2(1.0, 0.75)
      )
    ),
    5.0
  );
  base += vec3(glare * 0.12 * uPower) * finalAlpha;

  float structure = texture(
    uStructure,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  ).r * insideUnit(foregroundUv);
  vec2 structureBloom = texture(
    uStructureBloom,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  ).rg * insideUnit(foregroundUv);
  float line = structure * foregroundAlpha;
  float envelope = smoothstep(0.025, 0.42, light);
  vec3 emissionColor = spectrum * 0.85 + vec3(0.15);
  vec3 emission = (
    emissionColor
    * line
    * envelope
    * uPower
    * 40.0
    * uContourBrightness
  );
  vec3 bloom = (
    emissionColor
    * (structureBloom.r * 0.55 + structureBloom.g * 0.8)
    * line
    * envelope
    * uPower
    * 40.0
    * uContourBrightness
  );

  vec3 linear = pow(clamp(base, 0.0, 1.0), vec3(2.2));
  vec3 combined = 1.0 - (
    (1.0 - linear)
    * exp(-(emission * 0.38 + bloom * 0.85))
  );
  vec3 displayColor = pow(
    clamp(combined, 0.0, 1.0),
    vec3(1.0 / 2.2)
  );
  fragColor = vec4(displayColor * finalAlpha, finalAlpha);
}
