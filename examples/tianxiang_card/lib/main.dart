import 'package:build_flutter_holo_card_template/holographic_card.dart';
import 'package:flutter/material.dart';

void main() => runApp(const CardDemoApp());

class CardDemoApp extends StatelessWidget {
  const CardDemoApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: '天鹅 (EX) · 全息卡实测',
    theme: ThemeData(
      brightness: Brightness.dark,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xffa4e3c5),
        brightness: Brightness.dark,
      ),
      scaffoldBackgroundColor: const Color(0xff101716),
      useMaterial3: true,
    ),
    home: const CardDemo(),
  );
}

class CardDemo extends StatefulWidget {
  const CardDemo({super.key});
  @override
  State<CardDemo> createState() => _CardDemoState();
}

class _CardDemoState extends State<CardDemo> {
  double depth = 2;
  double backgroundMotion = 3;
  double effect = 0.65;
  double glow = 0.55;
  bool source = false;
  bool foil = true;

  String mode = 'height';
  bool physical = true;
  bool contour = false;
  Offset? pose;

  Widget card() {
    final base = 'qa/v2/$mode/candidate';
    Widget image;
    if (source || contour && mode != 'low') {
      image = Image.asset(
        source ? 'assets/card/source.png' : '$base/contour-overlay.png',
        fit: BoxFit.contain,
      );
    } else {
      final original = AssetImage('$base/source.png');
      final line = AssetImage('$base/foreground_contour.png');
      final bloom = AssetImage('$base/foreground_bloom.png');
      if (mode == 'low') {
        image = HolographicCard.low(
          cardImage: original,
          effectStrength: effect,
          foilStrength: foil ? 1 : 0,
          applyPhysicalTilt: physical,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
        );
      } else if (mode == 'medium') {
        image = HolographicCard.medium(
          cardImage: original,
          foregroundContourImage: line,
          foregroundBloomImage: bloom,
          effectStrength: effect,
          foilStrength: foil ? 1 : 0,
          contourGlowStrength: glow,
          applyPhysicalTilt: physical,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
        );
      } else {
        image = HolographicCard.height(
          cardImage: original,
          backgroundImage: AssetImage('$base/background.png'),
          foregroundImage: AssetImage('$base/foreground.png'),
          foregroundContourImage: line,
          foregroundBloomImage: bloom,
          backgroundSourceRect: const Rect.fromLTWH(
            80 / 1160,
            112 / 1621,
            1000 / 1160,
            1397 / 1621,
          ),
          depth: depth,
          backgroundMotionStrength: backgroundMotion,
          effectStrength: effect,
          foilStrength: foil ? 1 : 0,
          contourGlowStrength: glow,
          applyPhysicalTilt: physical,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
        );
      }
    }
    return Padding(padding: const EdgeInsets.all(36), child: image);
  }

  Widget control(
    String name,
    double value,
    double min,
    double max,
    int divisions,
    ValueChanged<double> changed,
  ) => Padding(
    padding: const EdgeInsets.only(top: 24),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(name)),
            Text(
              value.toStringAsFixed(2),
              style: const TextStyle(color: Color(0xffa4e3c5)),
            ),
          ],
        ),
        Slider(
          label: '$name ${value.toStringAsFixed(2)}',
          value: value,
          min: min,
          max: max,
          divisions: divisions,
          onChanged: (v) => setState(() => changed(v)),
        ),
      ],
    ),
  );

  Widget panel() => Container(
    constraints: const BoxConstraints(maxWidth: 360),
    padding: const EdgeInsets.all(28),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'HOLOGRAPHIC STUDY / 02',
          style: TextStyle(
            fontSize: 11,
            letterSpacing: 2.4,
            color: Color(0xffa4e3c5),
          ),
        ),
        const SizedBox(height: 20),
        const Text(
          '天鹅 (EX)',
          style: TextStyle(
            fontSize: 36,
            fontWeight: FontWeight.w600,
            letterSpacing: -1,
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          '移动鼠标，或按住卡面拖动。\n对比三档镭射、原图线条与背景景深。',
          style: TextStyle(height: 1.8, color: Color(0xffa5b4ae)),
        ),
        const SizedBox(height: 28),
        SegmentedButton<bool>(
          expandedInsets: EdgeInsets.zero,
          segments: const [
            ButtonSegment(value: false, label: Text('全息效果', maxLines: 1)),
            ButtonSegment(value: true, label: Text('原图对照', maxLines: 1)),
          ],
          selected: {source},
          onSelectionChanged: (v) => setState(() => source = v.first),
        ),
        const SizedBox(height: 12),
        SegmentedButton<String>(
          showSelectedIcon: false,
          expandedInsets: EdgeInsets.zero,
          segments: const [
            ButtonSegment(value: 'height', label: Text('height')),
            ButtonSegment(value: 'medium', label: Text('medium')),
            ButtonSegment(value: 'low', label: Text('low')),
          ],
          selected: {mode},
          onSelectionChanged: (v) => setState(() => mode = v.first),
        ),
        if (mode == 'height')
          control('背景后退距离', depth, 0, 3, 6, (v) => depth = v),
        if (mode == 'height') ...[
          control(
            '背景移动强度',
            backgroundMotion,
            0,
            4,
            40,
            (v) => backgroundMotion = v,
          ),
          const Text(
            '0 关闭移动 · 1 原始强度 · 达到背景边缘时自动限制',
            style: TextStyle(fontSize: 11, color: Color(0xff82948a)),
          ),
        ],
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('整卡倾斜'),
          value: physical,
          onChanged: (v) => setState(() => physical = v),
        ),
        if (mode != 'low')
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('轮廓叠加检查'),
            value: contour,
            onChanged: (v) => setState(() => contour = v),
          ),
        Wrap(
          spacing: 4,
          children: [
            for (final entry in {
              '自由': null,
              '中立': Offset.zero,
              '左': const Offset(-1, 0),
              '右': const Offset(1, 0),
              '上': const Offset(0, 1),
              '下': const Offset(0, -1),
              '↖': const Offset(-1, 1),
              '↗': const Offset(1, 1),
              '↙': const Offset(-1, -1),
              '↘': const Offset(1, -1),
            }.entries)
              TextButton(
                onPressed: () => setState(() => pose = entry.value),
                child: Text(entry.key),
              ),
          ],
        ),
        SwitchListTile(
          title: const Text('镭射材质'),
          subtitle: const Text('关闭后可单独检查轮廓光'),
          value: foil,
          onChanged: (v) => setState(() => foil = v),
        ),
        control('光效强度', effect, 0, 1, 20, (v) => effect = v),
        if (mode != 'low') control('轮廓亮度', glow, 0, 1, 20, (v) => glow = v),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => setState(() {
            depth = 2;
            backgroundMotion = 3;
            effect = 0.65;
            glow = 0.55;
            source = false;
            foil = true;
            mode = 'height';
            physical = true;
            contour = false;
            pose = null;
          }),
          icon: const Icon(Icons.refresh, size: 18),
          label: const Text('恢复默认'),
        ),
        const SizedBox(height: 26),
        const Text(
          '三档共用彩虹、箔纹与眩光。\nheight 背景后退；medium / low 固定原图。',
          style: TextStyle(fontSize: 12, height: 1.7, color: Color(0xff82948a)),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth >= 900 && constraints.maxHeight >= 720) {
            return Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1240),
                child: Row(
                  children: [
                    Expanded(child: card()),
                    Flexible(child: SingleChildScrollView(child: panel())),
                    const SizedBox(width: 24),
                  ],
                ),
              ),
            );
          }
          return SingleChildScrollView(
            child: Column(
              children: [
                SizedBox(
                  height: constraints.maxWidth.clamp(0, 650) * 1.397 + 50,
                  child: card(),
                ),
                panel(),
              ],
            ),
          );
        },
      ),
    ),
  );
}
