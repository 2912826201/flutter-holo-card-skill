import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class HolographicCardPainter extends CustomPainter {
  const HolographicCardPainter({
    required this.shader,
    required this.cardMaskImage,
    required this.backgroundImage,
    required this.foregroundImage,
    required this.characterImage,
    required this.characterContourImage,
    required this.characterBloomImage,
    required this.view,
    required this.depth,
    required this.effectStrength,
    required this.contourGlowStrength,
    required this.effectActivation,
    required this.hasCharacterLayer,
  });

  final ui.FragmentShader shader;
  final ui.Image cardMaskImage;
  final ui.Image backgroundImage;
  final ui.Image foregroundImage;
  final ui.Image characterImage;
  final ui.Image characterContourImage;
  final ui.Image characterBloomImage;
  final Offset view;
  final double depth;
  final double effectStrength;
  final double contourGlowStrength;
  final double effectActivation;
  final bool hasCharacterLayer;

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
      ..setFloat(7, effectActivation)
      ..setFloat(8, hasCharacterLayer ? 1 : 0)
      ..setImageSampler(0, backgroundImage)
      ..setImageSampler(1, foregroundImage)
      ..setImageSampler(2, characterImage)
      ..setImageSampler(3, characterContourImage)
      ..setImageSampler(4, characterBloomImage)
      ..setImageSampler(5, cardMaskImage);

    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);
  }

  @override
  bool shouldRepaint(HolographicCardPainter oldDelegate) {
    return oldDelegate.shader != shader ||
        oldDelegate.cardMaskImage != cardMaskImage ||
        oldDelegate.backgroundImage != backgroundImage ||
        oldDelegate.foregroundImage != foregroundImage ||
        oldDelegate.characterImage != characterImage ||
        oldDelegate.characterContourImage != characterContourImage ||
        oldDelegate.characterBloomImage != characterBloomImage ||
        oldDelegate.view != view ||
        oldDelegate.depth != depth ||
        oldDelegate.effectStrength != effectStrength ||
        oldDelegate.contourGlowStrength != contourGlowStrength ||
        oldDelegate.effectActivation != effectActivation ||
        oldDelegate.hasCharacterLayer != hasCharacterLayer;
  }
}
