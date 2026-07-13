# 零件图 CAD 原生尺寸样式对齐设计

## 文档状态

- 日期：2026-07-13
- 状态：已确认设计
- 实现分支：`codex/offline-part-drawing-engine`
- 样式基准：项目根目录 `零件标注.dwg`
- 范围：已放置尺寸的 CAD/PDF 表达样式

## 背景

当前零件图已能生成外轮廓、孔和总尺寸，但尺寸 renderer 把每条尺寸扁平化为一条 `LINE` 和一条 `TEXT`。结果没有尺寸界线、端头、文字断开、方向控制和半径/直径引线，DXF 中也不存在可编辑的 CAD `DIMENSION` 对象，因此图面与 `零件标注.dwg` 样板差异明显。

样板经只读副本转换和 DXF 检查后确认：DWG 中保留了明确的尺寸样式和文字样式；现有 Tekla 尺寸实体则已经拆为 `LINE/TEXT/POINT/HATCH` 图元，不能作为原生尺寸对象直接复制。正确做法是以样板参数为唯一标准，在离线引擎中生成新的 CAD 原生尺寸对象，而不是继续手绘或逐项让用户选择视觉参数。

本设计只改变“已经成功放置的尺寸如何表达”。当前真实 smoke 中 17 个孔相关标注意图未放置属于布局/尺寸覆盖问题，必须继续保留为 `REVIEW_REQUIRED`，不得通过样式变更掩盖。

## 目标

1. `PartDrawingDocument` 保留尺寸语义，不在布局阶段提前退化为线和文字。
2. DXF 使用原生线性、半径和直径 `DIMENSION` 实体，并采用样板定义的唯一尺寸样式。
3. PDF 从同一尺寸语义和同一版本化样式生成等价图元。
4. 输出尺寸值保持模型真实毫米值，不受图面缩放影响。
5. 不要求运行时启动 AutoCAD，也不把本机 DWG 文件作为部署依赖。

## 非目标

- 本阶段不修改图框、标题栏、零件表、备注区或整体图层配色。
- 本阶段不增加新的孔组定位规则，也不解决未放置尺寸容量问题。
- 本阶段不改零件几何、特征识别、比例选择或页面分区。
- 本阶段不通过 AutoCAD COM 或 `accoreconsole` 批量生成正式图纸。
- 本阶段不围绕特定零件号或项目名增加样式分支。

## 方案选择

### 采用：版本化样板样式 + CAD 原生尺寸

从 `零件标注.dwg` 一次性提取经过人工确认的参数，固化为版本化 `CadDimensionStyle`。DXF renderer 在文档中创建文字样式、端头块和 DIMSTYLE，并按尺寸语义创建原生 `DIMENSION`；PDF renderer 使用同一 style DTO 展开为矢量图元。

优点：DXF 尺寸可编辑、样式来源明确、离线和测试环境不依赖 AutoCAD、DXF/PDF 仍共享一份图纸真相。

### 不采用：运行时自动化 AutoCAD

每次调用 AutoCAD/`accoreconsole` 打开 DWG 模板并出图，能直接使用 CAD 环境，但会引入安装版本、许可证、文件锁、权限、语言包和批处理稳定性依赖，不符合当前离线引擎边界。

### 淘汰：继续手绘尺寸图元

手绘 `LINE + TEXT` 无法提供原生尺寸行为，且每增加一种标注都要重复实现端头、断线、旋转和避让，正是当前样式差异的根因。

## 样板参数

样板检查得到以下基础参数，作为 `partCadDimensionStyle.v1` 的来源证据：

| 参数 | 值 | 用途 |
| --- | ---: | --- |
| 文字字体 | Arial | CAD 尺寸数字 |
| 文字宽度系数 | 0.65 | 对齐样板压窄文字 |
| 纸面文字高度 | 2.5 mm | 线性、半径、直径尺寸 |
| 线性尺寸端头 | 45 度斜杠 | 对齐样板线性尺寸 |
| 引线端头 | 实心箭头 | 半径、直径及引出标注 |
| 端头尺寸 | 2.0 mm | 纸面尺寸 |
| 尺寸界线起点偏移 | 2.5 mm | 避免紧贴轮廓 |
| 尺寸界线超出量 | 2.0 mm | 超出尺寸线长度 |
| 文字与尺寸线间隙 | 1.0 mm | 文字断开和留白 |
| 小数位 | 0 | 默认整数毫米 |
| 末尾零抑制 | 开启 | 对齐样板整数表达 |
| 文字位置 | 尺寸线上方 | 水平/垂直尺寸随尺寸线方向 |

样板中的 `dimscale=20/50` 来自原图模型空间打印比例，不能原样硬编码。当前零件图在 A3 页面坐标中放置缩放后的几何，因此 style 的纸面尺寸保持不变，测量换算由每张图的 `layout.scale` 派生。

## 数据模型

新增格式无关的已放置尺寸 DTO，替代布局结果中的“尺寸线 + 尺寸文字”二元组：

```text
PlacedDimension
- dimension_id
- kind: LINEAR_HORIZONTAL | LINEAR_VERTICAL | RADIUS | DIAMETER | LEADER
- source_points
- dimension_line_point
- measured_value_mm
- display_text
- text_rotation
- style_id
- evidence_codes
```

`PartDrawingLayout` 输出：

- `placed_dimensions`：已成功布局的尺寸。
- `annotation_lines` / `annotation_texts`：只保留非尺寸说明和审核提示。
- `unplaced_intents`：保持现有质量门语义。

`PartDrawingDocument` 持有 `placed_dimensions` 和 `dimension_style`。DXF/PDF renderer 不得自行重新选择尺寸、改变尺寸值或吞掉未放置项。

## DXF 渲染

1. 创建版本化 CAD 文字样式，字体为 Arial、宽度系数为 `0.65`。
2. 创建 45 度斜杠端头块和 `partCadDimensionStyle.v1` DIMSTYLE。
3. 对水平/垂直尺寸调用 ezdxf 原生线性尺寸 API。
4. 对半径/直径尺寸调用对应原生尺寸 API，使用实心箭头端头。
5. 因模型轮廓已映射到纸面坐标，按 `1 / document.scale` 设置测量换算；显示值必须与 `measured_value_mm` 一致。
6. 仅当格式文本包含直径/半径符号或业务前后缀、无法由 DIMSTYLE 数值格式直接表达时，才允许使用显式尺寸文字覆盖；不得以覆盖文字修正错误测量，测试必须同时核对测量换算和显示值。
7. 调用 `dimension.render()` 生成兼容严格 CAD 的块内容，并继续执行 `ezdxf.audit()`。

原生尺寸统一位于现有 `DIMENSION` 层。本阶段不复制样板的整套图层颜色，以保持用户确认的“只对齐尺寸标注”范围。

## PDF 渲染

PDF 不启动 AutoCAD。renderer 从 `PlacedDimension + CadDimensionStyle` 展开：

- 尺寸线及断开文字位。
- 尺寸界线及起点偏移、超出量。
- 线性尺寸 45 度斜杠端头。
- 半径/直径实心箭头和引线。
- 按方向旋转并压窄的尺寸文字。

PDF 与 DXF 的尺寸文字集合、数量、端点和纸面样式参数必须一致。字体文件不可用时沿用现有明确失败策略，不静默替换。

## 错误处理

- 缺少合法尺寸源点或尺寸线位置：该意图进入 `unplaced_intents`，状态为 `REVIEW_REQUIRED`。
- 尺寸测量换算与模型值超出 `0.01 mm`：阻断该图渲染并返回 `RENDER_FAILED`。
- DIMSTYLE 或端头块创建失败：阻断 DXF 输出，不回退到手绘假尺寸。
- DXF audit 出错：保持现有原子输出策略，不留下部分正式文件。
- PDF 无法使用配置字体：保持现有明确错误，不输出乱码图。

## Acceptance Criteria

1. 矩形板的总长、总宽在 DXF 中是原生 `DIMENSION` 实体，不再只是独立 `LINE/TEXT`。
2. 线性尺寸具有样板式 45 度斜杠、尺寸界线、文字断开和方向正确的尺寸数字。
3. 半径和直径尺寸使用原生半径/直径对象及实心箭头引线。
4. DIMSTYLE 的字高、宽度系数、端头尺寸、界线偏移、超出量、文字间隙和精度与 `partCadDimensionStyle.v1` 一致。
5. 任一标准比例下，DXF 显示值和原生测量换算均与模型真实值一致，误差不超过 `0.01 mm`。
6. PDF 与 DXF 的已放置尺寸数量、文本和值一致，并呈现相同端头和间距规则。
7. 现有标题栏、页面分区、轮廓和图层配色不因本变更发生无关变化。
8. 未放置的孔相关尺寸继续出现在 manifest 和 `REVIEW_REQUIRED` 状态中。
9. DXF 通过 `ezdxf.audit()`，PDF 保持 A3 单页且非空。
10. 生产代码和测试不存在特定零件号、构件号或项目名的样式分支。

## Verification Plan

### 单元测试

- `dimension_optimizer`：总长、总宽、半径、直径 intent 转换为正确的 `PlacedDimension`，源点、尺寸线位置、测量值和文字方向正确。
- `CadDimensionStyle`：锁定样板参数和版本号，比例变化只影响测量换算，不改变纸面字高/端头大小。
- 密集尺寸：超过布局容量时仍进入 `unplaced_intents`，不因 renderer 升级改变质量状态。

### DXF 输出测试

- 用 `ezdxf` 读回，断言存在预期数量和类型的 `DIMENSION`。
- 核对 DIMSTYLE、文字样式、斜杠端头块及关键参数。
- 核对各标准比例下的测量值、显示文字和 `dimlfac`/等价换算。
- 执行 `audit()`，要求无错误。

### PDF 输出测试

- 读回 PDF，核对页数、尺寸文字集合和非空内容。
- 将 PDF 渲染为位图，检查尺寸端头、尺寸界线和文字区域存在有效像素。
- 对矩形板和带圆孔板生成固定 smoke 预览，人工与样板局部对照。

### 最小验证命令

```powershell
python -m unittest tests.test_part_drawing_layout tests.test_part_drawing_output
python -m unittest tests.test_part_drawing_pipeline
python -m unittest discover -s tests
```

真实 `T3-PX-317` smoke 继续使用当前快照重新生成 DXF/PDF/preview，并把 audit、实体统计、未放置尺寸数量和人工样式结论写入 `docs/verification/`。
