// SPDX-License-Identifier: GPL-3.0
// Source-aligned reflection, shared by height and medium. Never offset the maps.
vec3 contourMaterial(vec2 uv, vec3 card, vec3 foil) {
  float line = texture(uContour, uv).r;
  vec2 bloom = texture(uBloom, uv).rg;
  // The same light coordinates as foilMaterial. Turning the card sweeps a
  // specular band across the printed edges; the edges themselves stay fixed.
  vec2 light = uPointer - 0.5;
  float position = dot(uv - 0.5, vec2(0.731354, 0.681998));
  float center = dot(light, vec2(0.95, -0.85));
  float distanceToBand = position - center;
  float coreReflection = exp(-pow(distanceToBand / 0.14, 2.0));
  float haloReflection = exp(-pow(distanceToBand / 0.25, 2.0));
  float strength = uContourPower * sqrt(clamp(uPower, 0.0, 1.0));
  float reflectedLine = line * coreReflection;
  // Recover headroom only beneath the moving glint. Do not darken the card
  // globally or leave a permanently illuminated outline.
  vec3 base = mix(foil, card, clamp(reflectedLine * strength * 0.65, 0.0, 1.0));
  float emission = min((reflectedLine * 1.35
      + bloom.r * coreReflection * 0.65
      + bloom.g * haloReflection * 0.30) * strength, 0.60);
  return clamp(base + vec3(emission), 0.0, 1.0);
}
