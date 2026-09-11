# Flutter Holo Card Skill ✨

让一张普通卡图在 Flutter 里“活”起来：轻轻拖动，前景浮起、背景退后，彩虹镭射沿着卡面流动，人物轮廓也会跟着亮起来。小时候舍不得买的闪卡，现在可以自己搓啦。

## 先看效果

[![Flutter 全息卡演示](docs/demo.gif)](docs/demo.mp4)

> 点击动图可播放原视频。GitHub 首页会直接展示动态预览，不用先下载再脑补效果。

## 它会闪出什么

- 前景与背景会产生反向视差，卡面看起来更有纵深。
- 彩虹镭射、斜向扫光和细碎星芒会随观察角度流动，不是简单换几个颜色。
- 人物可见轮廓会泛起柔和高光，让主体更“跳”出卡面。
- 小幅拖动也能带动材质、扫光、轮廓和景深，适合 App 中克制的卡片倾角。
- 按住、拖动、松手的过渡保持连贯，卡片会自然回正。
- 背景和前景两层就能完成效果，不需要把人物单独拆成第三个移动图层。

## 谁可以用

它并不挑模型。只要你的 AI Agent 能查看图片、调用图片生成或编辑工具、读写本地文件、运行 Python，并能修改 Flutter 工程，就可以照着这套流程干活。

`SKILL.md`、资源处理脚本、Flutter 组件和 Shader 都是通用部分；`agents/openai.yaml` 只是给 OpenAI/Codex 准备的可选界面信息，不影响其他 Agent 使用。

## 让 AI Agent 帮你安装

不想自己搬文件？把下面这段完整丢给具备文件和命令行工具的 AI Agent：

```text
请从下面的 GitHub 仓库安装 build-flutter-holo-card：

仓库：https://github.com/2912826201/flutter-holo-card-skill.git
Skill 路径：skills/build-flutter-holo-card

请先识别当前 AI Agent 的 Skill 安装机制：
1. 如果支持 SKILL.md 或 Agent Skills，请将整个 Skill 目录安装到当前用户的 Skills 目录，不要只复制 SKILL.md。
2. 如果不支持自动发现 Skill，请保留完整仓库，并告诉我今后如何让 Agent 先读取该 SKILL.md 再执行任务。
3. 若同名目录已经存在，不要直接覆盖，先告诉我并询问如何处理。
4. 安装所需的 Python 依赖，并检查 scripts、references、assets 与 SKILL.md 是否完整。
5. 完成后告诉我在当前 AI Agent 中的具体调用方式。
```

### Codex 兼容入口

Codex 用户也可以直接复制这一句：

```text
请使用 $skill-installer，从 https://github.com/2912826201/flutter-holo-card-skill.git 的 skills/build-flutter-holo-card 路径安装这个 Skill。
```

## 手动安装

把完整的 `skills/build-flutter-holo-card` 目录放进你的 AI Agent 所使用的 Skills 目录。不同工具的目录位置并不相同，请以对应工具的说明为准。

Codex 的默认位置通常是：

```text
~/.codex/skills/build-flutter-holo-card
```

## 开始做卡

安装完成后，附上卡图并告诉 Agent：

```text
请读取并执行 build-flutter-holo-card 的 SKILL.md，把这张图制作成 Flutter 全息卡资源和可测试组件。
```

在支持 Skill 调用语法的环境中，也可以直接调用 `build-flutter-holo-card`；例如 Codex 可使用：

```text
使用 $build-flutter-holo-card，把这张图做成 Flutter 全息卡。
```

Skill 会准备卡片资源，并给出可接入 Flutter 项目的组件、`CustomPainter` 与 Runtime Shader。示例模板在 `skills/build-flutter-holo-card/assets/flutter`，资源处理脚本在 `skills/build-flutter-holo-card/scripts`。

### 只生成资源图

已经有自己的 Flutter 实现，只想让 Agent 把“闪卡食材”备好吗？可以明确启用仅资源模式：

```text
请使用 build-flutter-holo-card 的仅资源模式处理我提供的卡图。只生成并校准 source.png、background.png、foreground.png、character_contour.png 和 character_bloom.png 这五张运行时图片，使用临时对齐预览完成检查并报告结果。不要创建或修改任何 Flutter、Dart、Shader、页面、路由、测试或 pubspec 代码。
```

在 Codex 中也可以这样说：

```text
使用 $build-flutter-holo-card，只生成并校准全息卡所需资源图，不生成或修改代码。
```

`alignment-overlay.png` 只在生成阶段用来检查轮廓是否贴合。验收完成后，Skill 会自动清掉它以及选择板、遮罩、其他临时预览和校准报告，输出目录只留下五张运行时资源。`source.png` 既负责加载失败时的原图降级，也提供卡片圆角的静态 Alpha 遮罩，所以不能丢。

## 本地验证

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests

cd skills/build-flutter-holo-card/assets/flutter
flutter pub get
flutter analyze lib test
flutter test
```

## 致谢 💫

本项目参考了 [LerSent001/holo-card](https://github.com/LerSent001/holo-card) 的图层视差、轮廓光与全息材质思路，并把它实现为 Flutter Runtime Shader 版本。

为了让工作流更适合通用图片生成环境，这个 Flutter 版本收敛了生成范围，去掉了补绘被遮挡主体、恢复隐藏细节等更容易触发安全策略拒绝的环节。感谢原项目把这套闪闪发光的想法开源出来。

## License

代码与文档使用 [MIT License](LICENSE)。演示视频由用户提供，视频中的卡面、美术、角色、商标与其他第三方内容仍归各自权利方所有。
