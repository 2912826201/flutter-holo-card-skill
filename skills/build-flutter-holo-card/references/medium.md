# medium：固定原图＋前景轮廓反射

只生成一张前景素描。运行时为 source.png、foreground_contour.png、foreground_bloom.png，加共用箔纹。不分离前景、不补背景、不制作归属蒙版。

使用[共用素描提示词](resource-workflow.md#前景素描提示词)；生成线条直接制作轮廓和 bloom，不从原图重新提取边缘。素描达到 75 分就使用；局部省略和轻微偏差按[质量评分](quality-policy.md)接受。最多首轮加一次编辑，拒绝或预算用尽后报告缺项，不自动转向程序描线或 low。

asset-only 检查原图及轮廓叠加，组合通过线 80；完整集成再确认轮廓高光随角度移动、文字可读、原图/轮廓/bloom UV 一致。此档无内部视差，这是预期行为。
