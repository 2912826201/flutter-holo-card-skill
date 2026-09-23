# Demo 与一键导出

用户未指定等级时生成三档 Flutter Web Demo，初始 height；组件与 Demo 默认 `effectStrength=.8`、`foilStrength=1`，保留共享参考材质。仅明确请求 medium 时只需素描，low 不生图；不要为单档演示准备其余档位。

## 生成

先按资源流程验收用户所需的 candidate。三档 Demo 的同源素材只生成一次，medium 复用素描，low 复用原图。生成器会校验各档审查和 source 摘要，并从随包模板复制组件、Shader 和演示界面，不重新制作图片。

```sh
python scripts/create_demo.py --height WORK/height/candidate --medium WORK/medium/candidate --low WORK/low/candidate --output DELIVERY/demo --title '全息卡实验台'
```

明确要求单档 Demo 时只传该档，例如：

```sh
python scripts/create_demo.py --mode medium --medium WORK/medium/candidate --output DELIVERY/demo
```

在输出目录执行 `flutter pub get`，`flutter analyze`，`flutter test`，再以 `flutter run -d chrome` 打开，或 `flutter build web --release --no-web-resources-cdn` 后用静态服务器打开 build/web。运行时包原始 Shader 参考回归位于 `assets/flutter/test/`。生成器不覆盖已有目录；更新已有 Demo 前检查其差异。

## 两个按钮

- **导出当前组件**：浏览器本地下载 ZIP。使用点击时的等级和参数快照；将光效、镭射、适用的轮廓/景深/背景移动、视角灵敏度、倾斜幅度、自动展示、物理倾斜、固定姿态写入 `SelectedHoloCard` 构造默认值。仅含该档的原图及所需图片、共用箔纹、所需 Shader/include、组件实现、pubspec、映射/选择记录与许可证。无调参 UI、无其他档位图片。README 提供 path dependency 和组件使用方式。
- **导出完整 Demo**：包含所有已请求档位、资源、完整 Flutter Web 工程源码和两个导出按钮。保存当前等级与参数，重新打开及“恢复默认”都使用这组值；导出的 Demo 可再次导出。无绝对本地路径、临时审查截图或编译缓存。

两个按钮都是代码/资源导出，不是截图。打包期间按钮禁用并显示状态，异常明确提示；不重新生成图片、不上传源图、不依赖后端。原图对照只是查看开关，不改变导出的组件；自动展示保存开关，不冻结动画中的瞬时角度。固定姿态会被保存。

## 验证

需要检查当前档资源数（不含共用箔纹）：height 5、medium 3、low 1；测试导出 ZIP 的 CRC、所选值、包内图片与当前素材字节一致、完整 Demo 再次导出。至少解压组件包并通过消费项目编译，解压完整 Demo 并构建；浏览器实测按钮能触发 ZIP 下载及三档/参数切换。

## assets-only

`height assets-only`、`medium assets-only`、`low assets-only` 分别只运行对应资源流程和 `export_assets.py --mode MODE`，不创建 Demo/组件、不调用 create_demo.py。兼容 `asset-only`。只有无等级的 assets-only 才交付三档资源合集；共用素材复用。资源交付附带最小映射和素材审查记录，不能声称已验证动态渲染。
