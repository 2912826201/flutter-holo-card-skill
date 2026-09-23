# 资源与审查流程

命令以下以 `scripts/` 为当前目录。所有制作任务使用独立输出目录；`--mode height|medium|low` 默认 height。不要将示例卡的元素归属照搬到其他卡片。

1. `normalize_source.py --mode MODE --source input.jpg --output work/source.png --corner-radius-ratio 0.045`。圆角比例必须依据输入卡形选取，不确定时提供准确灰度卡形遮罩。保留宽高比，输出 RGBA 和摘要 sidecar。
2. height/medium：根据当前原图和本卡元素清单制作**填实**灰度保留区域。遮罩只有背景 0、前景 255；仅边界一像素可抗锯齿，灰色内部被拒绝。检查人物内部、文字及面板底色、卡框和原有遮挡关系，比较蒙版叠加。生成工具输出若分辨率不同，只能整画布同宽高比对齐，并记录这一步；不能自动裁切或扭曲。
3. 实际看过叠加后，`asset_pipeline.py review-mask --mode MODE --source work/source.png --mask work/mask.png --report work/mask-review.json --decision pass --evidence work/mask-overlay.png --notes '本卡范围与对齐检查结论'`。失败用 fail。每一档单独绑定报告，哪怕使用相同遮罩。
4. height 才生成补全背景；尺寸为 `(W+2*ceil(.08W), H+2*ceil(.08H))`，原画布位于 `(ceil(.08W),ceil(.08H),W,H)`。脚本以多尺度拉普拉斯颜色校正衔接未知区域，再精确回填原图中 mask=0 的已知背景；不允许生成结果改写这些像素。此校正不替代接缝和残影的实际审查。
5. `asset_pipeline.py build --mode MODE --source work/source.png --output work/MODE`；height/medium 追加 `--mask work/mask.png --mask-review work/mask-review.json`，height 再追加 `--background work/extended-background.png`。low 不需要蒙版或生图。输出 candidate，不代表视觉验收通过。
6. 检查 candidate 中 contour-overlay、背景/前景、中立合成和 Flutter 各姿态截图，按对应档位标准审查。`asset_pipeline.py review --mode MODE --bundle work/MODE/candidate --decision pass --evidence work/screenshots/neutral.jpg work/screenshots/active.jpg --notes '实际观察及测试范围'`。不能仅凭图片打开成功就 pass。存在缺陷时 fail 并迭代。
7. `check_assets.py --mode MODE --bundle work/MODE/candidate` 通过后才能交付/集成。`--candidate` 仅用于调试，返回 accepted=false。失败重试先将原候选移入 diagnostics，不能因旧文件仍存在就继续。清理使用 `cleanup_assets.py --mode MODE --bundle ...`，只删除 manifest 中登记的 temporary_files；不删除报告、来源、叠加图或截图。

## 生图拒绝时降档

只有生成服务明确返回拒绝（如 `moderation_blocked`）才使用此路由；记录被拒绝的步骤、服务返回的原始错误和已尝试档位。错误没有给出具体理由时不要猜测原因。停止使用当前档位的候选产物，将其留在 diagnostics，然后从同一原图和当前输入摘要开始下一档；不复用被拒绝或未通过审查的文件，也不改写上一档报告为通过。

- `height` 的遮罩或补背景生图被拒绝：尝试 `medium`。它只从原图提取前景线条及 bloom，不需要背景补绘或前景彩色生成；前景范围仍须用可靠的非生图方法确定，并按 medium 独立审查遮罩与轮廓。审查不合格时在 medium 内继续修正，不冒充通过，也不因此降到 low。
- `medium` 若仍有必需的生图请求被明确拒绝：尝试 `low`。`low` 只用原图与共用箔纹，不调用生图；按 low 标准重新 build、review、check。

降档后使用实际档位的 `--mode`、资源清单、Flutter 构造和验收标准。最终说明请求档位、实际档位、拒绝发生的位置与各档验收结果。生成结果质量差、尺寸错误、对不齐或格式/几何/视觉审查失败时，在当前档持续迭代直到通过验收；不能把它们写成“被拒绝”并自动降档。工具超时或脚本报错应在当前档排查恢复，同样不触发降档。

## 确定性制作

`asset_pipeline.py` 对原图做高斯降噪、Sobel 梯度、非极大值抑制与滞后阈值筛选，仅保留遮罩范围内的边缘。轮廓为不透明灰度 RGBA；bloom 为 R 近光晕、G 远光晕、B=0、A=255。前景 RGB 逐像素复制原图。medium 不输出运行时前景彩图。

旧 prepare_foreground/prepare_generated_lineart/prepare_structure_maps 命令已明确拒绝 v1 工作流，防止绕过摘要和上游审查。新的默认流程不接收 AI 线稿。检查重算源图边缘以发现偏移/重画；额外线条污染与棋盘格底色应分别诊断，不能把一般越界线条一律标成棋盘格。

## 验收状态与可移植性

manifest schema 2 包含 mode、源画布、背景 source rect、运行时与辅助文件 SHA-256、上游输入摘要、format/geometry/visual 独立状态。视觉结论绑定运行时文件、蒙版叠加和证据摘要。制作阶段的输入与证据路径用于追溯，请保留工作目录；迁移工作目录需重新绑定/复核，不能删掉验证失败条件。最终应用运行时不读取这些绝对路径。

`format` 表示文件可解码/资源齐全；`geometry` 表示坐标、尺寸、所有权、源 RGB 与提取算法一致；`visual` 表示实际审查。结构正确不证明语义分割、填补背景或镭射观感正确。原生结果单独记录；Web 截图不是手机 GPU 验证。

通过最终 check 后，asset-only 使用 `export_assets.py --mode MODE --bundle WORK/MODE/candidate --output delivery/MODE`，输出对应运行时图片、共享箔纹、许可与使用相对证据路径的验收清单。导出目录需为新版本，防止覆盖旧交付。
