// SPDX-License-Identifier: GPL-3.0
// Contour material: moving reflection v2.
#include <flutter/runtime_effect.glsl>
uniform vec2 uSize;
uniform vec2 uPointer;
uniform float uPower;
uniform float uFoilAspect;
uniform float uContourPower;
uniform float uFoilStrength;
uniform sampler2D uCard;
uniform sampler2D uFoil;
uniform sampler2D uContour;
uniform sampler2D uBloom;
out vec4 fragColor;
#include "foil_material.glsl"
#include "contour_material.glsl"
void main() {
  vec2 uv = FlutterFragCoord().xy / uSize;
  vec4 source = texture(uCard, uv);
  vec3 card = source.rgb / max(source.a, 0.001);
  vec3 result = foilMaterial(uv, card, uPower * uFoilStrength);
  result = contourMaterial(uv, card, result);
  fragColor = vec4(result*source.a, source.a);
}
