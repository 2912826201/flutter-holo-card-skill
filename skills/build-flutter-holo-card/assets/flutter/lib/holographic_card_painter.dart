import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';

/// Inverse of rotateX(pitch) * rotateY(yaw), with camera at (0, 0, 2).
List<double> backgroundCamera(Offset view, double radians) {
  final pitch = view.dy * radians, yaw = view.dx * radians;
  return [
    -2 * math.sin(yaw) * math.cos(pitch),
    2 * math.sin(pitch),
    2 * math.cos(yaw) * math.cos(pitch),
  ];
}

Offset projectBackgroundUv(
  Offset uv,
  double aspect,
  Offset pose,
  double radians,
  double depth,
) {
  final c = backgroundCamera(pose, radians);
  final d = 0.04 * math.min(1.0, 1 / aspect) * depth;
  final p = Offset(uv.dx - .5, (uv.dy - .5) / aspect);
  return Offset(
    (p.dx + d / c[2] * (p.dx - c[0])) / (1 + d / 2) + .5,
    (p.dy + d / c[2] * (p.dy - c[1])) / (1 + d / 2) * aspect + .5,
  );
}

// A single distance cap keeps the projection coherent; never clamp individual
// texture coordinates (which stretches/repeats the background at its edges).
double safeBackgroundDistance(
  double aspect,
  Offset pose,
  double radians,
  double depth,
  double strength,
  Rect sourceRect,
) {
  final camera = backgroundCamera(pose, radians);
  final requested = .04 * math.min(1.0, 1 / aspect) * depth * strength;
  bool fits(double d) {
    for (final x in [0.0, 1.0]) {
      for (final y in [0.0, 1.0]) {
        final px = x - .5, py = (y - .5) / aspect;
        final u = (px + d / camera[2] * (px - camera[0])) / (1 + d / 2) + .5;
        final v =
            (py + d / camera[2] * (py - camera[1])) / (1 + d / 2) * aspect + .5;
        final tx = sourceRect.left + u * sourceRect.width;
        final ty = sourceRect.top + v * sourceRect.height;
        if (tx < .002 || tx > .998 || ty < .002 || ty > .998) return false;
      }
    }
    return true;
  }

  if (fits(requested)) return requested;
  double lo = 0, hi = requested;
  for (var i = 0; i < 24; i++) {
    final mid = (lo + hi) / 2;
    if (fits(mid)) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return lo;
}

class HolographicCardPainter extends CustomPainter {
  const HolographicCardPainter({
    required this.shader,
    required this.images,
    required this.mode,
    required this.view,
    required this.depth,
    this.backgroundMotionStrength = 1,
    required this.effectStrength,
    this.foilStrength = 1,
    required this.contourGlowStrength,
    required this.maxTiltRadians,
    required this.viewSensitivity,
    required this.sourceRect,
  });
  final ui.FragmentShader shader;
  final List<ui.Image> images;
  final String mode;
  final Offset view;
  final double backgroundMotionStrength;
  final double depth,
      effectStrength,
      foilStrength,
      contourGlowStrength,
      maxTiltRadians,
      viewSensitivity;
  final Rect sourceRect;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final values = <double>[
      size.width,
      size.height,
      (0.5 + view.dx * 0.5 * viewSensitivity).clamp(0, 1),
      (0.5 - view.dy * 0.5 * viewSensitivity).clamp(0, 1),
      mode == 'low' ? effectStrength * foilStrength : effectStrength,
      images[1].width / images[1].height,
    ];
    if (mode != 'low') values.addAll([contourGlowStrength, foilStrength]);
    if (mode == 'height') {
      values.addAll(backgroundCamera(view, maxTiltRadians));
      values.add(
        safeBackgroundDistance(
          size.width / size.height,
          view,
          maxTiltRadians,
          depth,
          backgroundMotionStrength,
          sourceRect,
        ),
      );
      values.addAll([
        sourceRect.left,
        sourceRect.top,
        sourceRect.width,
        sourceRect.height,
      ]);
    }
    for (var i = 0; i < values.length; i++) {
      shader.setFloat(i, values[i]);
    }
    for (var i = 0; i < images.length; i++) {
      shader.setImageSampler(i, images[i], filterQuality: FilterQuality.medium);
    }
    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);
  }

  @override
  bool shouldRepaint(HolographicCardPainter old) =>
      old.shader != shader ||
      old.view != view ||
      old.depth != depth ||
      old.backgroundMotionStrength != backgroundMotionStrength ||
      old.effectStrength != effectStrength ||
      old.foilStrength != foilStrength ||
      old.contourGlowStrength != contourGlowStrength ||
      old.sourceRect != sourceRect ||
      old.maxTiltRadians != maxTiltRadians ||
      old.viewSensitivity != viewSensitivity;
}
