import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../lib/holographic_card.dart';
import '../lib/holographic_card_painter.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('loads five images with visible two-layer defaults', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(width: 250, height: 350, child: _card(image)),
          ),
        ),
      ),
    );
    final Finder renderer = await _waitForRenderer(tester);
    final HolographicCard widget = tester.widget(find.byType(HolographicCard));
    final HolographicCardPainter painter = _painter(tester, renderer);

    expect(widget.depth, 1);
    expect(widget.viewSensitivity, 3);
    expect(widget.maxTiltRadians, 0.24);
    expect(widget.idleEffectStrength, 0.22);
    expect(painter.effectStrength, closeTo(0.22, 0.001));
    expect(painter.cardMaskImage.width, 2);
    expect(tester.getSize(renderer), const Size(250, 250));

    final String shaderSource = File(
      'shaders/holographic_card.frag',
    ).readAsStringSync();
    expect(shaderSource, contains('uniform sampler2D uForeground;'));
    expect(shaderSource, contains('float broadPrism'));
    expect(shaderSource, contains('vec3 highlightColor'));
    expect(shaderSource, isNot(contains('uCharacter')));
    expect(shaderSource, isNot(contains('uLayeredCharacter')));
    expect(tester.takeException(), isNull);
  });

  testWidgets('uses a centered 160 percent painter surface', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(width: 200, height: 280, child: _card(image)),
        ),
      ),
    );
    final Finder renderer = await _waitForRenderer(tester);
    final Positioned surface = tester.widget<Positioned>(
      find.descendant(of: renderer, matching: find.byType(Positioned)),
    );

    expect(tester.getSize(renderer), const Size(200, 200));
    expect(surface.left, -60);
    expect(surface.top, -60);
    expect(surface.width, 320);
    expect(surface.height, 320);
  });

  testWidgets('drag preserves zero pitch until vertical movement and returns', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: SizedBox(width: 240, height: 240, child: _card(image)),
          ),
        ),
      ),
    );
    final Finder renderer = await _waitForRenderer(tester);
    final Rect rect = tester.getRect(renderer);
    final TestGesture gesture = await tester.startGesture(
      Offset(rect.center.dx, rect.top + rect.height * 0.8),
    );
    await gesture.moveBy(const Offset(30, 0));
    await tester.pump();
    expect(_painter(tester, renderer).view.dy, 0);

    await gesture.moveBy(const Offset(0, -45));
    await tester.pump(const Duration(milliseconds: 200));
    final HolographicCardPainter active = _painter(tester, renderer);
    expect(active.view.dy, greaterThan(0));
    expect(active.effectStrength, greaterThan(0.22));

    await gesture.up();
    await tester.pump();
    expect(_painter(tester, renderer).view, isNot(Offset.zero));
    await tester.pumpAndSettle();
    final HolographicCardPainter settled = _painter(tester, renderer);
    expect(settled.view, Offset.zero);
    expect(settled.effectStrength, closeTo(0.22, 0.001));
    expect(tester.takeException(), isNull);
  });

  testWidgets('effect strength zero remains zero during interaction', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 200,
            height: 200,
            child: _card(image, effectStrength: 0),
          ),
        ),
      ),
    );
    final Finder renderer = await _waitForRenderer(tester);
    final TestGesture gesture = await tester.startGesture(
      tester.getCenter(renderer),
    );
    await gesture.moveBy(const Offset(25, -25));
    await tester.pump(const Duration(milliseconds: 220));
    expect(_painter(tester, renderer).effectStrength, 0);
    await gesture.up();
    await tester.pumpAndSettle();
  });

  testWidgets('derives height under a width-only constraint', (
    WidgetTester tester,
  ) async {
    final MemoryImage image = MemoryImage(_whitePng());
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 180,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [_card(image)],
            ),
          ),
        ),
      ),
    );
    final Finder renderer = await _waitForRenderer(tester);
    expect(tester.getSize(renderer), const Size(180, 180));
    expect(tester.takeException(), isNull);
  });
}

HolographicCard _card(MemoryImage image, {double effectStrength = 1}) {
  return HolographicCard(
    cardImage: image,
    backgroundImage: image,
    foregroundImage: image,
    foregroundContourImage: image,
    foregroundBloomImage: image,
    effectStrength: effectStrength,
  );
}

Future<Finder> _waitForRenderer(WidgetTester tester) async {
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
  return renderer;
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
