// SPDX-License-Identifier: GPL-3.0
// Contour material: moving reflection v2.
#include <flutter/runtime_effect.glsl>
uniform vec2 uSize;
uniform vec2 uPointer;
uniform float uPower;
uniform float uFoilAspect;
uniform float uContourPower;
uniform float uFoilStrength;
uniform vec3 uCamera;
uniform float uDistance;
uniform vec4 uSourceRect;
uniform sampler2D uCard;
uniform sampler2D uFoil;
uniform sampler2D uContour;
uniform sampler2D uBloom;
uniform sampler2D uBackground;
uniform sampler2D uForeground;
out vec4 fragColor;
#include "foil_material.glsl"
#include "contour_material.glsl"
void main() {
  vec2 uv = FlutterFragCoord().xy / uSize;
  vec4 source = texture(uCard, uv);
  vec3 card = source.rgb / max(source.a, 0.001);
  // Camera and distance are in card-width units. Neutral projection is identity.
  vec2 ratio = vec2(1.0, uSize.y/uSize.x);
  vec2 p = (uv-0.5)*ratio;
  vec2 q = (p + uDistance/uCamera.z*(p-uCamera.xy))/(1.0+uDistance/2.0);
  vec2 backgroundUv = uSourceRect.xy + (q/ratio+0.5)*uSourceRect.zw;
  vec4 foreground = texture(uForeground, uv);
  vec3 background = texture(uBackground, backgroundUv).rgb;
  float owner = clamp(foreground.a/max(source.a, 0.001), 0.0, 1.0);
  // Apply only the background delta to the original composite. This preserves
  // exact neutral colors and avoids double-filtered fringes at matte boundaries.
  vec3 neutralBackground = texture(uBackground, uSourceRect.xy+uv*uSourceRect.zw).rgb;
  card = clamp(card + (background-neutralBackground)*(1.0-owner), 0.0, 1.0);
  vec3 result = foilMaterial(uv, card, uPower * uFoilStrength);
  result = contourMaterial(uv, card, result);
  fragColor = vec4(result*source.a, source.a);
}
