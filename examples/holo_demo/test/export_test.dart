import 'dart:convert';
import 'dart:io';
import 'package:archive/archive.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:holo_card_playground/card_settings.dart';
import 'package:holo_card_playground/demo_defaults.dart';
import 'package:holo_card_playground/export_bundle.dart';

class ExportedAssets extends CachingAssetBundle {
  ExportedAssets(this.files);
  final Map<String, List<int>> files;
  @override
  Future<ByteData> load(String key) async {
    // Flutter addresses package assets through their package prefix.
    final bytes = Uint8List.fromList(files[key]!);
    return ByteData.sublistView(bytes);
  }
}

Map<String, List<int>> unzip(List<int> bytes) => {
  for (final file in ZipDecoder().decodeBytes(bytes, verify: true))
    if (file.isFile) file.name: (file.content as List<int>),
};
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final mode in availableModes) {
    test(
      '$mode exports only required images and exact selected defaults',
      () async {
        final settings = CardSettings(
          mode: mode,
          effect: .37,
          foil: .62,
          contour: .41,
          depth: 1.7,
          motion: 2.4,
          sensitivity: 1.3,
          tilt: .17,
          auto: false,
          physical: false,
          poseX: -.8,
          poseY: .4,
        );
        final zip = await exportBundle(settings, fullDemo: false);
        final files = unzip(zip);
        expect(files.keys.where((k) => k.endsWith('.png')).toSet(), {
          for (final name in runtimeImages[mode]!) 'assets/card/$name',
          'assets/holographic_foil.png',
        });
        expect(files.keys.where((k) => k.endsWith('.frag')).toList(), [
          'shaders/${shaderEntry[mode]}',
        ]);
        expect(files.containsKey('lib/main.dart'), false);
        final selection = jsonDecode(utf8.decode(files['selection.json']!));
        expect(selection['settings'], settings.toJson());
        final code = utf8.decode(files['lib/selected_holo_card.dart']!);
        expect(code, contains('this.effectStrength = 0.37'));
        expect(code, contains('this.autoPlay = false'));
        expect(code, contains('const Offset(-0.8, 0.4)'));
        for (final name in runtimeImages[mode]!) {
          final original = await rootBundle.load(
            'assets/holographic_card/$mode/$name',
          );
          expect(
            files['assets/card/$name'],
            original.buffer.asUint8List(
              original.offsetInBytes,
              original.lengthInBytes,
            ),
          );
        }
        final output = Platform.environment['HOLO_EXPORT_TEST_OUTPUT'];
        if (output != null) {
          Directory(output).createSync(recursive: true);
          File('$output/$mode-component.zip').writeAsBytesSync(zip);
        }
      },
    );
  }
  test('full demo preserves controls, sources and can export again', () async {
    final settings = CardSettings(
      mode: availableModes.last,
      effect: .29,
      foil: .58,
      auto: false,
    );
    final zip = await exportBundle(settings, fullDemo: true);
    final files = unzip(zip);
    expect(
      files.keys,
      containsAll([
        'lib/main.dart',
        'lib/export_bundle.dart',
        'web/index.html',
        'pubspec.yaml',
      ]),
    );
    expect(
      utf8.decode(files['lib/demo_defaults.dart']!),
      contains('"effect":0.29'),
    );
    for (final mode in availableModes) {
      expect(files.keys, contains('assets/holographic_card/$mode/source.png'));
    }
    final second = unzip(
      await exportBundle(
        settings,
        fullDemo: false,
        bundle: ExportedAssets(files),
      ),
    );
    expect(
      jsonDecode(utf8.decode(second['selection.json']!))['settings'],
      settings.toJson(),
    );
    final fullAgain = unzip(
      await exportBundle(
        settings,
        fullDemo: true,
        bundle: ExportedAssets(files),
      ),
    );
    expect(fullAgain.keys.toSet(), files.keys.toSet());
    final output = Platform.environment['HOLO_EXPORT_TEST_OUTPUT'];
    if (output != null) {
      Directory(output).createSync(recursive: true);
      File('$output/full-demo.zip').writeAsBytesSync(zip);
    }
  });
}
