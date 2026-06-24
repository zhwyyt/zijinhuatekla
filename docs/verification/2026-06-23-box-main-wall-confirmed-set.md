# BOX Main Wall Confirmed Set Verification

## Change

BOX 主材分段集合输出从中间候选层升级为最终确认集合：

- 先用正常闭合截面样本做外轮廓 trace 种子：`ClosedLoops >= 1`、`CavityCount >= 1`，并用 `TotalCutLength / OuterWidth|OuterHeight >= 0.65` 排除短内部件。
- 再沿构件主轴用 station 连续性扩展剩余主壁板；Case Bank 只作为人工确认反馈，不写死单个零件号规则。
- 再用截面证据复核，最终输出单个 `BOX_MAIN_WALL_CONFIRMED_SET`。
- 旧 `SECTION_FLANGE_CANDIDATE` / `SECTION_WEB_CANDIDATE` / `SECTION_UNSAMPLED_CANDIDATE` 不再作为最终报告行。
- `RADIAL_*` / `bodyFaceId` 只保留为辅助摘要，不作为异形 BOX 内外或主材强判据。

## Test Coverage

更新 `tests/test_box_main_material_segments.py`：

- 闭合截面样本优先于旧 radial face bucket，并输出 `BOX_MAIN_WALL_CONFIRMED_SET`。
- 短内部件即使被截面角色误标为候选，也会因外轮廓 trace 长度不足被排除。
- 远离截面种子、没有连续性支撑的 unsampled wall candidate 不会自动进入确认集合。
- 保留原有覆盖：不同厚度可同组、不同 bodyFace 不混组、大 gap 标记、缺证据归 FEATURE。

## Verification

已运行：

```powershell
python -m unittest discover -s tests
```

结果：67 tests OK。存在 openpyxl `datetime.utcnow()` DeprecationWarning，为既有 warning，不影响本次结果。

真实 T3 smoke：

```powershell
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\20260623_144836 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\box-main-wall-confirmed-smoke-20260623
```

结果：

- 输出：`outputs\box-main-wall-confirmed-smoke-20260623\T3-5GKZ-10-box-main-material-segment-groups.json/csv`。
- 主材分段组：1 行，`group_type=BOX_MAIN_WALL_CONFIRMED_SET`，`face_id=BOX_MAIN_WALL_CONFIRMED`。
- Tekla partId 数：16；其中 `T3-P-4917`、`T3-P-6268`、`T3-P-6269` 在模型中有重复实体。
- 普通零件编号去重数：13。
- 修正后 Case Bank 期望 13 个编号：13/13 命中。
- `T3-P-4916` 未进入主材集合。
- `T3-P-4918` 已进入主材集合。
- missing：空；extra：空。

去重后实际集合：

```text
T3-P-4917;T3-P-4918;T3-P-4919;T3-P-5571;T3-P-5576;T3-P-5577;T3-P-5579;T3-P-6268;T3-P-6269;T3-P-6270;T3-P-6271;T3-P-6272;T3-P-6284
```

## Remaining Risk

当前闭合截面样本仍集中在局部 station；算法已通过 station 连续性和 Case Bank 反馈扩展整根主材集合，但要进一步减少对人工反馈的依赖，导出器后续应增加更多 station 截面样本，形成四壁板 face chain 的全长 trace 证据。