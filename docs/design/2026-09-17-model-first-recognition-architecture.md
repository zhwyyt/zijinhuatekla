# 模型优先识别架构

日期：2026-09-17  
范围：识别主链（零件特征 / 主材 / 主材形状 / 牛腿数量 → 识别 Excel）  
不在范围：自动详图、零件图、BOX 工序 DXF（冻结）

本文锁定四件事：主路径必须是模型出结果；几何库怎么选；模块边界现在就定；近期交付按 P0 出识别 Excel。

## 1. 结论

1. **主路径**：Tekla 模型 dump → 规范化构件文档 → 特征/关系/分类 → **识别 Excel**。所有特征、关系、标签只能来自模型。
2. **校对路径**：识别 Excel + 工厂真实清单 → 对齐 + 差异报告。这条路径 **禁止** 回写分类器，只做程序自动校对，减少人工核对。
3. **几何库**：P0/P1 **只用 Shapely 做平面拓扑**；3D 用本仓库薄内核（向量/坐标系/公差/投影）。**不引入** OpenCASCADE / pythonocc / CadQuery / trimesh / Open3D。C# 导出器继续用 Tekla Solid API 抽事实，不在 C# 侧引入几何库。
4. **导出器**：当前 `xingcaisuanfa` bundle（`tekla-body-bracket-export.v2-enhanced`）**够 P0 出识别 Excel**。不够的是字段完整性和实体粒度，不是缺一个通用 CAD 内核。缺口按 Feature Snapshot 补，不靠分类器硬凑。
5. **近期交付**：在现有 cache 上把流水线从「Excel 行驱动预测」翻成「模型零件驱动发射」，输出工厂列口径的识别 Excel；真实清单只走 `compare`。图纸代码从默认命令断开。

## 2. 两条流水线（硬约束）

当前 `cli analyze` → `run_offline_analysis` 是反的：先读工厂 Excel 行，再按行去 bundle 里找件并预测。分类器 `classify_part(row, summary)` 吃的是清单字段（规格、零件名称、工序、形状分类）。这会把工厂口径泄漏进识别，无法证明「结果来自模型」。

```
主路径（必须可独立跑）
  Tekla 模型
    → C# BodyBracket dump（事实，无业务标签）
    → Adapter → NormalizedMemberDocument
    → Features / Spatial / Classifiers
    → RecognitionWorkbook（识别 Excel + JSON sidecar）

校对路径（可选，永不进入分类器）
  RecognitionWorkbook + FactoryWorkbook
    → partPosition 精确对齐
    → DiffReport（MATCH / DIFF / DATA_MISSING / SCOPE_MISMATCH / REVIEW）
```

硬规则：

- 分类器、特征层、空间层 **不得 import** 工厂 Excel、不得读 `工序`/`形状分类`/`配送*` 作为输入。
- `partPosition` 精确匹配只用于校对路径。几何相似只进复核候选，不自动改号、不改识别结果。
- 拆板 `*-H-xxx[s/x/f]` 是制造口径映射，不是编号漂移；校对路径单独处理。
- 制造整板 vs Tekla 分段 → `MANUFACTURING_MODEL_SCOPE_MISMATCH`，不得当自动匹配成功。
- dump JSON 里不得写入 `predicted_*`。Raw ≠ derived。
- 不确定就输出 `UNKNOWN`，禁止用 `0` 或空串表示「没看出来」。

命令形态（实现时）：

- `emit-excel --root <dump> --member-id <id> --out <dir>`：主路径，不需要 `--truth-root`。
- `compare --recognition <xlsx> --truth-root <dir> --member-id <id>`：校对路径。
- 现有 `analyze` 保留为兼容壳，内部改为 emit + 可选 compare；默认不再画 DXF。

## 3. 几何库决策

### 3.1 现状（已核对代码）

| 位置 | 实际能力 | 用途 |
| --- | --- | --- |
| C# `TeklaSectionClassifier/Geometry.cs` | 只有 `Vector3D/Point/Line/BBox/CoordinateSystem` 字段，**没有**距离、变换、求交 | DTO，不是几何库 |
| C# dump | Tekla Solid 抽轮廓、孔、焊缝、Contact/Weld/Bolt、station loop、主轴、板坐标系 | Phase A RawDump |
| Python Shapely | `polygonize` / `unary_union` / point-in-polygon | BOX 截面闭合、内腔、内外关系 |
| Python ezdxf | 写 DXF | **仅图纸，冻结，识别主链禁用** |
| 分类器内散落的投影/station | 读 dump 的 `sectionProjectionEvidence` / `axisStation*` | 3D→2D 已在导出器做完 |

Python 识别主链 **已经在用几何库**，只是用在该用的地方：二维截面拓扑。原先「没用几何库」的观感来自 C# 侧只有手写向量结构、业务判断大量走 OBB/计数/名称启发式。

### 3.2 P0/P1 真正需要的几何运算

需要：

- 平面：轮廓成环、并集、内腔、点在多边形内、退化 loop 诊断 → **Shapely/GEOS**。
- 3D 薄层：点积、叉积、坐标系、沿主轴 station、把 3D 点投到板面 UV、公差比较 → **本仓库 `geom` 内核**，约几十个函数。
- 图：Weld/Contact/Bolt 邻接、簇、沿面 chain → 标准图，不是 CAD 内核。

不需要（P0/P1 不引入）：

- B-rep 布尔、实体求交、体积腔体网格 → OpenCASCADE / pythonocc / CadQuery。
- 三角网格碰撞/修复 → trimesh / Open3D。
- 在 Python 里重做 Tekla Solid 剖切。station loop 已由 C# 从 `teklaSolidFaceSectionSegments.v2` 导出。

### 3.3 选定栈

```
C# dump     : Tekla Open API 抽事实（Solid faces/loops/holes/welds/contacts）
Python geom : zijinhua_tekla.geom（Vec3, Frame, Tol, project_to_plane, station）
Python 2D   : shapely >= 2（仅平面拓扑，禁止从分类器直接 new Polygon 散落）
Python 图   : 标准库 / 现有 relationship 边
图纸        : ezdxf 冻结，识别 CLI 不依赖
```

Shapely 必须藏在 `geom.planar` 后面，分类器只问「这个投影点相对截面 loop 是 inside / cavity / outside / mixed / insufficient」。这样以后若替换 GEOS 实现，分类器不用动。

### 3.4 何时才允许升级几何库

只有同时满足才开题评估 OCC/trimesh，且要单独设计文档：

- 已有 Feature Snapshot 证明缺 **实体布尔或真 3D 腔体体积**，而不是缺导出字段。
- 用 Shapely + station loop 无法表达，且有失败案例 + 期望标签。
- 不把 OCC 当「先引进来以后有用」的依赖。

默认假设：后续组立顺序、邻接构件、牛腿单元，优先补 **导出字段和关系图**，不是补 CAD 内核。

## 4. 导出器是否够用

对象：`I:\xingcaisuanfa` `BodyBracketBundleExporter`，schema `tekla-body-bracket-export.v2-enhanced`。不重写 AutoDwg.Extract，不把 fable 11.2 的 C# Extractor 迁进来。Dump 向 11.2 Raw* **增量靠拢**。

### 4.1 P0 已够用的事实

对 cache `20260706_165011` 一类 bundle，零件上已有：

- 身份：`partId` / `partPosition` / `name` / `profileString` / `material` / `runtimeType`
- 板几何：`centroid` / `obbDims` / `boundingBox` / `thickness` / 板法向与长宽向 / `partCoordinateSystem`
- 轮廓：`contourPoints` / `contourSegments`（含 Line/Arc 标记）/ 凹点计数 / `hasArcContour`
- 孔：`boltHoles[]`（xyz + diameter + 螺栓组两端件）
- 切割计数：`booleanCutCount`（**详情不完整**，见缺口）
- 焊缝：`weldDetails[]`（主从件、类型、尺寸、车间/现场）
- 关系图：assembly `relationships[]`（Contact / Weld / Bolt）
- 构件证据：`memberAxisEvidence`、`boxSectionEvidence.stationLoops`、`hBeamSectionEvidence.stationFrames`
- 主材证据：`mainMaterialEvidence`（station 起止、`bodyFaceId`、邻接 gap、截面投影）

这些足够做：零件级加工尺寸/孔/切/焊特征、BOX/H 主材分段、截面形状 BOX/H/CROSS、车间形状（方块/异形/异形主材）的第一版、附属件簇种子。

### 4.2 已知缺口（按层补，不按构件号写规则）

| 缺口 | 归因 | 处理 |
| --- | --- | --- |
| `booleanCutDetails` 只覆盖 `BOOLEAN_CUT` | 部分已补 | dump 已出 `edgeBevels`（EdgeChamfer / 倾斜 Fitting·CutPlane / 板边楔体 BOOLEAN_CUT）；轮廓倒角仍走 `contourSegments`；型材另出 `endChamferCount` |
| 剖口壁厚只解析 H/PL | 评分/特征 | 型材用规格末位/腹翼缘厚（2–80mm），不用截面高宽当板厚；板边楔体最短边须为 O(t) |
| Beam 建模的 PL 无 `contourPoints` | 部分已补 | 导出器对非折弯 Beam 板从局部 AABB 合成板面四角；识别层无轮廓时用去厚 OBB 重建矩形。角部 BOOLEAN_CUT 仍是否定方块的倒角 |
| 邻板 AABB 的 BOOLEAN_CUT 误当剖口/洞口 | 评分/特征 | 剖口仍须 O(t) 楔体；剩余切割按与板 AABB 的贯穿/内含/贴边分成洞口、倒角、外来切割。外来切割不进 holeLike |
| 牛腿是「可数支承单元」不是板数量 | 新类型 / 实体粒度 | P0 先出簇 + `corbel_unit_count=UNKNOWN` 或低置信计数；P1 补根接触面/挑出主材的外伸证据 |
| 邻接构件、Component、螺栓组装配级 | 特征缺失 | P1 导出；P0 识别 Excel 不填邻接列 |
| 板内真实内孔环 vs 螺栓孔 | 部分已补 | P0：螺栓组 + 板内贯穿 BOOLEAN_CUT 记洞口；轮廓倒角/缺口走平面环。真内环轮廓仍待导出 |
| PolyBeam 展开、无法证明的弧 | 特征缺失 | 与零件图同一纪律：不能证明则 UNKNOWN/拒绝，禁止静默折线化 |
| C# 分类器写进 member JSON 的 `PartRoles` | Raw/derived 混放 | Adapter 可读作候选证据，**不得**当最终标签 |

原则：缺字段先改 dump / Feature Snapshot，再改分类器。禁止用单个构件号、零件号、项目名写死。

## 5. 现有算法哪些留下、哪些停用

| 算法 | 裁决 | 原因 |
| --- | --- | --- |
| BOX station loop + Shapely 内外/内腔 | **主路径保留** | 用的是模型截面事实，适合主材形状和内外区 |
| BOX 主壁板：闭合外轮廓种子 + 同面 chain + station 连续 + Weld/Contact | **主路径保留** | 工程证据链，不是厚度硬阈值 |
| H/GL station frame 翼缘/腹板 + 收尾相连 | **主路径保留** | 已从 name 判定迁出 |
| 组合截面 CROSS/BOX/H 沿轴分区 | **主路径保留** | 主材形状按 station，不是整根一根标签 |
| Contact/Weld 图 → 附属件簇 | **种子保留** | 可做牛腿候选，不能直接当牛腿个数 |
| `partPosition` 精确匹配 | **只留在 compare** | 识别不依赖清单编号 |
| `part_roles.infer_role` 吃 Excel 名称系列（H/PX/DB/PR）和「隔板」等 Tekla 名 | **主路径停用** | 清单方言 + 名称启发式；改为几何/关系证据，名称只作弱证据 |
| 超长宽板 → 箱型柱主壁板 | **降为弱特征** | 主壁板以截面/面归属为准 |
| OBB 尺寸当形状分类 | **辅助** | 车间形状以轮廓顶点数、凹点、弧、孔、切割为准 |
| 几何相似补号 | **永不自动命中** | 只进 compare 复核候选 |
| BOX 工序 DXF / 标注避让 / 零件图 snapshot | **冻结** | 与识别主链解耦 |

## 6. 目标模块与依赖方向

在现有 `architecture.py` 八层上 **加内核、拆出口、冻结图纸**，不推倒重来。目录可分批迁，但 **import 方向现在就执行**。

```
xingcaisuanfa dump JSON
        │
        ▼
adapters/          只读 dump / 可选工厂清单；产出 Normalized* ，零业务标签
        │
        ▼
geom/              Vec3/Frame/Tol + planar(shapely 封装)；无业务标签
        │
        ▼
features/          PartFeatureSnapshot / MemberFeatureSnapshot（事实）
        │
        ▼
spatial/           关系图、station 拓扑、簇、内外区（证据，不是最终角色）
        │
        ▼
classifiers/       member_body / main_material / part_role / shape / corbel
                   只读 features+spatial+vocab；输出 label, confidence, evidence
        │
        ├────────► reports/emit     识别 Excel / JSON sidecar     ★主交付
        │
        └────────► quality/compare  仅当提供工厂清单               ★校对
                        │
                        ▼
                   cases/           失败归因、期望标签、回归
```

冻结（默认 CLI 不调用，禁止新识别代码 import）：

- `reports/box_progressive_dxf.py`
- `reports/annotation_layout.py`
- `classifiers/box_assembly_drawing_steps.py`
- 零件图 worktree / `--export-part-drawing-snapshots`

允许的依赖（单向，测试锁定）：

```
adapters  → 无业务包
geom      → 无业务包
features  → adapters 契约, geom
spatial   → features, geom
classifiers → features, spatial, geom, vocab
reports/emit → classifiers 结果 + 契约
quality/compare → emit 结果 + 工厂清单适配；不得被 classifiers import
cases     → 分类结果与人工标签
pipeline  → 编排以上各层
cli       → pipeline / reports 薄壳
```

禁止：

- `classifiers` → `adapters.excel_truth` / `quality` / `reports`
- `features` → `classifiers`
- 识别代码 → `ezdxf` / drawing 模块
- 新规则里出现具体 `T3-*` / 零件号常量（回归样例放 `cases/` 和 `tests/` fixture）

`architecture.py` 的 `quality` 层职责改写为：**校对与数据质量，不参与识别打标**。识别阶段若 dump 缺字段，走 `INSUFFICIENT_EVIDENCE` / `UNKNOWN`，不要在识别路径上做 Excel 缺件判断。

## 7. 规范化输入（唯一合同）

Adapter 把 bundle + member JSON 收成一份 `NormalizedMemberDocument`，分类器只认它。字段级 schema 实现时落在 `contracts/`，这里锁语义。

```
NormalizedMemberDocument
  member_id, assembly_id
  axis: origin, direction, length, source
  stations[]: station, loops[] (2D in UV), diagnostics
  parts[]: NormalizedPart
  relationships[]: {a, b, edge_type, strength, meta}
  dump_diagnostics[]

NormalizedPart
  part_id, part_position, name, profile, material, runtime_type
  plate_frame (origin, n, long, width) | none
  obb, thickness, contour (segments, vertex_count, concave, has_arc)
  holes[] (xyz, diameter, mate_part_ids)
  cuts: count + details[]（可空）
  welds[]
  main_material_evidence（导出器事实，不是最终主材标签）
```

词汇表（实现时 `vocab.yaml`，分类器不得发明表外标签）：

- 构件主体：`BOX | H_I | T | CROSS | PLATE_BODY | UNKNOWN`（可按 station 分段，允许一根构件多段不同）
- 主材：`MAIN_WALL | FLANGE | WEB | TRANSITION | UNKNOWN`
- 车间形状：`方块 | 异形 | 异形主材 | UNKNOWN`（切割外形，不是 BOX/H）
- 零件角色：沿用 `contracts/role.py` 的 `PartRole`，缺证据为 `UNKNOWN`
- 牛腿：`CorbelUnit`（可数单元）≠ 牛腿板零件。P0 可只输出 `corbel_unit_count` + 成员 part_ids + 置信度

Excel 列（识别书对齐工厂清单，便于 compare）：

`构件名称, 零件名称, 规格, 长度, 数量, 材质, 工序, 形状分类`

另附 sidecar JSON：主材形状（按 station）、牛腿单元、证据码、置信度。Excel 放不下关系图，不要把证据塞进一个单元格凑合。

## 8. 近期 P0 交付（按本理解执行）

目标：同一份 T3 cache，**不打开 Tekla**，从模型生成识别 Excel；有真实清单时程序出差异，而不是人眼对。

顺序：

1. **冻结图纸**：`analyze` 默认不再写 DXF / drawing steps；需要时显式子命令。
2. **合同**：补 `NormalizedPart` / `NormalizedMemberDocument`；Adapter 从现有 bundle 填充，缺的字段显式空，不编造。
3. **分类入口翻转**：`classify_part(NormalizedPart, spatial, member_body)`，删除对工厂 `row` 的依赖。名称系列只作弱证据。
4. **`emit-excel`**：按模型零件发射工厂列；规格/长度从 profile + 几何取，不从清单抄。
5. **`compare`**：`partPosition` 精确对齐；输出 MATCH/DIFF/MISSING/SCOPE_MISMATCH；几何候选仅复核。
6. **回归**：现有 BOX/H 主材与内外测试保持绿；新增「无 truth 也能 emit」测试；用 T3-5GKZ-10 的工厂清单做 compare 基线，差异归因而不是改识别去贴清单。
7. **导出器**：P0 不改 C#，除非 emit 被缺字段挡住（当前预计挡不住主材/形状/孔焊；挡住的是牛腿精确计数，P0 允许 UNKNOWN）。

P0 验收：

- `emit-excel` 不传 `--truth-root` 能跑完，产出 xlsx + sidecar。
- 分类器测试里没有 `load_truth_rows`。
- compare 与 emit 可分开跑；关掉 compare 不影响识别数字。
- 不新增 OCC/trimesh/ezdxf 识别依赖。
- 主材形状来自 station 分类，不是零件 `形状分类` 列反过来填构件。

P1（P0 稳定后，不在本次交付）：

- 牛腿可数单元（根接触 + 外伸 + 同向簇）
- 导出器补全 `booleanCutDetails`、内孔环、邻接装配
- `geom.planar` 收口所有 Shapely 调用
- 工序从焊缝/孔/切割证据出，而不是抄清单「工序」列

## 9. 明确不做

- 不把自动详图、零件图、Tekla 2017 套图重新接进默认识别命令。
- 不把 fable AutoDwg C# Extractor 整仓迁入。
- 不靠「尽快出一张能看的 Excel」把工厂清单字段喂回分类器。
- 不围绕单个构件号补 if/else。
- 不把几何相似、长度相近当成自动对上。
- 不在识别结果里静默把 UNKNOWN 写成 0。

## 10. 与旧文档的关系

- `docs/design/2026-06-17-agent-architecture-skeleton.md`：八层仍有效；**数据流方向按本文翻转**；quality 改为校对层。
- 主材分段、BOX 内外、H 侧向、composite station 的设计仍有效，作为 classifiers 实现，不作为 Excel 对齐逻辑。
- 图纸类 `2026-07-*` 设计全部冻结，识别里程碑不引用它们的验收项。
