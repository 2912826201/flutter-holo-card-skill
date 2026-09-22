import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/holographic_card.dart';
import '../lib/holographic_card_painter.dart';

MemoryImage asset(String name) =>
    MemoryImage(File('test/fixtures/$name.png').readAsBytesSync());
HolographicCard card(
  String mode, {
  double power = 1,
  Offset? pose,
  bool physical = true,
  double depth = 1,
  ImageProvider? source,
  void Function(Object, StackTrace)? onError,
}) {
  final image = source ?? asset('source');
  final foil = asset('foil');
  if (mode == 'low')
    return HolographicCard.low(
      cardImage: image,
      foilImage: foil,
      shaderAssetPath: 'shaders/low.frag',
      effectStrength: power,
      controlledTilt: pose,
      applyPhysicalTilt: physical,
      onError: onError,
    );
  if (mode == 'medium')
    return HolographicCard.medium(
      cardImage: image,
      foilImage: foil,
      foregroundContourImage: asset('contour'),
      foregroundBloomImage: asset('bloom'),
      shaderAssetPath: 'shaders/medium.frag',
      effectStrength: power,
      controlledTilt: pose,
      applyPhysicalTilt: physical,
      onError: onError,
    );
  return HolographicCard.height(
    cardImage: image,
    foilImage: foil,
    foregroundContourImage: asset('contour'),
    foregroundBloomImage: asset('bloom'),
    backgroundImage: asset('background'),
    foregroundImage: asset('foreground'),
    backgroundSourceRect: const Rect.fromLTWH(
      8 / 116,
      12 / 164,
      100 / 116,
      140 / 164,
    ),
    shaderAssetPath: 'shaders/holographic_card.frag',
    depth: depth,
    effectStrength: power,
    controlledTilt: pose,
    applyPhysicalTilt: physical,
    onError: onError,
  );
}

Future<void> mount(WidgetTester tester, Widget child) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: Center(child: SizedBox(width: 200, height: 280, child: child)),
    ),
  ),
);
Finder get renderer => find.byKey(const ValueKey('holographic-card-renderer'));
Future<void> ready(WidgetTester tester, {int count = 1}) async {
  for (var i = 0; i < 40; i++) {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 30)),
    );
    await tester.pump();
    if (renderer.evaluate().length == count) break;
  }
  expect(renderer, findsNWidgets(count));
}

HolographicCardPainter painter(WidgetTester tester) =>
    tester
            .widget<CustomPaint>(
              find.descendant(
                of: renderer.first,
                matching: find.byType(CustomPaint),
              ),
            )
            .painter!
        as HolographicCardPainter;
Future<List<int>> pixels(WidgetTester tester, Finder finder) async {
  final boundary = tester.renderObject<RenderRepaintBoundary>(finder);
  final image = await boundary.toImage();
  final data = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
  image.dispose();
  return data!.buffer.asUint8List().toList();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('background motion gain stays inside overscan at every extreme', () {
    const rect = Rect.fromLTWH(36 / 522, 51 / 731, 450 / 522, 629 / 731);
    expect(
      safeBackgroundDistance(.715, const Offset(1, 1), .35, 3, 0, rect),
      0,
    );
    final normal = safeBackgroundDistance(
      .715,
      const Offset(1, 0),
      .24,
      1,
      1,
      rect,
    );
    expect(
      safeBackgroundDistance(.715, const Offset(1, 0), .24, 1, 2, rect),
      closeTo(normal * 2, 1e-9),
    );
    for (final aspect in [.2, .715, 1.0, 2.0, 5.0]) {
      for (final x in [-1.0, 0.0, 1.0]) {
        for (final y in [-1.0, 0.0, 1.0]) {
          final pose = Offset(x, y), c = backgroundCamera(Offset(x, y), .35);
          for (final strength in [0.0, 1.0, 2.0, 4.0]) {
            final d = safeBackgroundDistance(
              aspect,
              pose,
              .35,
              3,
              strength,
              rect,
            );
            for (final u in [0.0, 1.0]) {
              for (final v in [0.0, 1.0]) {
                final px = u - .5, py = (v - .5) / aspect;
                final qx = (px + d / c[2] * (px - c[0])) / (1 + d / 2) + .5;
                final qy =
                    (py + d / c[2] * (py - c[1])) / (1 + d / 2) * aspect + .5;
                expect(
                  rect.left + qx * rect.width,
                  inInclusiveRange(.001999, .998001),
                );
                expect(
                  rect.top + qy * rect.height,
                  inInclusiveRange(.001999, .998001),
                );
              }
            }
          }
        }
      }
    }
  });

  test('background projection neutral, depth zero and overscan safety', () {
    for (final aspect in [0.2, 0.715, 1.0, 2.0, 5.0]) {
      for (final uv in [
        Offset.zero,
        const Offset(1, 0),
        const Offset(0, 1),
        const Offset(1, 1),
      ]) {
        expect(
          (projectBackgroundUv(uv, aspect, Offset.zero, .35, 3) - uv).distance,
          lessThan(1e-10),
        );
        for (final x in [-1.0, 0.0, 1.0]) {
          for (final y in [-1.0, 0.0, 1.0]) {
            for (final depth in [0.0, 1.0, 3.0]) {
              final result = projectBackgroundUv(
                uv,
                aspect,
                Offset(x, y),
                .35,
                depth,
              );
              expect(result.dx, inInclusiveRange(-.08, 1.08));
              expect(result.dy, inInclusiveRange(-.08, 1.08));
              if (depth == 0) expect((result - uv).distance, lessThan(1e-10));
            }
          }
        }
      }
    }
    expect(
      projectBackgroundUv(
        const Offset(.5, .5),
        .715,
        const Offset(1, 0),
        .24,
        1,
      ).dx,
      greaterThan(.5),
    );
  });
  for (final mode in ['height', 'medium', 'low']) {
    testWidgets('$mode loads only required images on the exact card canvas', (
      tester,
    ) async {
      await mount(tester, card(mode));
      await ready(tester);
      expect(
        painter(tester).images.length,
        mode == 'height'
            ? 6
            : mode == 'medium'
            ? 4
            : 2,
      );
      expect(tester.getSize(renderer), const Size(200, 280));
      expect(
        find.descendant(of: renderer, matching: find.byType(Positioned)),
        findsNothing,
      );
      expect(tester.takeException(), isNull);
      await mount(tester, const SizedBox());
    });
  }
  for (final mode in ['height', 'medium', 'low']) {
    testWidgets(
      '$mode power zero matches original and stays fixed at any pose',
      (tester) async {
        await mount(
          tester,
          card(mode, power: 0, pose: const Offset(1, -1), physical: false),
        );
        await ready(tester);
        final rendered = (await tester.runAsync(
          () => pixels(tester, renderer),
        ))!;
        await mount(
          tester,
          RepaintBoundary(
            key: const ValueKey('original'),
            child: Image(
              image: asset('source'),
              fit: BoxFit.fill,
              filterQuality: FilterQuality.medium,
            ),
          ),
        );
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 100)),
        );
        await tester.pump();
        final original = (await tester.runAsync(
          () => pixels(tester, find.byKey(const ValueKey('original'))),
        ))!;
        expect(rendered.length, original.length);
        var maxError = 0;
        for (var i = 0; i < rendered.length; i++) {
          final error = (rendered[i] - original[i]).abs();
          if (error > maxError) maxError = error;
        }
        expect(maxError, lessThanOrEqualTo(1));
      },
    );
  }
  testWidgets(
    'low matches unmodified reference shader at equal pose and power',
    (tester) async {
      for (final pose in [
        Offset.zero,
        const Offset(-1, 1),
        const Offset(1, -1),
      ]) {
        await mount(tester, card('low', pose: pose, physical: false));
        await ready(tester);
        final actual = (await tester.runAsync(() => pixels(tester, renderer)))!;
        await mount(
          tester,
          HolographicCard.low(
            cardImage: asset('source'),
            foilImage: asset('foil'),
            shaderAssetPath: 'test/fixtures/reference_foil.frag',
            effectStrength: 1,
            controlledTilt: pose,
            applyPhysicalTilt: false,
          ),
        );
        await ready(tester);
        final reference = (await tester.runAsync(
          () => pixels(tester, renderer),
        ))!;
        expect(actual, reference);
      }
    },
  );
  testWidgets(
    'height foreground and Alpha stay anchored through all depth/pose extremes',
    (tester) async {
      await mount(tester, card('height', power: 0, physical: false, depth: 0));
      await ready(tester);
      final neutral = (await tester.runAsync(() => pixels(tester, renderer)))!;
      for (final depth in [0.0, 1.0, 3.0]) {
        for (final x in [-1.0, 0.0, 1.0]) {
          for (final y in [-1.0, 0.0, 1.0]) {
            await mount(
              tester,
              card(
                'height',
                power: 0,
                physical: false,
                depth: depth,
                pose: Offset(x, y),
              ),
            );
            await ready(tester);
            final actual = (await tester.runAsync(
              () => pixels(tester, renderer),
            ))!;
            // Uniform background fixture isolates foreground/card-boundary displacement.
            for (var i = 0; i < actual.length; i++) {
              expect(
                (actual[i] - neutral[i]).abs(),
                lessThanOrEqualTo(i % 4 == 3 ? 0 : 1),
              );
            }
          }
        }
      }
    },
  );
  testWidgets('horizontal and vertical drag return continuously', (
    tester,
  ) async {
    await mount(tester, card('low'));
    await ready(tester);
    final gesture = await tester.startGesture(tester.getCenter(renderer));
    await gesture.moveBy(const Offset(35, 0));
    await tester.pump();
    expect(painter(tester).view.dy, 0);
    await gesture.moveBy(const Offset(0, -40));
    await tester.pump();
    expect(painter(tester).view.dy, greaterThan(0));
    await gesture.up();
    await tester.pump();
    expect(painter(tester).view, isNot(Offset.zero));
    await tester.pumpAndSettle();
    expect(painter(tester).view, Offset.zero);
    await mount(
      tester,
      HolographicCard.low(
        cardImage: asset('source'),
        foilImage: asset('foil'),
        shaderAssetPath: 'shaders/low.frag',
        autoPlay: true,
      ),
    );
    await ready(tester);
    await tester.pump(const Duration(milliseconds: 400));
    final automaticPose = painter(tester).view;
    final touch = await tester.startGesture(tester.getCenter(renderer));
    await tester.pump();
    expect((painter(tester).view - automaticPose).distance, lessThan(1e-6));
    await touch.up();
    await tester.pump(const Duration(milliseconds: 300));
    await mount(tester, const SizedBox());
  });
  testWidgets('failed texture reports error and displays original', (
    tester,
  ) async {
    Object? failure;
    await mount(
      tester,
      HolographicCard.low(
        cardImage: asset('source'),
        foilImage: const AssetImage('missing.png'),
        onError: (e, s) => failure = e,
      ),
    );
    for (var i = 0; i < 10; i++) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pump();
    }
    expect(failure, isNotNull);
    expect(renderer, findsNothing);
    expect(find.byType(Image), findsOneWidget);
  });
  testWidgets('quick replacement and disposal leave no stale resources', (
    tester,
  ) async {
    await mount(tester, card('height'));
    await mount(tester, card('medium'));
    await mount(tester, card('low'));
    await ready(tester);
    expect(painter(tester).mode, 'low');
    await mount(tester, const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
  testWidgets('multiple instances own separate shader/image handles', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Row(
          children: [
            SizedBox(width: 180, height: 252, child: card('low')),
            SizedBox(width: 180, height: 252, child: card('medium')),
          ],
        ),
      ),
    );
    await ready(tester, count: 2);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
  testWidgets('single-axis unbounded constraints retain source aspect', (
    tester,
  ) async {
    for (final widthOnly in [true, false]) {
      final child = widthOnly
          ? SizedBox(
              width: 180,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [card('low')],
              ),
            )
          : SizedBox(
              height: 252,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [card('low')],
              ),
            );
      await tester.pumpWidget(MaterialApp(home: Center(child: child)));
      await ready(tester);
      final size = tester.getSize(renderer);
      expect(size.width / size.height, closeTo(100 / 140, 1e-6));
    }
  });
  testWidgets('reduced motion disables physical rotation and internal depth', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: SizedBox(
            width: 200,
            height: 280,
            child: card('height', pose: const Offset(1, 1)),
          ),
        ),
      ),
    );
    await ready(tester);
    expect(painter(tester).depth, 0);
    final transform = tester
        .widget<Transform>(
          find.byKey(const ValueKey('holographic-card-transform')),
        )
        .transform;
    expect(transform.entry(0, 0), 1);
    expect(transform.entry(1, 1), 1);
  });
}
