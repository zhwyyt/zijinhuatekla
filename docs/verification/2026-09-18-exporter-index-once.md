# 2026-09-18 导出器回滚点与第一版加速

## GitHub 回滚点（优化前可跑通的版本）

识别仓库 `zijinhuatekla` 分支 `codex/box-progressive-drawing`：

- 提交 `c57043d`
- 标签 `rollback/model-first-plate-cuts-20260918`

导出器仓库 `xingcaisuanfa` 分支 `codex/upstream-axis-audit-20260428`：

- 提交 `2ed1d08`（exporter `0.3.2-plate-face`）
- 标签 `rollback/exporter-0.3.2-plate-face-20260918`

回滚导出器：

```powershell
cd I:\xingcaisuanfa
git checkout rollback/exporter-0.3.2-plate-face-20260918
dotnet build .\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj -c Debug
```

## 第一版加速（0.3.3-index-once）

bundle 阶段不再对每根 assembly 全模型扫描 EdgeChamfer / Fitting / CutPlane，改为 **Write() 入口建一次 father→对象索引**。零件的 GetBooleans / GetBolts / GetWelds 只枚举一次。进度每 10 根打一行。不再写空的 `assembly-*.labels.template.json`。

JSON 字段契约仍是 `tekla-body-bracket-export.v2-plate-face`。剖口漏检时先对照 `T3-H-574`、板边楔体矩形板，再回滚到 `0.3.2-plate-face`。
