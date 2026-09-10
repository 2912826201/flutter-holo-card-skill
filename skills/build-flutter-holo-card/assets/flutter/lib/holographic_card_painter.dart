import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class HolographicCardPainter extends CustomPainter {
  const HolographicCardPainter({
    required this.shader,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.characterContourImage,
    required this.characterBloomImage,
    required this.view,
    required this.depth,
    required this.effectStrength,
    required this.contourGlowStrength,
  });

  final ui.FragmentShader shader;
  final ui.Image backgroundImage;
  final ui.Image foregroundImage;
  final ui.Image characterContourImage;
  final ui.Image characterBloomImage;
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
      ..setImageSampler(2, characterContourImage)
      ..setImageSampler(3, characterBloomImage);

    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);
  }

  @override
  bool shouldRepaint(HolographicCardPainter oldDelegate) {
    return oldDelegate.shader != shader ||
        oldDelegate.backgroundImage != backgroundImage ||
        oldDelegate.foregroundImage != foregroundImage ||
        oldDelegate.characterContourImage != characterContourImage ||
        oldDelegate.characterBloomImage != characterBloomImage ||
        oldDelegate.view != view ||
        oldDelegate.depth != depth ||
        oldDelegate.effectStrength != effectStrength ||
        oldDelegate.contourGlowStrength != contourGlowStrength;
  }
}
