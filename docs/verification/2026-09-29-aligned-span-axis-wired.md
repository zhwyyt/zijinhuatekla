# 2026-09-29 主轴改为分组跨度

规则正文：`docs/design/2026-09-29-aligned-span-member-axis.md`。

主材提取和 Body/Bracket 导出共用 `AlignedSpanMemberAxis`。方向按零件局部轴 5° 分组，取合并跨度最大的一组；轴线过贴合零件的面积加权中心；长度含该组零件和质心落在截面半径内的零件。来源字段为 `assemblyParts.alignedSpanCentroid`。

`TeklaSectionClassifier.Runner` Debug 编译通过，0 错误。已有 cache 仍是旧轴，要在 Tekla 里重新导出后才会变成这套方向。
