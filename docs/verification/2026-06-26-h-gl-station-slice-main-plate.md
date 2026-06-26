# H/GL station slice 主板识别验证

日期：2026-06-26

## 结论

已新增 H/GL/BEAM 主材分组的 station slice 优先口径。该口径只在导出数据包含 `assembly.metadata.hBeamSectionEvidence.stationFrames[].partSlices` 时启用；未提供该证据时，仍回退到旧的显式中文名 `上翼缘 / 腹板 / 下翼缘` 识别。

## 主判据

输入：`metadata.hBeamSectionEvidence.stationFrames[].partSlices`。

候选零件必须满足：

- 在多个 station 上存在有效 `sectionLoops`，或至少 4 条 `segments` 可形成截面切片。
- `roleHint` 只能作为 slice 几何的辅助类型说明，目前接受 `flange_candidate` / `web_candidate`，不读取 `member.Classification.PartRoles`。
- station 覆盖跨度 `>= 1800mm`。
- station 覆盖比例 `>= 0.50`。
- 覆盖比例的分母优先使用 `stationFrames` 的 station span，并与 `metadata.memberAxisEvidence.length` 取较大值，避免真实导出中 mainPart 局部轴长误作构件全长。

输出 evidence code：`H_GL_STATION_SLICE_MAIN_PLATE`。

## 防回归点

新增单元测试：

- `test_ignores_part_roles_when_h_gl_lacks_explicit_section_evidence`
- `test_classifies_h_gl_main_plates_from_station_slice_loops`

覆盖：

- `PartRoles` 即使给出 `web_candidate/flange_candidate/wall_candidate`，没有 station slice 证据时也不能自动升级为 H/GL 主板。
- 有效 station slice/loop 覆盖足够长时，`T2-3B-526`、`T2-3B-797`、`T2-3B-508` 可被识别为 H/GL 主板。
- 短局部件和尾段局部件不进入主板集合。

## 真实选择集 smoke

数据：`I:\zijinhuatekla\cache\20260626_134928`。
构件：`T2-3GL-55`。

结果：

| role | partPosition | station count | station span | coverage ratio | roleHint |
| --- | --- | ---: | ---: | ---: | --- |
| FLANGE | T2-3B-508 | 23 | 2826.589 | 0.568 | flange_candidate |
| FLANGE | T2-3B-526 | 39 | 4720.124 | 0.949 | flange_candidate |
| WEB | T2-3B-797 | 37 | 4640.124 | 0.933 | web_candidate |

本次 smoke 未输出 `T2-3B-502`、`T2-3B-540`、`T2-3B-51` 等局部干扰件。

## 验证命令

```powershell
python -m unittest tests.test_main_material_segments tests.test_box_main_material_segments tests.test_pipeline_offline tests.test_reports_offline
```

结果：

```text
Ran 22 tests in 0.698s
OK
```

备注：存在既有 `openpyxl datetime.utcnow()` DeprecationWarning，不影响断言。

## 局限

当前版本是 H/GL station slice 主板识别的第一版，先解决“不能靠 PartRoles/关系推主板”的问题。它尚未进一步判断局部 H 截面边界参与度、上下翼缘相对位置、腹板中心线稳定性；后续若要细分上翼缘/下翼缘/腹板语义，应继续增强 `hBeamSectionEvidence` 的 frame/topology 字段，而不是回退到名称或零件号规则。