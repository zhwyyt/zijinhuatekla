# Zijinhua Tekla

Tekla 深化模型识别与加工口径分析项目。

当前第一阶段聚焦：把已深化模型导出的 JSON/bundle 与加工清单 Excel 对齐，识别主材、派生加工板、零件加工尺寸、工序和冲突证据。

## 快速验证

```powershell
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs
```
