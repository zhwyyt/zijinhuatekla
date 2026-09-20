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

## 2026-09-20 选择集实测

选择 `T3-5GKZ-1`～`16`（16 根箱型柱）。

- dump：`I:\xingcaisuanfa\cache\20260920_index_once_smoke`
- 总耗时约 11.5 min（构件 JSON ~8.7 min + 剖口索引 10.4s + bundle 157.2s）
- 索引：3697 个父零件，只建一次
- 与 `20260918_plate_cuts_batch` 中相同 16 个 `assemblyId` 比较：`edgeBevelCount` **0 条差异**
- 识别：`outputs/model-first-index-once-smoke/recognition-all.xlsx`，1709 行，失败 0；方块且倒角/洞口 = 0；剖口=是 118；方块且剖口 46

## 2026-09-20 第二批选择集（梁为主）

`T3-4HXL` / `T3-4HXZ` / `T3-6GL` / `T3-6GKL` 等，273 根装配。

- dump：`I:\xingcaisuanfa\cache\20260920_index_once_smoke2`
- 总耗时约 5.7 min（剖口索引仍 10.4s 一次，bundle 174.5s）
- 与 0918 大批量 dump 重叠 248 根 assembly：`edgeBevelCount` **0 条差异**
- 识别：`outputs/model-first-index-once-smoke2/recognition-all.xlsx`，2335 行，失败 0；方块且倒角/洞口 = 0；剖口=是 350

## 第二版加速（0.3.4-single-pass）

GitHub 回滚点（做这一刀之前的可跑通版本）：

- 导出器 `a40587d`，标签 `rollback/exporter-0.3.3-index-once-20260920`
- 识别仓库 `72553d9`（0.3.3 实测记录）

本版只改识别导出 live 路径：

1. `SamplingOptions.Enabled=false`，不再按 0.1/0.3/0.5/0.7/0.9 切截面。离线 `--reclassify-cache` 仍默认采样。
2. 选择集只走一遍：同一根 assembly 上 `ExtractAssembly` + `BuildAssemblyExport`，写出 member JSON 和 bundle。
3. 没有稳定截面样本时，若 bundle `stationLoops.closedLoopCount>0` 则把 `MainClass` 叠成 Box 并保证 `KeyDimensionsDisplay` 以 `BOX` 开头；否则若有 H `stationFrames` 则叠成 H。不覆盖已有 H/Box/T/Pipe/Angle/Cross。
4. 工作平面 / `GetLocalBoundingBox` / 共享 `GetSolid` **未改**。COM 仍单线程。

JSON 字段契约仍是 `tekla-body-bracket-export.v2-plate-face`。剖口漏检时先回滚 `rollback/exporter-0.3.3-index-once-20260920`。

回滚导出器：

```powershell
cd I:\xingcaisuanfa
git checkout rollback/exporter-0.3.3-index-once-20260920
dotnet build .\TeklaSectionClassifier.Runner\TeklaSectionClassifier.Runner.csproj -c Debug
```

## 2026-09-20 选择集实测（0.3.4）

当前选择集 289 根装配（含先前 16 根 `T3-5GKZ` 箱型柱 + 273 根梁为主的选择，另有少量新件）。`assemblyPosition` 重复 13 个号、18 根装配，member JSON 271 份。

- dump：`I:\xingcaisuanfa\cache\20260920_single_pass_smoke`
- 版本：`xingcai-runner-body-bracket-0.3.4-single-pass`，schema 仍 `v2-plate-face`
- 墙钟约 11.2 min；剖口索引 9.8s / 3697 父零件；装配循环 355s（含关采样后的 Extract+Bundle）
- 271 份 member JSON 的 `Samples` 全部为 0
- 与 `20260920_index_once_smoke` 重叠 16、`smoke2` 重叠 273、`20260918_plate_cuts_batch` 重叠 264：`edgeBevelCount` **全部 0 条差异**
- 识别：`outputs/model-first-single-pass-smoke/recognition-all.xlsx`，4044 行，失败 0；方块且倒角/洞口 = 0；剖口=是 468；方块且剖口 48

### 叠层副作用（已改代码，当前 dump 未重导）

关采样后 `FirstPassMemberClassifier` 对无型材直读的组合截面会落到 Irregular。本版用 bundle 闭合环叠成 Box。实测 bundle 上 **闭合环+H frame 同时存在 188 根**（16 根 GKZ 全是双证据），叠层无条件优先 Box，把大量 `T3-6GL` 的 H 翼缘/腹板标成 `BOX主壁板`：

- 与 smoke2 重叠零件 2335 行，主材列差异 416
- 其中 `H上翼缘/H腹板/H下翼缘 → BOX主壁板` 各 116 行，均在 `6GL`

已把叠层改成 **只在单一证据时生效**：仅闭合环→Box，仅 H frame→H，双证据不覆盖。当前 Excel 的 `6GL` 主材列不要用。重导后才会带上该修复。

## 2026-09-20 退回 0.3.3

关采样会伤主材，live 导出器已 `git revert` 0.3.4，重新编译为 `xingcai-runner-body-bracket-0.3.3-index-once`。截面采样恢复。标签 `rollback/exporter-0.3.3-index-once-20260920` 仍是可跑通回滚点。
