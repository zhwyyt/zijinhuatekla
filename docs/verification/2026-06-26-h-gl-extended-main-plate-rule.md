# H/GL 扩展主板规则撤回记录

日期：2026-06-26

## 结论

本文件原记录的 `H_GL_CONNECTED_WALL_MAIN_PLATE` 规则已撤回，不再作为当前算法依据。

撤回原因：该规则把 `member.Classification.PartRoles`、零件长连续性和焊接/接触关系组合成 H/GL 主板判据。这个方向与当前主材识别原则冲突：H/GL 异形主板应优先由 `assembly.metadata.hBeamSectionEvidence.stationFrames[].partSlices` 的切面/loop/topology 证据确认，`name`、`PartRoles` 和关系只能作为解释、fallback 或调试线索，不能直接升级为主判据。

## 保留事实

用户已人工确认 `T2-3GL-55` 中以下零件属于异形 H/GL 主板：

- `T2-3B-526`
- `T2-3B-797`
- `T2-3B-508`

该事实保留在 `cases/seed.json` 和 `docs/verification/2026-06-26-t2-3gl-55-main-plate-confirmation.md`，用途是 Case Bank / 回归验收事实，不是隐藏硬编码规则。

## 当前代码口径

当前已移除以下错误抽象：

- `_h_gl_extended_main_plate_groups`
- `_is_long_h_gl_wall_candidate`
- `_has_edge_ids`
- H/GL 主材角色中由 `PartRoles` 推导 `FLANGE/WEB/EXTENDED_MAIN_PLATE` 的路径

现阶段 H/GL 主材分组只保留旧的显式中文名口径：

- `上翼缘` -> `TOP_FLANGE`
- `腹板` -> `WEB`
- `下翼缘` -> `BOTTOM_FLANGE`

## 后续正确方向

下一版 H/GL 异形主板识别应重新设计为切面证据优先：

- 输入优先使用 `metadata.hBeamSectionEvidence.stationFrames[].partSlices`。
- 依据 station 连续覆盖、有效 `sectionLoops/segments`、局部 H/GL frame 边界参与度、同一零件在多 station 的拓扑稳定性来确认主板。
- `PartRoles`、中文 `name` 和关系仅作为辅助解释或低置信 fallback，不作为主板升级主判据。
- `T2-3GL-55` 仅作为回归 smoke，不能围绕构件号或零件号写死。