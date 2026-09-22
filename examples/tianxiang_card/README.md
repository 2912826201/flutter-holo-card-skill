# 天鹅 EX · 三档实卡对照

演示直接引用当前 skill 的 Flutter 包。输入为用户提供的卡图，归一化为 1000×1397；height 使用每边 8% 延展背景，medium/low 保留完整原图。

```bash
flutter pub get
flutter run -d chrome
# 或生成可以离线加载 CanvasKit 的 Web 文件
flutter build web --debug --no-web-resources-cdn
python3 -m http.server 5320 --bind 127.0.0.1 --directory build/web
```

本次预览地址：[三档对照](http://127.0.0.1:5320/)。切换 height/medium/low，提供原图对照、光效强度、关闭整卡倾斜、轮廓叠加和九个固定姿态；height 额外提供 0–3 背景距离。默认镭射强度 0.65；按住拖动或悬停会增强反射，释放后连续回正。

[最终默认画面](qa/v2/final-default.jpg) · [倾斜状态](qa/v2/final-height-active.jpg) · [27 组景深对照](qa/v2/final-height-contact-sheet.jpg) · [验证记录](qa/v2/validation.md)

已生成可移植资源包：[height](deliverables/height/manifest.json)、[medium](deliverables/medium/manifest.json)、[low](deliverables/low/manifest.json)。每包包含对应运行时图片、共用箔纹、许可证和摘要绑定的视觉证据。使用 skill 的 `export_assets.py --mode MODE --verify deliverables/MODE` 可重新核验导出内容。

当前三档资源均通过本地格式、几何与所记录范围内的 Web 视觉检查。Python 19 项、模板 Flutter 15 项、实卡 Widget 1 项通过；Flutter 分析及 Web 构建通过。未执行 macOS/iOS/Android 应用或真机验证，不能将浏览器结果当成原生通过。

本次素材从源图提取细线及 bloom，修正了旧生成遮罩的内部孔洞和细框遗漏，补全背景后进行边界颜色衔接并回填原图已知背景。详细提示词保存在 `qa/v2/prompts.json`，本卡修正步骤在 `qa/v2/prepare_demo.py`。

旧截图、失败线稿和旧报告保留在 `qa/`；旧说明见 [baseline-notes.md](qa/baseline-notes.md)。被替代的候选保留在各档 `diagnostics/`，不打包进演示或最终交付。源卡图和美术内容的权利归原权利方；镭射材质来源与 GPL-3.0 许可随 Flutter 包和资源包附带。
