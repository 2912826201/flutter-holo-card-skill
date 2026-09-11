import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../lib/holographic_card.dart';
import '../lib/holographic_card_painter.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('loads the shader and changes pitch only after vertical drag', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 250,
              height: 350,
              child: HolographicCard(
                cardImage: image,
                backgroundImage: image,
                foregroundImage: image,
                characterContourImage: image,
                characterBloomImage: image,
              ),
            ),
          ),
        ),
      ),
    );

    final Finder renderer = find.byKey(
      const ValueKey('holographic-card-renderer'),
    );
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 300)),
    );
    for (
      int attempt = 0;
      attempt < 30 && renderer.evaluate().isEmpty;
      attempt++
    ) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(renderer, findsOneWidget);
    expect(_painter(tester, renderer).cardMaskImage.width, 2);
    expect(_painter(tester, renderer).cardMaskImage.height, 2);
    final String shaderSource = File(
      'shaders/holographic_card.frag',
    ).readAsStringSync();
    expect(
      shaderSource,
      contains('float cardMask = texture(uCardMask, point).a;'),
    );
    expect(shaderSource, contains('float finalAlpha = cardMask;'));

    final Rect card = tester.getRect(renderer);
    final TestGesture gesture = await tester.startGesture(
      Offset(card.center.dx, card.top + card.height * 0.82),
    );
    await gesture.moveBy(const Offset(24, 0));
    await tester.pump();
    expect(_painter(tester, renderer).view.dy, 0);

    await gesture.moveBy(const Offset(0, -48));
    await tester.pump();
    expect(_painter(tester, renderer).view.dy, greaterThan(0));

    await gesture.up();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}

HolographicCardPainter _painter(WidgetTester tester, Finder renderer) {
  final CustomPaint paint = tester.widget<CustomPaint>(
    find.descendant(of: renderer, matching: find.byType(CustomPaint)),
  );
  return paint.painter! as HolographicCardPainter;
}

Uint8List _whitePng() {
  return base64Decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFUlEQVR4nGP8////fwYGBgYmEAHCAD34BABm6tHAAAAAAElFTkSuQmCC',
  );
}
