import 'dart:math' as math;
import 'card_settings.dart';
import 'demo_defaults.dart';
import 'export_bundle.dart';
import 'download_stub.dart' if (dart.library.js_interop) 'download_web.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:build_flutter_holo_card_template/holographic_card.dart';

late final SemanticsHandle semanticsHandle;
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  semanticsHandle = WidgetsBinding.instance.ensureSemantics();
  runApp(const HoloLab());
}

const accent = Color(0xffd4b3ff);
const muted = Color(0xff9292a7);

class HoloLab extends StatelessWidget {
  const HoloLab({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Holo Lab · ${demoCard['title']}',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: const Color(0xff101016),
      colorScheme: ColorScheme.fromSeed(
        seedColor: accent,
        brightness: Brightness.dark,
      ),
      useMaterial3: true,
      fontFamily: 'sans-serif',
      sliderTheme: const SliderThemeData(
        trackHeight: 3,
        thumbShape: RoundSliderThumbShape(enabledThumbRadius: 6),
      ),
    ),
    home: const Playground(),
  );
}

class Playground extends StatefulWidget {
  const Playground({super.key});
  @override
  State<Playground> createState() => _PlaygroundState();
}

class _PlaygroundState extends State<Playground> {
  late HolographicCardMode mode;
  late double effect, foil, contour, depth, motion, sensitivity, tilt;
  late bool auto, physical;
  bool original = false, exporting = false;
  Offset? pose;
  String? error, exportStatus;
  final defaults = CardSettings.fromJson(initialSettings);
  double get aspect => (demoCard['width'] as num) / (demoCard['height'] as num);
  @override
  void initState() {
    super.initState();
    restoreSettings();
  }

  void restoreSettings() {
    mode = HolographicCardMode.values.byName(defaults.mode);
    effect = defaults.effect;
    foil = defaults.foil;
    contour = defaults.contour;
    depth = defaults.depth;
    motion = defaults.motion;
    sensitivity = defaults.sensitivity;
    tilt = defaults.tilt;
    auto = defaults.auto;
    physical = defaults.physical;
    pose = defaults.poseX == null
        ? null
        : Offset(defaults.poseX!, defaults.poseY!);
    original = false;
    error = null;
  }

  void reset() => setState(restoreSettings);
  CardSettings get currentSettings => CardSettings(
    mode: mode.name,
    effect: effect,
    foil: foil,
    contour: contour,
    depth: depth,
    motion: motion,
    sensitivity: sensitivity,
    tilt: tilt,
    auto: auto,
    physical: physical,
    poseX: pose?.dx,
    poseY: pose?.dy,
  );
  Future<void> export(bool fullDemo) async {
    final snapshot = currentSettings;
    setState(() => exporting = true);
    try {
      final bytes = await exportBundle(snapshot, fullDemo: fullDemo);
      final name = fullDemo
          ? 'holo-demo.zip'
          : 'holo-${snapshot.mode}-component.zip';
      downloadZip(bytes, name);
      if (mounted) setState(() => exportStatus = '已发起下载：$name');
      if (mounted)
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('已发起下载：$name · 使用点击时的等级与参数')));
    } catch (error) {
      if (mounted) setState(() => exportStatus = '导出失败：$error');
      if (mounted)
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('导出失败：$error')));
    } finally {
      if (mounted) setState(() => exporting = false);
    }
  }

  Rect get sourceRect {
    final r = (demoCard['sourceRect'] as List).cast<num>();
    return Rect.fromLTWH(
      r[0].toDouble(),
      r[1].toDouble(),
      r[2].toDouble(),
      r[3].toDouble(),
    );
  }

  AssetImage asset(String name) =>
      AssetImage('assets/holographic_card/${mode.name}/$name.png');
  void loadError(Object value, StackTrace stack) {
    debugPrint('Holo resource error: $value');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() => error = value.toString());
    });
  }

  Widget card() {
    if (original) {
      return Image(
        image: asset('source'),
        fit: BoxFit.contain,
        semanticLabel: '原始卡图',
      );
    }
    switch (mode) {
      case HolographicCardMode.height:
        return HolographicCard.height(
          key: ValueKey(mode),
          cardImage: asset('source'),
          backgroundImage: asset('background'),
          foregroundImage: asset('foreground'),
          foregroundContourImage: asset('foreground_contour'),
          foregroundBloomImage: asset('foreground_bloom'),
          backgroundSourceRect: sourceRect,
          depth: depth,
          backgroundMotionStrength: motion,
          effectStrength: effect,
          foilStrength: foil,
          contourGlowStrength: contour,
          viewSensitivity: sensitivity,
          maxTiltRadians: tilt,
          applyPhysicalTilt: physical,
          autoPlay: auto,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
          onError: loadError,
          semanticLabel: 'height 立体全息卡，可拖动',
        );
      case HolographicCardMode.medium:
        return HolographicCard.medium(
          key: ValueKey(mode),
          cardImage: asset('source'),
          foregroundContourImage: asset('foreground_contour'),
          foregroundBloomImage: asset('foreground_bloom'),
          effectStrength: effect,
          foilStrength: foil,
          contourGlowStrength: contour,
          viewSensitivity: sensitivity,
          maxTiltRadians: tilt,
          applyPhysicalTilt: physical,
          autoPlay: auto,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
          onError: loadError,
          semanticLabel: 'medium 轮廓反射卡，可拖动',
        );
      case HolographicCardMode.low:
        return HolographicCard.low(
          key: ValueKey(mode),
          cardImage: asset('source'),
          effectStrength: effect,
          foilStrength: foil,
          viewSensitivity: sensitivity,
          maxTiltRadians: tilt,
          applyPhysicalTilt: physical,
          autoPlay: auto,
          controlledTilt: pose,
          controlledActivation: pose == null ? null : 1,
          onError: loadError,
          semanticLabel: 'low 纯镭射卡，可拖动',
        );
    }
  }

  String get explanation => switch (mode) {
    HolographicCardMode.height => '前景停留在卡面，背景随视角后退。',
    HolographicCardMode.medium => '保留完整卡图，光沿前景轮廓游走。',
    HolographicCardMode.low => '以原始卡图呈现彩虹箔纹与眩光。',
  };
  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth >= 880;
          return SingleChildScrollView(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1440),
                child: Padding(
                  padding: EdgeInsets.all(wide ? 32 : 18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(11),
                              gradient: const LinearGradient(
                                colors: [Color(0xffe9cffc), Color(0xff8b9dff)],
                              ),
                            ),
                            child: const Icon(
                              Icons.auto_awesome,
                              color: Color(0xff272038),
                              size: 22,
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Text(
                            'HOLO / LAB',
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 2,
                            ),
                          ),
                          const Spacer(),
                          if (box.maxWidth > 500)
                            const Text(
                              'FLUTTER DEMO',
                              style: TextStyle(
                                color: muted,
                                fontSize: 10,
                                letterSpacing: 1.4,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 28),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '调节光效与视角',
                                  style: TextStyle(
                                    fontSize: box.maxWidth < 440 ? 23 : 30,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 1,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  demoCard['title'] as String,
                                  style: TextStyle(color: muted, fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                          TextButton.icon(
                            onPressed: reset,
                            icon: const Icon(Icons.restart_alt, size: 17),
                            label: const Text('恢复默认'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 25),
                      if (wide)
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: stage(math.max(560, box.maxHeight - 220)),
                            ),
                            const SizedBox(width: 24),
                            SizedBox(width: 350, child: controls()),
                          ],
                        )
                      else ...[
                        modeSelector(),
                        const SizedBox(height: 14),
                        stage(480),
                        const SizedBox(height: 18),
                        controls(showMode: false),
                      ],
                      const SizedBox(height: 18),
                      const Text(
                        '移动鼠标或拖动卡面，调整参数后可导出',
                        style: TextStyle(color: muted, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    ),
  );

  Widget stage(double height) => Container(
    height: height,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(22),
      border: Border.all(color: const Color(0xff30303d)),
      gradient: const RadialGradient(
        center: Alignment(0, -.1),
        radius: .85,
        colors: [Color(0xff292436), Color(0xff18181f), Color(0xff141419)],
      ),
    ),
    child: Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 18, 18, 0),
          child: Row(
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  color: Color(0xffaddec1),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                original
                    ? '原始卡图'
                    : '${mode.name.toUpperCase()} · ${pose != null
                          ? '固定角度'
                          : auto
                          ? '自动展示'
                          : '自由交互'}',
                style: const TextStyle(
                  fontSize: 11,
                  letterSpacing: 1,
                  color: muted,
                ),
              ),
              const Spacer(),
              FilterChip(
                label: const Text('原图对照'),
                selected: original,
                onSelected: (v) => setState(() => original = v),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (_, constraints) {
              final width = math.min(
                math.min(
                  (constraints.maxHeight - 36) * aspect,
                  constraints.maxWidth - 70,
                ),
                410.0,
              );
              return Center(
                child: SizedBox(
                  width: width,
                  height: width / aspect,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: .45),
                          blurRadius: 50,
                          offset: const Offset(0, 25),
                        ),
                      ],
                    ),
                    child: card(),
                  ),
                ),
              );
            },
          ),
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              '资源加载失败：$error',
              style: const TextStyle(color: Colors.redAccent),
            ),
          ),
        Text(
          explanation,
          style: const TextStyle(color: Color(0xffb9b5c5), fontSize: 12),
        ),
        const SizedBox(height: 14),
        Wrap(
          spacing: 7,
          children: [
            angleButton('自由', null),
            angleButton('正面', Offset.zero),
            angleButton('左', const Offset(-.8, 0)),
            angleButton('右', const Offset(.8, 0)),
            angleButton('上', const Offset(0, .8)),
            angleButton('下', const Offset(0, -.8)),
          ],
        ),
        const SizedBox(height: 20),
      ],
    ),
  );
  Widget angleButton(String label, Offset? value) => ChoiceChip(
    label: Text(label),
    selected: pose == value,
    visualDensity: VisualDensity.compact,
    onSelected: (_) => setState(() => pose = value),
  );

  Widget modeSelector() => SizedBox(
    width: double.infinity,
    child: SegmentedButton<HolographicCardMode>(
      style: const ButtonStyle(
        visualDensity: VisualDensity.compact,
        padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 6)),
      ),
      showSelectedIcon: false,
      segments: [
        for (final name in availableModes)
          ButtonSegment(
            value: HolographicCardMode.values.byName(name),
            label: Text(name),
          ),
      ],
      selected: {mode},
      onSelectionChanged: (v) => setState(() {
        mode = v.single;
        error = null;
      }),
    ),
  );

  Widget controls({bool showMode = true}) => Container(
    padding: const EdgeInsets.all(22),
    decoration: BoxDecoration(
      color: const Color(0xff1b1b23),
      border: Border.all(color: const Color(0xff30303d)),
      borderRadius: BorderRadius.circular(22),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '渲染模式',
          style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
        ),
        const SizedBox(height: 14),
        if (showMode) modeSelector(),
        const SizedBox(height: 7),
        Text(switch (mode) {
          HolographicCardMode.height => '立体全息 · 5 张资源',
          HolographicCardMode.medium => '轮廓反射 · 3 张资源',
          HolographicCardMode.low => '纯镭射 · 1 张资源',
        }, style: const TextStyle(color: muted, fontSize: 11)),
        divider(),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: exporting ? null : () => export(false),
            icon: const Icon(Icons.download, size: 18),
            label: const Text('导出当前组件'),
          ),
        ),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: exporting ? null : () => export(true),
            icon: const Icon(Icons.folder_zip_outlined, size: 18),
            label: const Text('导出完整 Demo'),
          ),
        ),
        Text(
          exporting ? '正在打包…' : (exportStatus ?? '导出后会下载 ZIP，当前参数将用作默认值'),
          style: const TextStyle(color: muted, fontSize: 10),
        ),
        divider(),
        knob('整体光效', effect, 1, (v) => effect = v),
        knob('镭射强度', foil, 1, (v) => foil = v),
        if (mode != HolographicCardMode.low)
          knob('轮廓反光', contour, 1, (v) => contour = v),
        if (mode == HolographicCardMode.height) ...[
          divider(),
          knob('背景景深', depth, 3, (v) => depth = v),
          knob('背景移动', motion, 4, (v) => motion = v),
        ],
        divider(),
        knob('视角灵敏度', sensitivity, 2, (v) => sensitivity = v),
        knob('倾斜幅度', tilt, .35, (v) => tilt = v),
        toggle('自动展示', '缓慢转动，鼠标交互优先', auto, (v) {
          auto = v;
          pose = null;
        }),
        toggle('卡面倾斜', '关闭后仅观察光线与内部景深', physical, (v) => physical = v),
      ],
    ),
  );
  Widget divider() => const Padding(
    padding: EdgeInsets.symmetric(vertical: 10),
    child: Divider(height: 1, color: Color(0xff33333f)),
  );
  Widget knob(
    String label,
    double value,
    double max,
    ValueChanged<double> update,
  ) => Column(
    children: [
      Row(
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: Color(0xffcecad8)),
          ),
          const Spacer(),
          Text(
            value.toStringAsFixed(2),
            style: const TextStyle(
              fontSize: 11,
              color: accent,
              fontFeatures: [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
      SizedBox(
        height: 34,
        child: Slider(
          key: ValueKey(label),
          value: value,
          max: max,
          divisions: max == .35 ? 35 : (max * 100).round(),
          label: '$label ${value.toStringAsFixed(2)}',
          semanticFormatterCallback: (v) => '$label ${v.toStringAsFixed(2)}',
          onChanged: (v) => setState(() => update(v)),
        ),
      ),
    ],
  );
  Widget toggle(
    String title,
    String subtitle,
    bool value,
    ValueChanged<bool> update,
  ) => Padding(
    padding: const EdgeInsets.only(top: 8),
    child: Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 12)),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 10, color: muted),
              ),
            ],
          ),
        ),
        Switch(value: value, onChanged: (v) => setState(() => update(v))),
      ],
    ),
  );
}
