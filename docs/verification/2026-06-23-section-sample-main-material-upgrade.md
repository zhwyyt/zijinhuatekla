# Section Sample Main Material Upgrade Verification

## Change

BOX 主材分段算法从旧 `bodyFaceId/RADIAL_*` face bucket 升级为优先消费新版 `members/member_*.json` 的截面采样证据：

- 非异常截面样本且 `ClosedLoops >= 1`、`CavityCount >= 1` 时，使用 `SectionParts[].RoleHint` 生成 `SECTION_FLANGE_CANDIDATE` / `SECTION_WEB_CANDIDATE` 组。
- 使用 `member.Parts[].AxisProjection` 覆盖旧 root bundle station，避免新截面证据与旧 station 坐标混用。
- 未被正常截面采样切到的候选，仅在 member role 为 `wall_candidate`、bundle name 为 `COLUMN`，或 Case Bank 人工确认集合包含该 `partPosition` 时，保留为 `SECTION_UNSAMPLED_CANDIDATE`。
- 旧 `RADIAL_*` 只保留在 evidence summary，不再作为 BOX 主材分组核心。

## Verification

已运行：

```powershell
python -m unittest discover -s tests
```

结果：66 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\section-samples-main-material-smoke-20260623-v5
```

结果：

- 输出 `T3-5GKZ-10-box-main-material-segment-groups.json/csv`。
- 分组行数：25。
- `SECTION_FLANGE_CANDIDATE=6`。
- `SECTION_WEB_CANDIDATE=6`。
- `SECTION_UNSAMPLED_CANDIDATE=13`。
- 修正后人工确认的 13 个主材分段编号：13/13 召回。
- `T3-P-4916` 已修正为非主材短局部件；`T3-P-4918` 是主材长板并纳入 Case Bank 确认集合。

GL 回归：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_135923 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-6GL-110 --out outputs\section-samples-gl-regression-20260623-v2
```

结果保持：

- `TOP_FLANGE=T3-P-4866`，`CONTINUOUS`。
- `WEB=T3-P-4753`，`CONTINUOUS`。
- `BOTTOM_FLANGE=T3-P-4863;T3-P-5555;T3-P-4862`，`CONTINUOUS`。

## Remaining Risk

当前 `SECTION_UNSAMPLED_CANDIDATE` 仍是候选保留层，不等同于已由闭合截面直接证明。后续应让导出器增加更多 station 截面样本，或在 Python 侧用多 station wall trace 进一步把四个壁板面分成稳定 face chains。

