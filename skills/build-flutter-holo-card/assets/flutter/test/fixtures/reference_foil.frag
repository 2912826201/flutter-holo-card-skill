// SPDX-License-Identifier: GPL-3.0
// 根据 simeydotme/pokemon-cards-css 的 Full Art 材质改写，许可与来源见
// licenses/pokemon-cards-css.GPL-3.0.txt 和 pokemon-cards-css.NOTICE.md。
#include <flutter/runtime_effect.glsl>

uniform vec2 uSize;
uniform vec2 uPointer;
uniform float uPower;
uniform float uFoilAspect;
uniform sampler2D uCard;
uniform sampler2D uFoil;
out vec4 fragColor;

float luminance(vec3 c) { return dot(c, vec3(0.3, 0.59, 0.11)); }
vec3 exclusion(vec3 a, vec3 b) { return a + b - 2.0 * a * b; }
vec3 hardLight(vec3 base, vec3 layer) {
  return mix(2.0 * base * layer, 1.0 - 2.0 * (1.0-base) * (1.0-layer), step(vec3(0.5), layer));
}
vec3 dodge(vec3 base, vec3 layer) { return min(vec3(1.0), base / max(vec3(0.001), 1.0-layer)); }

// 光谱保留自身饱和度，以斜向亮带提供明暗；越界颜色按亮度收缩，避免直接截断色相。
vec3 withLuminance(vec3 color, float lightness) {
  vec3 c = color + lightness - luminance(color);
  float lo = min(c.r, min(c.g, c.b));
  float hi = max(c.r, max(c.g, c.b));
  if (lo < 0.0) c = lightness + (c-lightness) * lightness / max(0.001, lightness-lo);
  if (hi > 1.0) c = lightness + (c-lightness) * (1.0-lightness) / max(0.001, hi-lightness);
  return c;
}

// 红、黄、绿、青、蓝、紫六个 sunpillar 色标，首尾连续循环。
vec3 spectrum(float position) {
  float p = fract(position) * 6.0;
  vec3 a = vec3(1.0, 0.478, 0.46);
  vec3 b = vec3(1.0, 0.928, 0.38);
  vec3 c = vec3(0.659, 1.0, 0.38);
  vec3 d = vec3(0.52, 1.0, 0.968);
  vec3 e = vec3(0.48, 0.584, 1.0);
  vec3 f = vec3(0.847, 0.46, 1.0);
  if (p < 1.0) return mix(a, b, p);
  if (p < 2.0) return mix(b, c, p-1.0);
  if (p < 3.0) return mix(c, d, p-2.0);
  if (p < 4.0) return mix(d, e, p-3.0);
  if (p < 5.0) return mix(e, f, p-4.0);
  return mix(f, a, p-5.0);
}

// CSS 133° 的投影方向；渐变周期为背景对角投影长度的 12%。
// 反向层连续延展亮带，避免跨过背景边界时整条反射突然跳变。
vec3 bands(vec2 uv, vec2 background, float widthScale) {
  vec2 scale = vec2(widthScale, 1.0);
  vec2 p = (uv - (1.0-scale) * background) / scale;
  vec2 direction = vec2(0.731354, 0.681998);
  vec2 physical = scale * vec2(uSize.x/uSize.y, 1.0);
  float t = 0.5 + dot((p-0.5)*physical, direction) / dot(physical, abs(direction));
  float phase = mod(t, 0.12);
  vec3 dark = vec3(0.055, 0.082, 0.18);
  vec3 middle = vec3(0.56, 0.64, 0.64);
  vec3 bright = vec3(0.561, 0.759, 0.759);
  if (phase < 0.038) return mix(dark, middle, phase/0.038);
  if (phase < 0.045) return mix(middle, bright, (phase-0.038)/0.007);
  if (phase < 0.052) return mix(bright, middle, (phase-0.045)/0.007);
  if (phase < 0.10) return mix(middle, dark, (phase-0.052)/0.048);
  return dark;
}

// 两层各自调整亮度、对比和饱和度，合成后保留交错光谱，不再重复压缩。
vec3 filtered(vec3 c, float brightness, float contrast, float saturation) {
  c = (c * brightness - 0.5) * contrast + 0.5;
  c = mix(vec3(luminance(c)), c, saturation);
  return clamp(c, 0.0, 1.0);
}

void main() {
  vec2 uv = FlutterFragCoord().xy / uSize;
  vec4 source = texture(uCard, uv);
  vec3 card = source.rgb / max(source.a, 0.001);
  // 指针 0–100% 对应背景横向 37–63%、纵向 33–67%。
  vec2 background = vec2(0.37, 0.33) + uPointer * vec2(0.26, 0.34);
  float fromCenter = clamp(length((uPointer-0.5)*2.0), 0.0, 1.0);
  vec2 bandPosition = vec2(background.x + background.y*0.2, background.y);

  // 箔纹从卡面原点固定平铺；宽度为卡宽的 33%，保留纹理宽高比。
  vec2 tileSize = vec2(0.33, 0.33 * uSize.x / uSize.y / uFoilAspect);
  vec3 grain = texture(uFoil, fract(uv/tileSize)).rgb;
  float rainbowY = (uv.y + 6.0*background.y) / 7.0;
  vec3 rainbow = spectrum((-rainbowY-0.05)/0.30);
  vec3 shine = withLuminance(rainbow, luminance(bands(uv, bandPosition, 3.0)));
  shine = filtered(exclusion(shine, grain), 0.35 + fromCenter*0.3, 2.0, 1.5);

  // 第二层使用不同背景尺寸反向移动，exclusion 形成交错的彩色明暗条带。
  float reverseY = (uv.y + 3.0*background.y) / 4.0;
  vec3 reverse = withLuminance(spectrum((-reverseY-0.05)/0.30), luminance(bands(uv, -bandPosition, 1.95)));
  reverse = filtered(exclusion(reverse, grain), 0.8 + fromCenter*0.5, 1.6, 1.4);
  shine = exclusion(shine, reverse);

  // 箔层能量取 72%，保留白色印刷区域的层次，避免 color-dodge 过曝。
  vec3 result = mix(card, dodge(card, shine * 0.72), uPower);
  vec2 ratio = vec2(uSize.x/uSize.y, 1.0);
  float farCorner = length(max(uPointer, 1.0-uPointer)*ratio);
  float distanceToLight = length((uv-uPointer)*ratio) / max(farCorner, 0.001);
  vec3 glare = mix(vec3(0.75), vec3(0.333, 0.357, 0.368), clamp((distanceToLight-0.05)/0.55, 0.0, 1.0));
  glare = mix(glare, vec3(0.14, 0.06, 0.113), clamp((distanceToLight-0.6)/0.9, 0.0, 1.0));
  // 高光覆盖强度为箔光的 75%，与彩虹层共同形成明暗，不对整卡强行抬黑。
  result = mix(result, hardLight(result, filtered(glare, 1.0, 1.2, 1.0)), uPower*0.75);
  fragColor = vec4(clamp(result, 0.0, 1.0) * source.a, source.a);
}
