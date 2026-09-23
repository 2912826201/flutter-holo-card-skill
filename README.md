# Flutter Holo Card Skill

把一张静态卡图变成可交互的 Flutter 全息卡。拖动或悬停时，彩虹箔纹与眩光会随视角流动；松手后卡片平滑回正。选择 `height`、`medium` 或 `low`，即可决定是否加入景深和前景轮廓反射。

## 三种效果

下面是同一张卡在相同拖动轨迹下的实际 Flutter 渲染效果：

| `height` · 立体全息 | `medium` · 轮廓反射 | `low` · 纯镭射 |
| :---: | :---: | :---: |
| ![height：背景随视角移动，人物和卡框保持在卡面，前景轮廓反光](docs/previews/height.gif) | ![medium：完整原图不产生内部视差，前景轮廓随视角反光](docs/previews/medium.gif) | ![low：完整原图上的彩虹箔纹与眩光](docs/previews/low.gif) |
| 前景固定、背景后退，轮廓随角度被照亮 | 卡图保持完整，只让前景线条反光 | 保留原图，只叠加彩虹箔纹与眩光 |

### `height`：有景深的立体卡片

人物、文字和边框保持在同一卡面，补全的背景位于后方。转动卡片时，背景产生透视视差，前景轮廓像反射光一样局部亮起。景深和背景移动强度均可调节。

### `medium`：没有景深的轮廓反射

完整原图始终保持原位。Skill 从原图提取前景线条，反光沿人物、装备和卡框随角度移动，背景不参与描线。适合想保留卡面原貌，同时增强细节的卡片。

### `low`：简洁的镭射卡

直接在完整原图上叠加彩虹箔纹与眩光，不制作分层或轮廓。适合只想要角度变色效果的卡片。

## 功能

- **原图优先**：保留卡面人物、文字与边框的颜色和位置；`height` 只补全背景中需要显露的区域。
- **随手势响应**：支持鼠标悬停、触摸拖动、平滑回正，也支持由应用控制姿态；整卡倾斜和自动展示可单独开关。
- **效果可调**：可分别调节镭射材质、轮廓反光和整体光效；`height` 还可调节景深与背景移动。
- **交付到 Flutter 项目**：Skill 制作所选档位的卡图资源，并集成配套组件、Shader 和箔纹；使用 `asset-only` 时只交付资源。

## 使用

将 [`build-flutter-holo-card`](skills/build-flutter-holo-card/SKILL.md) 安装到 Skills 目录，然后附上卡图并指定效果：

```text
使用 $build-flutter-holo-card，height，把这张卡集成到 Flutter 项目。
使用 $build-flutter-holo-card，medium，保留原图并让前景轮廓随角度反光。
使用 $build-flutter-holo-card，low，asset-only。
```

不指定档位时使用 `height`。`asset-only` 可与任一档位组合。

材质来源及许可见 [第三方说明](THIRD_PARTY_NOTICES.md)。
