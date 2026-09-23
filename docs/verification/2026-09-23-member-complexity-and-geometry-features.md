# 2026-09-23 构件复杂度与几何零件特征验证

## 数据

- Tekla 当前选择集：289 装配。
- dump：`cache/20260922_173818`
- exporter：`xingcai-runner-body-bracket-0.3.3-solid-cut-proof`

## 输出

- 零件特征：`outputs/selection-main-plus-features-20260922/recognition-main-plus-features.xlsx`
- 构件复杂度：`outputs/member-complexity-20260922/member-complexity.xlsx`

## 命令

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python outputs/selection-main-plus-features-20260922/run_batch.py
python outputs/member-complexity-20260922/run_batch.py
```

## 结果

- 单元测试：`218 tests OK`。
- 零件特征：4044 行，失败 0。
- 构件复杂度：289 行，失败 0。
- 零件特征汇总：剖口 467、倒角 1085、割孔 353、切割 1025、洞口 308、螺栓孔 1258、焊接垫板 141。
- 构件类型分布：H 2134、BOX 1709、一字板 100、角钢 50、异形 51。
- 构件形态分布：变截面 121、同截面 132、折弯 8、多个折弯 28。
- 牛腿：合计 124；无 228、同一楼层高度 47、多楼层高度 14；方向为垂直 41、斜 15、混合 5。
- `HXZ` 抽样：13 个构件实例均输出主材类型“一字板”。

## 边界

- 牛腿方向使用主轴和牛腿主件 `axisX` 夹角，当前按 70°–110° 判垂直，其余判斜。
- 折弯/多个折弯当前由 `PolyBeam`、折叠标签和截面变化组合判定，尚无 Tekla 原生折弯对象直证。
- 未做人工作业级全量复核；输出可作为复核入口，不作为最终制造确认单。
