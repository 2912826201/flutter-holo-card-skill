# 表里杀缭乱 · 三档 Flutter 预览

预览：http://127.0.0.1:5321/ 。鼠标悬停或拖动卡片，切换 height / medium / low。可关闭镭射单独检查反射轮廓，或将光效强度设为零对照原图。

- height：人物、双武器、徽记、黑银边框、红白文字面板固定；插画背景后退。
- medium：完整原图＋前景反射轮廓，无内部视差。
- low：完整原图＋共享箔纹，无分层/轮廓。

原始输入 450×629，保留原始像素尺寸，不进行 AI 超分或文字重绘。圆角比例 .055。height 背景 522×731，源区域 (36,51,450,629)。mask 生图 1061×1483、背景生图 1060×1484，均检查宽高比误差低于 1% 后整画布缩放，无裁切；prepare_mask.py 记录前景范围修正。

本次通过内置 imagegen 制作遮罩和未知背景，提示词记录于 work/prompts.md。low 不依赖生图产物。前景 RGB、轮廓与两级 bloom 由 skill 脚本直接取自原图。

运行：在本目录执行 `flutter pub get`、`flutter run -d chrome`；静态预览可 `flutter build web --debug --no-web-resources-cdn` 后 `python3 -m http.server 5321 --bind 127.0.0.1 --directory build/web`。

验收：Flutter analyze、3 个真实卡图渲染测试及 Web debug 构建通过。qa/depth-grid.jpg 记录 height 27 姿态，qa/*-active.jpg 为浏览器实测。height/medium 测试轮廓开关、镭射开关、激活量、高光随角度移动、Alpha不变与全光效关闭一致性；low 测试全光效关闭一致性。Web 宽屏和窄屏已观察，未验证原生设备。放大预览的文字清晰度受 450×629 输入限制。

work 为可追溯制作目录；deliverables 为通过分档审查的资源包。旧失败候选仅保留在 work/*/diagnostics，不供预览加载。当前示例通过相对 path dependency 使用仓库中的 Flutter skill 模板，无 chaoqushang 本机路径依赖。
