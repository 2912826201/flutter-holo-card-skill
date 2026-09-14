#version 460 core
#include <flutter/runtime_effect.glsl>

uniform vec2 uSize;
uniform vec2 uView;
uniform float uDepth;
uniform float uContourBrightness;
uniform float uPower;
uniform float uEffectActivation;
uniform float uLayeredCharacter;
uniform sampler2D uBackground;
uniform sampler2D uForeground;
uniform sampler2D uCharacter;
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
  vec2 outputPoint = FlutterFragCoord().xy / uSize;
  vec2 point = uLayeredCharacter > 0.5
    ? (outputPoint - vec2(0.5)) * 1.6 + vec2(0.5)
    : outputPoint;
  float cardMask = texture(
    uCardMask,
    clamp(point, vec2(0.0), vec2(1.0))
  ).a * insideUnit(point);

  float depthCoefficient = uDepth < 0.0 ? 0.06 : 0.08;
  vec2 characterUv = point - uView * depthCoefficient * uDepth;
  vec2 foregroundUv = uLayeredCharacter > 0.5
    ? point - uView * 0.14 * max(uDepth, 0.0)
    : characterUv;
  vec2 backgroundUv = (
    (point - vec2(0.5)) * 0.5
    + vec2(0.5)
    - uView * 0.25
  );

  vec4 foreground = texture(
    uForeground,
    clamp(foregroundUv, vec2(0.0), vec2(1.0))
  );
  vec3 foregroundColor = unpremultiply(foreground);
  float foregroundClip = uLayeredCharacter > 0.5
    ? (uDepth > 0.0 ? 1.0 : cardMask)
    : 1.0;
  foreground.a *= insideUnit(foregroundUv) * foregroundClip;
  vec4 character = texture(
    uCharacter,
    clamp(characterUv, vec2(0.0), vec2(1.0))
  );
  vec3 characterColor = unpremultiply(character);
  character.a *= insideUnit(characterUv) * foregroundClip;
  vec4 background = texture(
    uBackground,
    clamp(backgroundUv, vec2(0.0), vec2(1.0))
  );
  vec3 backgroundColor = unpremultiply(background);
  background.a *= insideUnit(backgroundUv) * cardMask;

  float foregroundAlpha = foreground.a;
  float characterAlpha = uLayeredCharacter > 0.5
    ? character.a
    : 0.0;
  vec3 basePremultiplied = backgroundColor * background.a;
  float baseAlpha = background.a;
  vec3 base;
  if (uLayeredCharacter > 0.5) {
    basePremultiplied = (
      characterColor * characterAlpha
      + basePremultiplied * (1.0 - characterAlpha)
    );
    baseAlpha = characterAlpha + baseAlpha * (1.0 - characterAlpha);
    base = basePremultiplied / max(baseAlpha, 0.0001);
  } else {
    // 兼容模式的颜色按原前景 Alpha 混合，最终形状仍严格由卡形遮罩决定。
    // 这样既保留旧版静止画面，也不会在圆角处被前景 Alpha 顶成直角。
    base = mix(backgroundColor, foregroundColor, foregroundAlpha);
    baseAlpha = cardMask;
  }
  float finalAlpha = baseAlpha;
  float activePower = uPower * uEffectActivation;

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
    + spectrum * 0.07 * baseAlpha
  );
  base = mix(base, foil, light * 0.48 * activePower);

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
  ) * activePower * (
    1.0 - (uLayeredCharacter > 0.5 ? characterAlpha : foregroundAlpha)
  ) * cardMask;

  if (uLayeredCharacter > 0.5) {
    vec3 composed = (
      foregroundColor * foregroundAlpha
      + base * baseAlpha * (1.0 - foregroundAlpha)
    );
    finalAlpha = foregroundAlpha + baseAlpha * (1.0 - foregroundAlpha);
    base = composed / max(finalAlpha, 0.0001);
  }

  if (finalAlpha <= 0.001) {
    fragColor = vec4(0.0);
    return;
  }

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
  base += vec3(glare * 0.12 * activePower) * finalAlpha;

  float structure = texture(
    uStructure,
    clamp(characterUv, vec2(0.0), vec2(1.0))
  ).r * insideUnit(characterUv);
  vec2 structureBloom = texture(
    uStructureBloom,
    clamp(characterUv, vec2(0.0), vec2(1.0))
  ).rg * insideUnit(characterUv);
  float contourOwnerAlpha = uLayeredCharacter > 0.5
    ? characterAlpha
    : foregroundAlpha;
  float uiOcclusion = uLayeredCharacter > 0.5
    ? 1.0 - foregroundAlpha
    : 1.0;
  float line = structure * contourOwnerAlpha * uiOcclusion;
  float envelope = smoothstep(0.025, 0.42, light);
  vec3 emissionColor = spectrum * 0.85 + vec3(0.15);
  vec3 emission = (
    emissionColor
    * line
    * envelope
    * activePower
    * 40.0
    * uContourBrightness
  );
  vec3 bloom = (
    emissionColor
    * (structureBloom.r * 0.55 + structureBloom.g * 0.8)
    * line
    * envelope
    * activePower
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
