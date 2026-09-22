import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:build_flutter_holo_card_template/holographic_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

// Opt-in artifact recorder: real touch events drive the production widget.
void main() {
  for (final mode in ['height', 'medium', 'low']) {
    testWidgets(
      'record $mode drag and release',
      (tester) async {
        final base = 'work/$mode/candidate';
        final source = AssetImage('$base/source.png');
        final line = AssetImage('$base/foreground_contour.png');
        final bloom = AssetImage('$base/foreground_bloom.png');
        final Widget card = switch (mode) {
          'height' => HolographicCard.height(
            cardImage: source,
            foregroundContourImage: line,
            foregroundBloomImage: bloom,
            backgroundImage: AssetImage('$base/background.png'),
            foregroundImage: AssetImage('$base/foreground.png'),
            backgroundSourceRect: const Rect.fromLTWH(
              36 / 522,
              51 / 731,
              450 / 522,
              629 / 731,
            ),
            depth: 2,
            backgroundMotionStrength: 3,
          ),
          'medium' => HolographicCard.medium(
            cardImage: source,
            foregroundContourImage: line,
            foregroundBloomImage: bloom,
          ),
          _ => HolographicCard.low(cardImage: source),
        };
        await tester.pumpWidget(
          MaterialApp(
            home: Center(
              child: RepaintBoundary(
                key: const ValueKey('record'),
                child: SizedBox(
                  width: 360,
                  height: 480,
                  child: ColoredBox(
                    color: const Color(0xff101716),
                    child: Center(
                      child: SizedBox(width: 300, height: 419.33, child: card),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
        final renderer = find.byKey(
          const ValueKey('holographic-card-renderer'),
        );
        for (var i = 0; i < 60 && renderer.evaluate().isEmpty; i++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 40)),
          );
          await tester.pump();
        }
        expect(renderer, findsOneWidget);
        final output = Directory('build/readme-frames/$mode')
          ..createSync(recursive: true);
        var frame = 0;
        Future<void> capture() async {
          await tester.runAsync(() async {
            final boundary = tester.renderObject<RenderRepaintBoundary>(
              find.byKey(const ValueKey('record')),
            );
            final image = await boundary.toImage();
            final bytes = await image.toByteData(
              format: ui.ImageByteFormat.png,
            );
            File(
              '${output.path}/${(frame++).toString().padLeft(3, '0')}.png',
            ).writeAsBytesSync(bytes!.buffer.asUint8List());
            image.dispose();
          });
        }

        for (var i = 0; i < 6; i++) {
          await tester.pump(const Duration(milliseconds: 67));
          await capture();
        }
        final center = tester.getCenter(renderer);
        final drag = await tester.startGesture(center);
        for (var i = 0; i < 48; i++) {
          final t = i / 47;
          await drag.moveTo(
            center +
                Offset(
                  105 * math.sin(t * math.pi * 2) + 75 * t,
                  -95 * math.sin(t * math.pi * 4) - 60 * t,
                ),
          );
          await tester.pump(const Duration(milliseconds: 67));
          await capture();
        }
        // Finish away from neutral, then record the widget's actual eased return.
        await drag.moveTo(center + const Offset(75, -60));
        await tester.pump(const Duration(milliseconds: 67));
        await capture();
        await drag.up();
        for (var i = 0; i < 17; i++) {
          await tester.pump(const Duration(milliseconds: 67));
          await capture();
        }
        expect(tester.takeException(), isNull);
      },
      skip: !const bool.fromEnvironment('RECORD_GIFS'),
    );
  }
}
