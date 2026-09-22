import 'dart:io';
import 'dart:ui' as ui;
import 'package:build_flutter_holo_card_template/holographic_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

// Real source-extracted lines, not black placeholder maps.
void main() {
  for (final mode in ['height']) {
    testWidgets('$mode contour visible with and without foil', (tester) async {
      final output = Directory('qa/parallax-fix')..createSync(recursive: true);
      Future<List<int>> render(
        double glow,
        double foil,
        double activation, {
        double power = .65,
        Offset pose = const Offset(.7, -.5),
        double depth = 0,
      }) async {
        final base = 'work/$mode/candidate';
        final original = AssetImage('$base/source.png');
        final contour = AssetImage('$base/foreground_contour.png');
        final bloom = AssetImage('$base/foreground_bloom.png');
        final card = mode == 'low'
            ? HolographicCard.low(
                cardImage: original,
                foilStrength: foil,
                effectStrength: power,
                controlledActivation: activation,
                controlledTilt: pose,
                applyPhysicalTilt: false,
              )
            : mode == 'medium'
            ? HolographicCard.medium(
                cardImage: original,
                foregroundContourImage: contour,
                foregroundBloomImage: bloom,
                contourGlowStrength: glow,
                foilStrength: foil,
                effectStrength: power,
                controlledActivation: activation,
                controlledTilt: pose,
                applyPhysicalTilt: false,
              )
            : HolographicCard.height(
                cardImage: original,
                foregroundContourImage: contour,
                foregroundBloomImage: bloom,
                backgroundImage: AssetImage('$base/background.png'),
                foregroundImage: AssetImage('$base/foreground.png'),
                depth: depth,
                backgroundMotionStrength: 4,
                backgroundSourceRect: const Rect.fromLTWH(
                  36 / 522,
                  51 / 731,
                  450 / 522,
                  629 / 731,
                ),
                contourGlowStrength: glow,
                foilStrength: foil,
                effectStrength: power,
                controlledActivation: activation,
                controlledTilt: pose,
                applyPhysicalTilt: false,
              );
        await tester.pumpWidget(
          MaterialApp(
            home: Center(
              child: RepaintBoundary(
                key: const ValueKey('capture'),
                child: SizedBox(width: 320, height: 447.04, child: card),
              ),
            ),
          ),
        );
        final renderer = find.byKey(
          const ValueKey('holographic-card-renderer'),
        );
        for (var i = 0; i < 50; i++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 30)),
          );
          await tester.pump();
          if (renderer.evaluate().isNotEmpty) break;
        }
        expect(renderer, findsOneWidget);
        await tester.pumpAndSettle();
        return (await tester.runAsync(() async {
          final boundary = tester.renderObject<RenderRepaintBoundary>(
            find.byKey(const ValueKey('capture')),
          );
          final image = await boundary.toImage();
          final bytes = await image.toByteData(
            format: ui.ImageByteFormat.rawRgba,
          );
          final png = await image.toByteData(format: ui.ImageByteFormat.png);
          File(
            '${output.path}/$mode-depth$depth-x${pose.dx}-y${pose.dy}-foil$foil-glow$glow-active$activation-power$power.png',
          ).writeAsBytesSync(png!.buffer.asUint8List());
          image.dispose();
          return bytes!.buffer.asUint8List().toList();
        }))!;
      }

      if (mode == 'low') {
        await render(0, 1, 0);
        await render(0, 1, 1);
        expect(
          await render(0, 1, 1, power: 0),
          await render(0, 0, 1, power: 0),
        );
        return;
      }
      if (mode == 'height') {
        for (final depth in [0.0, 1.0, 3.0]) {
          for (final x in [-1.0, 0.0, 1.0]) {
            for (final y in [-1.0, 0.0, 1.0]) {
              await render(0, 0, 1, pose: Offset(x, y), depth: depth);
            }
          }
        }
      }
      final metrics = <String, Object>{};
      for (final activation in [0.0, 1.0]) {
        for (final foil in [0.0, 1.0]) {
          final off = await render(0, foil, activation);
          final on = await render(.35, foil, activation);
          int visible = 0, unchanged = 0, changedAlpha = 0;
          double total = 0;
          for (var i = 0; i < off.length; i += 4) {
            final delta =
                ((on[i] - off[i]).abs() +
                    (on[i + 1] - off[i + 1]).abs() +
                    (on[i + 2] - off[i + 2]).abs()) /
                3;
            if (delta >= 5) visible++;
            // Allow one quantization level when comparing independently rendered frames.
            if (delta <= 1) unchanged++;
            if (on[i + 3] != off[i + 3]) changedAlpha++;
            total += delta;
          }
          metrics['foil$foil-active$activation'] = {
            'visiblePixels': visible,
            'unchangedPixels': unchanged,
            'meanDelta': total / (off.length / 4),
          };
          expect(visible, greaterThan(1500));
          expect(unchanged, greaterThan(off.length / 4 * .35));
          expect(total / (off.length / 4), lessThan(12));
          expect(changedAlpha, 0);
        }
      }
      // With foil disabled and depth zero, only the contour reflection can move.
      final dark = await render(0, 0, 1);
      final centroids = <double>[];
      for (final pose in [const Offset(-.6, 0), const Offset(.6, 0)]) {
        final lit = await render(.35, 0, 1, pose: pose);
        double weighted = 0, energy = 0;
        for (var i = 0; i < lit.length; i += 4) {
          final amount =
              ((lit[i] - dark[i]) +
                      (lit[i + 1] - dark[i + 1]) +
                      (lit[i + 2] - dark[i + 2]))
                  .clamp(0, 765)
                  .toDouble();
          final pixel = i ~/ 4;
          final projection =
              (pixel % 320) / 320 * .731354 + (pixel ~/ 320) / 448 * .681998;
          weighted += projection * amount;
          energy += amount;
        }
        expect(energy, greaterThan(10000));
        centroids.add(weighted / energy);
      }
      expect(centroids[1] - centroids[0], greaterThan(.20));
      metrics['reflectionCentroids'] = centroids;
      expect(
        await render(.35, 1, 1, power: 0),
        await render(0, 0, 1, power: 0),
      );
      File('${output.path}/$mode-metrics.txt').writeAsStringSync('$metrics\n');
      expect(tester.takeException(), isNull);
    });
  }
}
