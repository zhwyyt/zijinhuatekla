# 2026-09-29 休息平台花纹钢板

规则在 `docs/design/2026-09-27-member-structural-role-assertions.md`，实现为 `MR-LANDING-001`。

`cache/external-links-20260928` 里，`11-1LTHW-3` 这类装配有一块水平花纹钢板，材质 `Q235花纹板`，平面约 1390 mm × 1890 mm，厚度 6 mm。其余零件是 `L50*5`，质心都在板下 28 mm。同几何的装配有 12 根，平面短边 1290 mm 到 1890 mm，角钢 6 根到 25 根。

梯段里的折弯踏步、短边约 200 mm 的平踏步，以及短边约 600 mm、下面用扁钢加劲的平台板，不满足“一块花纹板加同一侧等边角钢”。

单元测试：`tests/test_member_structural_role.py` 的 `test_horizontal_checker_plate_on_one_side_angles_is_landing`。普通钢板、短边 600 mm、角钢分居两侧、混有加劲板都不命中。构件编号不进入证据。
