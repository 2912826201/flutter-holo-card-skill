// SPDX-License-Identifier: GPL-3.0
#include <flutter/runtime_effect.glsl>
uniform vec2 uSize;
uniform vec2 uPointer;
uniform float uPower;
uniform float uFoilAspect;
uniform sampler2D uCard;
uniform sampler2D uFoil;
out vec4 fragColor;
#include "foil_material.glsl"
void main() {
  vec2 uv = FlutterFragCoord().xy / uSize;
  vec4 source = texture(uCard, uv);
  vec3 card = source.rgb / max(source.a, 0.001);
  vec3 result = foilMaterial(uv, card, uPower);
  fragColor = vec4(result*source.a, source.a);
}
