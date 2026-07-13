# Zijinhua Tekla

Tekla 深化模型识别与加工口径分析项目。

当前第一阶段聚焦：把已深化模型导出的 JSON/bundle 与加工清单 Excel 对齐，识别主材、派生加工板、零件加工尺寸、工序和冲突证据。

当前也提供平板零件离线出图引擎：消费 `partDrawingSnapshot.v1` 快照，按 `partPosition` 归并并输出可人工复核的 DXF、PDF 和 drawing JSON。`OK` 表示自动出图完整，不代表生产放行。

## 快速验证

```powershell
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs
python -m zijinhua_tekla.cli draw-parts --snapshot-root tests\fixtures\part_drawing --out outputs\part-drawings
```

包含中文文字的 PDF 需要通过 `--cjk-font <ttf-path>` 显式提供可嵌入的 CJK TrueType 字体。
