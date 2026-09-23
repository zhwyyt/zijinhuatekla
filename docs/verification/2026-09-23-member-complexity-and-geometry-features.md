# 2026-09-23 构件复杂度与几何零件特征验证

## 数据

- Tekla 当前选择集：289 装配。
- dump：`cache/20260922_173818`
- exporter：`xingcai-runner-body-bracket-0.3.3-solid-cut-proof`

## 输出

- 零件特征（最终版）：`outputs/selection-main-plus-features-20260922/recognition-main-plus-features-geometry-v3.xlsx`
- 构件复杂度（最终版）：`outputs/member-complexity-20260922/member-complexity-geometry-v3.xlsx`

## 命令

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python outputs/selection-main-plus-features-20260922/run_batch.py
python outputs/member-complexity-20260922/run_batch.py
```

## 结果

- 单元测试：`225 tests OK`。
- 零件特征：4044 行，失败 0。
- 构件复杂度：289 行，失败 0。
- 零件特征汇总：剖口 467、倒角 1085、割孔 353、切割 1025、洞口 308、螺栓孔 1258、焊接垫板 141。
- 构件复杂度主材分布：H钢 203、BOX 33、一字板 3、角钢 50；UNKNOWN 0。
- 构件形态分布：变截面 121、同截面 132、折弯 8、多个折弯 28。
- 牛腿：合计 124；无 228、同一楼层高度 47、多楼层高度 14；方向为垂直 41、斜 15、混合 5。
- `HXZ` 抽样：13 个构件实例中 8 个主件为单板输出一字板，5 个主件为 `BH/H` 输出 H钢；零件表只把一字板的 `mainPartId` 标为主材，不再把附属板标记为 `BOX主壁板`。
- `GKZ` 修正：16 个构件实例全部输出 BOX，证据为 `section.box_signature:4/5`；无 UNKNOWN。旧逻辑曾因 H 板组签名或判定顺序抢判。

## 回归修正

- 失败案例：`T3-4HXZ-1/5/8/9/10` 主件为 `BH/H`，旧逻辑按 `HXZ` 编号族强制输出一字板。
- 期望口径：编号不参与判定；`BH/H` 输出 H钢，`PL/FLAT/plateLike` 且无组合截面签名才输出一字板。
- 证据：`section.major_plates>=3`、`section.web_and_two_flanges`、`section.closed_loop`、`profile.PL`、`main_part.plate_like`。
- 回归测试：`tests/test_member_complexity.py` 覆盖直 H 截面、无组合签名单板、单板组成 H、BOX 封闭核心、十字核心、BOX/H 冲突和直截面主板不被当单板。
- 追加失败案例：`T3-5GKZ-4/10` 等 BOX 柱端部样本有附属板放大计数，不能用宽泛十字签名；核心正交拓扑必须守恒，期望统一输出 BOX。

## 边界

- 牛腿方向使用主轴和牛腿主件 `axisX` 夹角，当前按 70°–110° 判垂直，其余判斜。
- 折弯/多个折弯当前由 `PolyBeam`、折叠标签和截面变化组合判定，尚无 Tekla 原生折弯对象直证。
- 未做人工作业级全量复核；输出可作为复核入口，不作为最终制造确认单。
