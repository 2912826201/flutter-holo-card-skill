# Holo Lab

可调参数的 Flutter Web 全息卡 Demo。三档均保留原始 Full Art 彩虹箔纹和眩光。
只有指定档位的交付会限制可选档位，不会补生成其他档位素材。

```sh
flutter pub get
flutter run -d chrome
```

发布静态网页：`flutter build web --release --no-web-resources-cdn`，将 build/web 放到静态服务器。

- 导出当前组件：使用点击时的等级、光效、轮廓、景深、视角、自动展示、物理倾斜及固定角度作为默认值；仅带当前等级的运行图片、所需 Shader 和许可证。
- 导出完整 Demo：保留全部可选等级、全部资源与导出按钮；重开后选中导出时的等级和参数。“恢复默认”恢复这组保存值。
- 导出在浏览器本地生成 ZIP，不需要服务端或额外生图。原图对照只是预览开关，不会把组件导出成一张静态图；自动动画只保存开关，不冻结当前动画帧。
- 安装的生成工具会自动写入 demo_defaults.dart 和 export_payload.json；不要手工删除源文件清单，否则无法完整导出。

组件所带材质及箔纹许可见 packages/build_flutter_holo_card_template/licenses。卡图权利归原权利方。
