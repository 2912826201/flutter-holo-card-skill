import 'dart:convert';
import 'package:archive/archive.dart';
import 'package:flutter/services.dart';
import 'card_settings.dart';

const packageName = 'build_flutter_holo_card_template';
const runtimeImages = {
  'height': [
    'source.png',
    'background.png',
    'foreground.png',
    'foreground_contour.png',
    'foreground_bloom.png',
  ],
  'medium': ['source.png', 'foreground_contour.png', 'foreground_bloom.png'],
  'low': ['source.png'],
};
const shaderEntry = {
  'height': 'holographic_card.frag',
  'medium': 'medium.frag',
  'low': 'low.frag',
};

String defaultsSource(
  CardSettings settings,
  Map<String, dynamic> card,
  List<dynamic> modes,
) =>
    'const initialSettings = ${jsonEncode(settings.toJson())};\n'
    'const demoCard = ${jsonEncode(card).replaceAll(r'$', r'\$')};\n'
    'const availableModes = ${jsonEncode(modes)};\n';

// Called with an immutable snapshot captured before the first asynchronous read.
Future<Uint8List> exportBundle(
  CardSettings settings, {
  required bool fullDemo,
  AssetBundle? bundle,
}) async {
  final loader = bundle ?? rootBundle;
  final payload =
      jsonDecode(await loader.loadString('assets/export_payload.json'))
          as Map<String, dynamic>;
  final sources = Map<String, String>.from(payload['sources'] as Map);
  final modes = payload['modes'] as List<dynamic>;
  final card = Map<String, dynamic>.from(payload['card'] as Map);
  if (!modes.contains(settings.mode)) throw StateError('当前档位未打包');
  final files = <String, List<int>>{};
  void addText(String path, String content) =>
      files[path] = utf8.encode(content);
  Future<void> addAsset(String path, String key) async {
    final data = await loader.load(key);
    files[path] = data.buffer.asUint8List(
      data.offsetInBytes,
      data.lengthInBytes,
    );
  }

  if (fullDemo) {
    sources['lib/demo_defaults.dart'] = defaultsSource(settings, card, modes);
    sources.forEach(addText);
    for (final key in (payload['images'] as List).cast<String>()) {
      await addAsset(key, key);
    }
    // Rebuild the embedded source manifest as well: the exported demo can export again.
    addText(
      'assets/export_payload.json',
      jsonEncode({...payload, 'sources': sources}),
    );
  } else {
    final prefix = 'packages/$packageName/';
    final allowed = {
      'lib/holographic_card.dart',
      'lib/holographic_card_painter.dart',
      'shaders/${shaderEntry[settings.mode]}',
      'shaders/foil_material.glsl',
      if (settings.mode != 'low') 'shaders/contour_material.glsl',
    };
    for (final entry in sources.entries) {
      if (!entry.key.startsWith(prefix)) continue;
      final relative = entry.key.substring(prefix.length);
      if (allowed.contains(relative) || relative.startsWith('licenses/')) {
        addText(relative, entry.value);
      }
    }
    for (final path in allowed) {
      if (!files.containsKey(path)) throw StateError('缺少组件源文件：$path');
    }
    for (final name in runtimeImages[settings.mode]!) {
      await addAsset(
        'assets/card/$name',
        'assets/holographic_card/${settings.mode}/$name',
      );
    }
    await addAsset(
      'assets/holographic_foil.png',
      'packages/$packageName/assets/holographic_foil.png',
    );
    addText('lib/selected_holo_card.dart', componentSource(settings, card));
    addText('pubspec.yaml', '''name: $packageName
description: Holographic card with exported defaults.
version: 1.0.0
publish_to: none
environment:
  sdk: ^3.9.0
dependencies:
  flutter:
    sdk: flutter
flutter:
  assets:
    - assets/card/
    - assets/holographic_foil.png
  shaders:
    - shaders/${shaderEntry[settings.mode]}
''');
    addText('README.md', '''# 导出的全息卡组件

当前档位：${settings.mode}。导出时的参数已写入 SelectedHoloCard 的构造默认值。
将此目录放入应用的 packages/$packageName，并在应用的 pubspec.yaml 中添加：

```yaml
dependencies:
  $packageName:
    path: packages/$packageName
```

执行 `flutter pub get`，然后使用：

```dart
import 'package:$packageName/selected_holo_card.dart';
const SelectedHoloCard();
```

用 SizedBox 或父布局设置卡片尺寸。构造函数中的参数可以覆盖默认值。
图片资源位于 assets/card/；请保留包名、Shader、箔纹和许可证文件。
此包只包含当前档位所需的 Shader 和图片，不含调参界面。
''');
  }
  addText(
    'selection.json',
    const JsonEncoder.withIndent('  ').convert({
      'settings': settings.toJson(),
      'card': card,
      'kind': fullDemo ? 'demo' : 'component',
    }),
  );
  final archive = Archive();
  for (final file in files.entries) {
    archive.addFile(ArchiveFile(file.key, file.value.length, file.value));
  }
  return Uint8List.fromList(ZipEncoder().encode(archive)!);
}

String componentSource(CardSettings s, Map<String, dynamic> card) {
  final rect = (card['sourceRect'] as List).join(', ');
  final pose = s.poseX == null
      ? 'null'
      : 'const Offset(${s.poseX}, ${s.poseY})';
  return '''import 'package:flutter/material.dart';
import 'holographic_card.dart';

/// Exported ${s.mode} card; constructor defaults match the selected demo state.
class SelectedHoloCard extends StatelessWidget {
  const SelectedHoloCard({super.key,
    this.effectStrength = ${s.effect}, this.foilStrength = ${s.foil},
    ${s.mode != 'low' ? 'this.contourGlowStrength = ${s.contour},' : ''}
    ${s.mode == 'height' ? 'this.depth = ${s.depth}, this.backgroundMotionStrength = ${s.motion},' : ''}
    this.viewSensitivity = ${s.sensitivity}, this.maxTiltRadians = ${s.tilt},
    this.autoPlay = ${s.auto}, this.applyPhysicalTilt = ${s.physical},
    this.controlledTilt = $pose,
  });
  final double effectStrength, foilStrength, viewSensitivity, maxTiltRadians;
  ${s.mode != 'low' ? 'final double contourGlowStrength;' : ''}
  ${s.mode == 'height' ? 'final double depth, backgroundMotionStrength;' : ''}
  final bool autoPlay, applyPhysicalTilt;
  final Offset? controlledTilt;

  @override
  Widget build(BuildContext context) => HolographicCard.${s.mode}(
    cardImage: const AssetImage('packages/$packageName/assets/card/source.png'),
    ${s.mode != 'low' ? "foregroundContourImage: const AssetImage('packages/$packageName/assets/card/foreground_contour.png'),\n    foregroundBloomImage: const AssetImage('packages/$packageName/assets/card/foreground_bloom.png'),\n    contourGlowStrength: contourGlowStrength," : ''}
    ${s.mode == 'height' ? "backgroundImage: const AssetImage('packages/$packageName/assets/card/background.png'),\n    foregroundImage: const AssetImage('packages/$packageName/assets/card/foreground.png'),\n    backgroundSourceRect: const Rect.fromLTWH($rect),\n    depth: depth, backgroundMotionStrength: backgroundMotionStrength," : ''}
    effectStrength: effectStrength, foilStrength: foilStrength,
    viewSensitivity: viewSensitivity, maxTiltRadians: maxTiltRadians,
    autoPlay: autoPlay, applyPhysicalTilt: applyPhysicalTilt,
    controlledTilt: controlledTilt,
    controlledActivation: controlledTilt == null ? null : 1,
  );
}
''';
}
