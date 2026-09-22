# low：参考镭射基线

仅 source.png 和随包 holographic_foil.png。不要调用生图，不制作遮罩、分层、线条或 bloom。normalize 后直接 build。

验收：只加载两张纹理；内部 UV 固定；光效为零与原图一致。用同一原图、箔纹、uPointer 和激活量，对比参考 Full Art 材质的双向彩虹、箔纹、眩光；随姿态连续变化，无接缝/闪烁/明显摩尔纹，文字与亮部可读。参考公式保存在共享 foil_material.glsl，来源和 GPL 许可随包附带。浏览器和原生 GPU 分开记录。
