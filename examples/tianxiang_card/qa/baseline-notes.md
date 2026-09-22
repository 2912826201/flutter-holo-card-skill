# 天鹅 (EX) 全息卡试跑

这是一份当前 skill 的真实 Flutter 演示，直接依赖仓库中的 `HolographicCard` 和 `holographic_card.frag`，没有重写或修改渲染算法。使用用户提供的 2166×3025 卡图，按原比例缩放为 1000×1397，圆角半径按宽度的 4.5% 建立 Alpha。

**状态：可运行的素材试验版，未通过完整视觉验收。**

## 运行

在本目录运行：

```sh
flutter pub get
flutter run -d chrome
```

也可构建本地预览：

```sh
flutter build web --debug --no-web-resources-cdn
python3 -m http.server 5318 --bind 127.0.0.1 --directory build/web
```

然后打开 http://127.0.0.1:5318 。仅在本机监听，没有发布到互联网。

## 使用

- 在卡面上悬停或按住拖动；移出或松手后回正。
- 原图对照用于比较原始卡面和生成素材合成结果。
- 景深范围 −2 到 +2，默认 1；两个机甲、文字、特效和边框同属一个前景。
- 光效强度默认 1，设为 0 会关闭彩虹、星芒、高光、描线和 bloom，但保留倾斜、视差。
- 轮廓亮度默认 0.35。静止光效为交互强度的 22%。

## 资源与生成

五张运行时贴图位于 `assets/card/`：

- `source.png`：原图及圆角 Alpha。
- `background.png`：生成式补绘的纯场景。
- `foreground.png`：原图 RGB 加生成式前景遮罩。
- `foreground_contour.png`：归一化并限制到前景范围的轮廓。
- `foreground_bloom.png`：R/G 两级光晕。

使用内置 `image_gen.imagegen`，未使用付费 API CLI。完整提示词保存在 `qa/prompts.json`。补背景、遮罩与线稿分别进行了两次生成。使用 skill 自带的 `normalize_source.py`、`prepare_foreground.py`、`prepare_generated_lineart.py`、`prepare_structure_maps.py` 和 `check_assets.py` 处理资源。生成图只做全画布缩放，没有局部变形对齐。颜色前景未重新绘制。

## 已确认的问题

1. **线稿未通过原始输入校验。** `qa/lineart-report.json` 的 `ok` 为 false：原始生成线稿信号有 0.4689% 的画布落在前景之外；文字、装甲和框线存在位置及形状漂移。小字的生成描线还改变了字形。`qa/contour-overlay.png` 可直接看到双线。
2. **运行时检查通过不等于线稿合格。** 脚本先写出乘过前景 Alpha 的结构图，再返回错误；继续制作的演示贴图能通过 `check_assets.py` 的尺寸、通道、Alpha、前景 RGB 保真及边界检查，却不能纠正前景内部的线条偏移。本演示保留这种真实结果以便诊断，不能当作验收通过。
3. **背景与原图不同。** 生成式补绘改动了原有色调、纹理与地面环形几何；中性合成不能精确复原原图。部分前景遮罩区域还带着原图背景颜色，接缝可见。
4. **视差是整个前景平移。** 正景深大角度时，边框、文字和机甲整体出框，呈现两张卡错开的观感；负景深裁剪到原卡范围时，边缘数字和文字也会被裁切。
5. **光效偏重描线。** 这张卡原有较多白线，再加生成描线和 bloom，会显得偏亮，彩虹反光比描线克制。

完整 skill 要求 “Regenerate a shifted line-art result; do not warp individual contours into place.”（见 `../../skills/build-flutter-holo-card/SKILL.md`）。已重生成一次线稿，但结果仍有漂移，因此不声称完整素材流程验收通过，也没有运行仅在视觉验收后执行的 `cleanup_assets.py`。诊断图与报告留在 `qa/`，运行时目录只含五张 PNG。

## 验证记录

通过：

```sh
dart format lib test
flutter test
flutter analyze lib test
flutter build web --debug --no-web-resources-cdn
```

真实图片 Widget 测试覆盖五张图与 Shader 加载、原图宽高比、宽窄布局、景深 −2/0/+2、水平及垂直拖动、连续回弹、静止/激活强度和关闭光效。浏览器实际检查了默认/悬停画面、原图对照、景深 −2/0/+2 和关闭光效；截图位于 `qa/`。

资源格式检查通过，前景 RGB 与归一化原图完全相同。前景遮罩报告有较宽半透明区域警告（9.68%）；原始线稿归一化校验失败及视觉问题见上文。未做 iPhone 真机或 macOS 原生应用验证；手机宽度浏览器预览不等于真机测试。
