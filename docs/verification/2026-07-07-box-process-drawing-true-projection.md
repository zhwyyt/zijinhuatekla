# BOX 工序图真实投影验证记录

## Scope

- Design: `docs/design/2026-07-07-box-process-drawing-true-projection.md`
- Renderer: `src/zijinhua_tekla/reports/box_progressive_dxf.py`
- Report payload: `src/zijinhua_tekla/reports/offline.py`
- Output directory: `outputs/box-progressive-drawing-selected-20260706`

## Root Cause

真实 cache `cache/20260706_165011/members/member_T3-3GZ-6.json` 中零件有 `SolidEdges`，但报告层 `_drawing_part_snapshots()` 原先只输出零件号、规格、station、face、bolt/weld，导致 DXF 无法消费真实几何，只能画 station/lane 矩形。

另一个真实 smoke 暴露点：几何不在 `result.assembly.parts`，而在 `result.member.Parts`。本次已将 member 几何按 `partId/PartId` 合并进 drawing snapshot。

## RED Tests

### Missing projection payload

Command:

```powershell
python -m unittest tests.test_reports_offline
```

Expected failure before fix:

```text
KeyError: 'projectionEdges'
```

### Renderer behavior

Command:

```powershell
python -m unittest tests.test_box_progressive_dxf
```

Expected failures before fix:

```text
STEP 1 BASE_MAIN_WALL not found
R500 not found
BEND 8° not found
```

## GREEN Tests

Commands:

```powershell
python -m unittest tests.test_reports_offline
python -m unittest tests.test_box_progressive_dxf
python -m unittest discover -s tests
```

Results:

```text
tests.test_reports_offline: Ran 1 test ... OK
tests.test_box_progressive_dxf: Ran 7 tests ... OK
discover: Ran 121 tests ... OK
```

Note: full discovery still emits existing `openpyxl` `datetime.utcnow()` deprecation warnings.

## Smoke

Command:

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260706_165011 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-3GZ-6 --out outputs\box-progressive-drawing-selected-20260706
```

Generated:

- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.json`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf`
- `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps-preview-first-row-true-projection.png`

Readback summary:

```text
steps 29
parts 95
parts_with_projectionEdges 95
projection_edges_total 3349
parts_with_projectionArcs 0
entities 66564
sheets 29
true_projection_labels 29
part_diagonal_lines 9336
arcs 0
bbox 0.0 -4032.0 1853.0 420.0
```

## Result

当前 DXF 不再是单张阶段图，也不再是 station/lane 简化图。它默认输出 29 张阶段页，并且每页主视优先使用真实 `projectionEdges`。这版可以作为 BOX 柱工序图真实投影原型继续审查。

## Remaining Risk

- 自动尺寸/PartMark 避让仍是简化实现，复杂阶段可能需要 Tekla Drawing API 或更强 CAD 标注布局器。
- 当前 projection 使用全局 `X/Z` 主视，尚未自动判断最佳视向。
- 当前真实样例没有显式 `projectionArcs`，弧形半径能力仅通过单元测试和数据契约验证。

## CAD Openability Fix

用户反馈生成的 DXF 在 CAD 中提示无效。复核确认旧 writer 虽然声明 `AC1021/R2007`，但只手写了 `HEADER/ENTITIES`，实体是近似 R12 的简化结构，没有完整 `TABLES/BLOCKS` 和 `AcDbEntity/AcDbLine/AcDbText` subclass 标记；`ezdxf.audit()` 能读，不代表严格 CAD 能打开。

修复：

- `_DxfWriter` 改为使用 `ezdxf.new("R2007", setup=True)` 正规写出。
- 项目依赖新增 `ezdxf`。
- 测试新增 `TABLES/BLOCKS/AcDbLine/AcDbText` 结构断言。

重新生成 `outputs\box-progressive-drawing-selected-20260706\T3-3GZ-6-box-assembly-drawing-steps.dxf` 后读回：

```text
SECTION 9
TABLES 3
BLOCKS 1
ENTITIES 1
AcDbEntity 66577
AcDbLine 63105
AcDbText 6748
version AC1021
errors 0
fixes 0
entities 66564
sheets 29
true_projection 29
```

最新测试：

```text
python -m unittest tests.test_box_progressive_dxf tests.test_reports_offline
Ran 8 tests ... OK

python -m unittest discover -s tests
Ran 121 tests ... OK
```
