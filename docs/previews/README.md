# 三档动图录制

输入：阿卡丽「表里杀缭乱」450×629 原图与通过审查的三档素材。

在仓库根目录执行：

```sh
cd examples/akali_card
flutter test --dart-define=RECORD_GIFS=true test/record_readme_test.dart
cd ../..
.venv/bin/python docs/previews/encode_gifs.py
```

录制器对生产组件发送同一组真实触摸拖动事件，不使用 autoPlay 或后期伪造变形。包含静止、左右/上下拖动、松手连续回正。每档原始72帧，约4.8秒，360×480；GIF会合并重复帧并保留时长。每档使用统一256色调色板减少帧间色彩跳变。原始PNG帧位于忽略的 build/readme-frames，不随仓库提交。

参数：effectStrength=.65、contourGlowStrength=.55、默认箔纹和整卡倾斜；height 的 depth=2、backgroundMotionStrength=3。medium/low 无内部视差，low 无轮廓贴图。GIF是Flutter测试渲染器输出，不是手机录屏或原生性能证明。
