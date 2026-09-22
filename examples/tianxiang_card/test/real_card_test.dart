import 'package:build_flutter_holo_card_template/holographic_card.dart';
import 'package:build_flutter_holo_card_template/holographic_card_painter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget scene({
  double depth = 1,
  double power = 1,
  double width = 320,
  double height = 450,
}) => MaterialApp(
  home: Scaffold(
    body: Center(
      child: SizedBox(
        width: width,
        height: height,
        child: HolographicCard.height(
          cardImage: const AssetImage('qa/v2/height/candidate/source.png'),
          backgroundImage: const AssetImage(
            'qa/v2/height/candidate/background.png',
          ),
          foregroundImage: const AssetImage(
            'qa/v2/height/candidate/foreground.png',
          ),
          foregroundContourImage: const AssetImage(
            'qa/v2/height/candidate/foreground_contour.png',
          ),
          foregroundBloomImage: const AssetImage(
            'qa/v2/height/candidate/foreground_bloom.png',
          ),
          shaderAssetPath:
              'packages/build_flutter_holo_card_template/shaders/holographic_card.frag',
          backgroundSourceRect: const Rect.fromLTWH(
            80 / 1160,
            112 / 1621,
            1000 / 1160,
            1397 / 1621,
          ),
          depth: depth,
          effectStrength: power,
        ),
      ),
    ),
  ),
);

void main() {
  testWidgets('real assets, background depth, aspect ratio and interaction', (
    tester,
  ) async {
    await tester.pumpWidget(scene());
    final renderer = find.byKey(const ValueKey('holographic-card-renderer'));
    for (
      var attempt = 0;
      attempt < 40 && renderer.evaluate().isEmpty;
      attempt++
    ) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 100)),
      );
      await tester.pump();
    }
    expect(renderer, findsOneWidget);
    HolographicCardPainter painter() =>
        tester
                .widget<CustomPaint>(
                  find.descendant(
                    of: renderer,
                    matching: find.byType(CustomPaint),
                  ),
                )
                .painter!
            as HolographicCardPainter;
    expect(painter().images[4].width, 1160);
    expect(painter().images[5].height, 1397);
    for (final dimensions in [
      const Size(200, 500),
      const Size(500, 200),
      const Size(320, 450),
    ]) {
      for (final depth in [0.0, 1.0, 3.0]) {
        await tester.pumpWidget(
          scene(
            depth: depth,
            width: dimensions.width,
            height: dimensions.height,
          ),
        );
        await tester.pumpAndSettle();
        final size = tester.getSize(renderer);
        expect(size.width / size.height, closeTo(1000 / 1397, 0.0001));
        expect(size.width, lessThanOrEqualTo(dimensions.width));
        expect(size.height, lessThanOrEqualTo(dimensions.height));
        expect(painter().depth, depth);
        expect(tester.takeException(), isNull);
      }
    }
    final gesture = await tester.startGesture(tester.getCenter(renderer));
    await gesture.moveBy(const Offset(35, 0));
    await tester.pump();
    expect(painter().view.dy, 0);
    await gesture.moveBy(const Offset(20, -40));
    await tester.pump(const Duration(milliseconds: 200));
    expect(painter().view.dy, greaterThan(0));
    expect(painter().effectStrength, closeTo(1, 0.001));
    await gesture.up();
    await tester.pump();
    expect(painter().view, isNot(Offset.zero));
    await tester.pumpAndSettle();
    expect(painter().view, Offset.zero);
    expect(painter().effectStrength, closeTo(0.22, 0.001));
    await tester.pumpWidget(scene(power: 0));
    await tester.pumpAndSettle();
    final disabled = await tester.startGesture(tester.getCenter(renderer));
    await disabled.moveBy(const Offset(40, -30));
    await tester.pump(const Duration(milliseconds: 200));
    expect(painter().effectStrength, 0);
    await disabled.up();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
