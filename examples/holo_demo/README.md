# Holo Lab

Flutter Web 全息卡 Demo。可预览已打包的档位、调整效果，并导出当前组件或完整 Demo。

```sh
flutter pub get
flutter run -d chrome
```

构建静态网页：`flutter build web --release --no-web-resources-cdn`，然后将 `build/web` 放到静态服务器。

- **导出当前组件**：将当前档位和参数设为组件默认值，打包该档所需的图片、Shader 与源码。
- **导出完整 Demo**：打包已包含的档位、资源和调参界面；重新打开后使用导出时的档位与参数。

ZIP 在浏览器本地生成。`lib/demo_defaults.dart` 保存初始参数，`assets/export_payload.json` 保存可再次导出的源码与资源清单；保留这两个文件才能使用导出功能。原图对照仅用于预览，不改变导出的组件。

材质与箔纹的来源及许可见 `packages/build_flutter_holo_card_template/licenses/`。卡图按其自身授权使用。
