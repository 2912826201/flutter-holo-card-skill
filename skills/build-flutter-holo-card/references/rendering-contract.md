# Flutter 渲染与集成

完整集成使用 `scripts/integrate_flutter.py --mode MODE --bundle WORK/MODE/candidate --project TARGET`。只接受全部验收通过的 candidate，复制本 skill 的 Flutter 包（代码、三档 shader、共享 include、箔纹和许可），更新目标 pubspec 的 path dependency 与卡图 assets，保留原 pubspec 备份。该脚本不依赖作者机器上的 chaoqushang 路径。已存在的用户目录不会被静默覆盖；需要先检查差异再迁移。`asset-only` 跳过项目写入，交付对应运行时资源、共享箔纹、映射和审查报告。

包名 `build_flutter_holo_card_template`，默认箔纹与 Shader 使用 package asset 路径。若直接复制进 lib 而非保留 package，显式指定 foilImage 和 shaderAssetPath，并按模板 pubspec 注册全部 shader，保留 foil_material.glsl、contour_material.glsl 相对 include。

```dart
import 'package:build_flutter_holo_card_template/holographic_card.dart';

HolographicCard.low(cardImage: const AssetImage('assets/card/source.png'));
HolographicCard.medium(
  cardImage: const AssetImage('assets/card/source.png'),
  foregroundContourImage: const AssetImage('assets/card/foreground_contour.png'),
  foregroundBloomImage: const AssetImage('assets/card/foreground_bloom.png'),
  applyPhysicalTilt: false,
);
HolographicCard.height(
  cardImage: const AssetImage('assets/card/source.png'),
  backgroundImage: const AssetImage('assets/card/background.png'),
  foregroundImage: const AssetImage('assets/card/foreground.png'),
  foregroundContourImage: const AssetImage('assets/card/foreground_contour.png'),
  foregroundBloomImage: const AssetImage('assets/card/foreground_bloom.png'),
  depth: 1,
  // Use manifest.background_source_rect, especially for rounded pixel padding.
  backgroundSourceRect: const Rect.fromLTWH(80/1160,112/1621,1000/1160,1397/1621),
  onError: (error, stack) { /* report failed resource loading */ },
);
```

未命名构造是 height 的迁移入口，需要迁移到扩展背景和新 source rect。各档构造只要求自身资源。错误展示原图并调用 onError（未设置时 FlutterError.reportError），不伪装成另一档的成功。

## 空间与材质

pose/controlledTilt 的 x 向右、y 向上，范围 [-1,1]。controlledActivation 为 0–1；idleEffectStrength 默认 .22，effectStrength 默认 .65（1 为参考实现全强度）。关闭全部光效设 effectStrength=0。foilStrength 默认 1，设为 0 只关闭镭射材质，可独立检查轮廓反射；contourGlowStrength 默认 .35，设为 0 只关闭轮廓。autoPlay 默认为 false；开启后按 8 秒周期轻微展示，触摸/悬停优先。physical tilt 与 viewSensitivity 独立；后者只改变材质角度响应。

相机焦距为卡宽两倍，背景距离 `d=.04*min(卡宽,卡高)*depth`。逆整卡旋转得到局部相机 C；卡面点 P 的后平面交点为 `Q=P+d/Cz*(P-Cxy)`，除以中立尺度 `(1+d/f)` 恢复中立坐标，然后映射到背景 source rect。共享静态源 Alpha 裁剪全部输出；没有扩大的出框绘制区。depth=0 时内部投影恒等。

medium/low 只改变材质参数和可选整卡姿态，所有采样保持原图 UV。height/medium 的白色轮廓是随角度移动的局部反射，使用与镭射相同的光源坐标驱动斜向亮带，离开亮带后淡出；不能做成整圈常亮描边。核心线和两级光晕共用原图 UV，在高光位置局部恢复被箔光占用的亮度空间，然后限制发光能量。轮廓采用独立感知强度曲线，避免静止衰减与剩余亮度连乘导致光效消失。原图通过通用 ImageProvider 加载，图片句柄 clone 后独立释放；过期加载被取消，换图不保留旧结果。

减少动画时关闭物理旋转/景深并立即回正，保留可控的静态材质响应。屏幕大小和单轴无界约束按源图宽高比布局。运行 `flutter analyze`、`flutter test` 和示例 `flutter build web --no-web-resources-cdn`，同时按所选档的视觉要求核验实际渲染。真机/native 未运行时必须明确标记未验证。

轮廓验收必须使用非空的真实轮廓贴图：固定原图坐标和激活量，分别比较镭射开/关、轮廓开/关，以及左右/上下转动。验证高光沿线移动、非照亮区域淡出、没有全卡洗白，不能仅凭 shader 加载成功或黑色测试贴图判定有效。修改 GLSL include 后需清理相关构建缓存或更新 shader 入口，避免增量构建仍使用旧 shader。
