# Flutter Holo Card Skill ✨

把一张平面卡图制作为 Flutter 双层全息镭射卡：背景独立移动，人物、文字、边框、面板和前景特效保持原有遮挡关系并作为一个完整前景移动。

## 效果结构

Skill 只保留一种稳定方案：

- `background.png`：补全后的纯场景背景，整张画布不透明；
- `foreground.png`：人物与所有非背景元素合并，颜色直接来自原图；
- `foreground_contour.png`：覆盖整个前景的白色素描线稿；
- `foreground_bloom.png`：线稿的近距离与宽距离光晕；
- `source.png`：原图与卡片圆角 Alpha。

不再生成独立人物层，也没有 layered/merged 模式切换、人物遮住 UI 时的补绘分支或安全拒绝降级分支。人物五官、服饰、文字和边框不会经过彩色重绘，减少不同生成结果之间的漂移。

## 镭射表现

- 背景与合并前景使用不同 UV，默认景深即可看到层次；
- 卡片轻微倾斜，内部材质响应更明显且不会过早进入夹紧死区；
- 宽幅棱镜色带、细密衍射、稀疏星芒和高光共同响应观察方向；
- 静止时保留克制的镭射质感，按住或悬停时平滑增强；
- 彩虹只轻量染色，不用高透明度颜色覆盖原画；
- 白色素描高光覆盖人物、物件、前景特效、文字、符号、面板、Logo 和卡框；
- 两级 bloom 形成真实光晕，不再被压回单像素线芯；
- 组件按资源原始比例适配父布局，避免卡面被拉伸。

## 安装

将完整的 `skills/build-flutter-holo-card` 目录安装到 Agent 的 Skills 目录。Codex 用户可以使用：

```text
请使用 $skill-installer，从 https://github.com/2912826201/flutter-holo-card-skill.git 的 skills/build-flutter-holo-card 路径安装这个 Skill。
```

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

## 使用

完整生成资源并集成 Flutter：

```text
使用 $build-flutter-holo-card，把这张图做成 Flutter 全息卡。
```

只生成五张运行时资源：

```text
使用 $build-flutter-holo-card，asset-only，只生成并验证双层全息卡资源，不修改 Flutter 代码。
```

Flutter 组件的核心 API：

```dart
HolographicCard(
  cardImage: const AssetImage('assets/card/source.png'),
  backgroundImage: const AssetImage('assets/card/background.png'),
  foregroundImage: const AssetImage('assets/card/foreground.png'),
  foregroundContourImage:
      const AssetImage('assets/card/foreground_contour.png'),
  foregroundBloomImage:
      const AssetImage('assets/card/foreground_bloom.png'),
)
```

默认 `depth = 1`、`viewSensitivity = 3`、`maxTiltRadians = 0.24`。可用 `effectStrength = 0` 完全关闭镭射和线稿光效。

## 本地验证

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests

cd skills/build-flutter-holo-card/assets/flutter
flutter pub get
dart format --output=none --set-exit-if-changed lib test
flutter analyze lib test
flutter test
```

## 原型与许可

项目参考了 [LerSent001/holo-card](https://github.com/LerSent001/holo-card) 的分层视差、轮廓光和全息材质思路，并针对 Flutter Runtime Shader 与更稳定的双层素材流程重新实现。

代码和文档使用 [MIT License](LICENSE)。演示视频中的卡面、美术、角色、商标与其他第三方内容仍归各自权利方所有，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
