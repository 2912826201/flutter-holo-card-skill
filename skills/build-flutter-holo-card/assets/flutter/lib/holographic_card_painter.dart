import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class HolographicCardPainter extends CustomPainter {
  const HolographicCardPainter({
    required this.shader,
    required this.cardMaskImage,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.foregroundContourImage,
    required this.foregroundBloomImage,
    required this.view,
    required this.depth,
    required this.effectStrength,
    required this.contourGlowStrength,
  });

  final ui.FragmentShader shader;
  final ui.Image cardMaskImage;
  final ui.Image backgroundImage;
  final ui.Image foregroundImage;
  final ui.Image foregroundContourImage;
  final ui.Image foregroundBloomImage;
  final Offset view;
  final double depth;
  final double effectStrength;
  final double contourGlowStrength;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) {
      return;
    }

    shader
      ..setFloat(0, size.width)
      ..setFloat(1, size.height)
      ..setFloat(2, view.dx)
      ..setFloat(3, view.dy)
      ..setFloat(4, depth)
      ..setFloat(5, contourGlowStrength)
      ..setFloat(6, effectStrength)
      ..setImageSampler(0, backgroundImage)
      ..setImageSampler(1, foregroundImage)
      ..setImageSampler(2, foregroundContourImage)
      ..setImageSampler(3, foregroundBloomImage)
      ..setImageSampler(4, cardMaskImage);

    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);
  }

  @override
  bool shouldRepaint(HolographicCardPainter oldDelegate) {
    return oldDelegate.shader != shader ||
        oldDelegate.cardMaskImage != cardMaskImage ||
        oldDelegate.backgroundImage != backgroundImage ||
        oldDelegate.foregroundImage != foregroundImage ||
        oldDelegate.foregroundContourImage != foregroundContourImage ||
        oldDelegate.foregroundBloomImage != foregroundBloomImage ||
        oldDelegate.view != view ||
        oldDelegate.depth != depth ||
        oldDelegate.effectStrength != effectStrength ||
        oldDelegate.contourGlowStrength != contourGlowStrength;
  }
}
