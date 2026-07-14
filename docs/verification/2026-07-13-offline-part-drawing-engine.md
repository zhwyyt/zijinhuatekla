# 平板零件离线出图引擎验证

## 验证范围

本轮实现 `partDrawingSnapshot.v1` 的离线消费端和独立 DXF/PDF 出图引擎，覆盖：

- 快照契约解析和数据校验。
- 平板三维轮廓到局部二维几何归一化。
- 同一 `partPosition` 的轮廓、厚度、孔槽和切割冲突质量门。
- 圆孔、孔组、槽、多边形切口、切角、缺口和圆弧特征识别。
- 总体、板厚、孔槽、切口和圆弧尺寸意图。
- A3 横向页面布局、碰撞/溢出复核状态。
- 同一 `PartDrawingDocument` 到 DXF、PDF 和 drawing JSON 的输出。
- `draw-parts` 批处理 CLI、单零件失败隔离和批次摘要。

本轮不包含 Tekla 导出器生产端、真实模型快照和生产放行。折弯板、型材和构件工序图也不在本轮范围内。

## 自动测试

### 零件图 focused tests

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m unittest tests.test_part_drawing_contracts tests.test_part_drawing_geometry tests.test_part_drawing_quality tests.test_part_drawing_features tests.test_part_drawing_dimensions tests.test_part_drawing_layout tests.test_part_drawing_output tests.test_part_drawing_pipeline
```

结果：`Ran 33 tests ... OK`。

### 完整回归

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m unittest discover -s tests
```

结果：`Ran 165 tests ... OK`。存在既有 openpyxl `datetime.utcnow()` DeprecationWarning，不影响断言。

## CLI Smoke

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m zijinhua_tekla.cli draw-parts --snapshot-root tests\fixtures\part_drawing --out outputs\part-drawing-fixture-smoke-20260713
```

结果：

```text
Part drawings: OK=1 REVIEW_REQUIRED=0 REJECTED=0
```

生成文件：

- `parts/P-1001/P-1001.dxf`
- `parts/P-1001/P-1001.pdf`
- `parts/P-1001/P-1001.drawing.json`
- `part-drawing-batch-summary.json`

## 产物读回

- DXF audit：`errors=0`、`fixes=0`。
- DXF 实体：`LINE=7`、`TEXT=9`。
- PDF：`2407 bytes`、`1 page`、`420.0 x 297.0 mm`。
- drawing JSON：`status=OK`、`part_position=P-1001`、`annotation_count=3`。
- 几何指纹：`5a1fdb486ee5aa7179087c4dca32ab854c776c74b84b2a030d87a9626eff2640`。

DXF、PDF 和 JSON 均由同一 `PartDrawingDocument` 生成。显式圆孔、槽和圆弧另有单元测试验证为 `CIRCLE`、两直线加两圆弧、原生 `ARC` 图元。

## 质量门证据

- 同编号厚度、孔位或制造指纹不一致：`PART_POSITION_CONFLICT / REJECTED`，只写冲突证据。
- 损坏 JSON：`SNAPSHOT_INVALID / REJECTED`，不阻断同批合法零件。
- 不可靠圆弧特征：`FEATURE_AMBIGUOUS / REVIEW_REQUIRED`。
- 密集标注放不下：保留未放置意图并返回 `REVIEW_REQUIRED`，不重叠输出。
- 非 ASCII PDF 未配置 CJK 字体：明确 `RENDER_FAILED`，不留下半套输出。

## 剩余工作

1. 在 Tekla 导出器实现 `partDrawingSnapshot.v1` 生产端。
2. 用真实模型平板件完成外轮廓、孔槽、切割和属性字段 smoke。
3. 根据真实失败案例补 exporter 字段或特征规则，不围绕零件号写特例。
4. 完成人工图面复核后，再评估生产放行所需公差、坡口和加工说明。
