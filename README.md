# Zijinhua Tekla

Tekla 深化模型的构件角色、构件复杂度与零件特征识别。2026-10-10 起以已人工验收的实验成果为正式基线，当前收尾分支为 `feat/recognition-mainline`。

## 正式识别入口

安装与验证：

```powershell
python -m pip install -e .
python -m unittest discover -s tests
```

桌面入口：

```powershell
python -m zijinhua_tekla.cli gui
```

GUI 模式1从已打开的 Tekla 模型导出当前选择集；模式2选择导出目录或 bundle，输入项目名称、工程区域后生成单个 Excel。批量命令与 GUI 共用同一报告函数：

```powershell
python -m zijinhua_tekla.cli export-excel --root <导出目录> --project-name <项目名称> --project-area <工程区域> --out outputs
```

输入目录包含 `tekla-body-bracket-export.bundle.json` 和 `members/member_<构件号>.json`。输出固定有三张主表：

| 表 | 用途 |
|---|---|
| 构件角色 | 柱、梁、支撑、埋件、楼梯、休息平台等结构职能，以及子类、轴线姿态、规则和证据 |
| 构件复杂度 | 主材截面/形态、轴线形状/折点、牛腿数量/方向/楼层及加工特征统计 |
| 零件特征 | 零件编号、加工尺寸、主材标记、剖口/倒角/切割/洞口/螺栓孔、工序及形状 |

有候选或失败时另带 `连接复核` / `识别失败` 辅助表。近邻不自动升级为焊缝或螺栓连接。零件特征中的既有“构件类型”列指主材截面类型，不替代构件角色。

## 主轴与数据边界

主轴使用已验收的 `AlignedSpanMemberAxis`，实现在 `I:\xingcaisuanfa`；bundle 的 `memberAxisEvidence.source` 和 member 的 `LongitudinalAxisSource` 应为 `assemblyParts.alignedSpanCentroid`。`Member.MainAxis` 是主段，`AxisSegments/GuidePolyline` 保留折线链。Python 不重新按最长零件推轴。

历史 cache 仍可用来诊断，报告和 GUI 会提示旧主轴/来源不一致；这些输出不能充当新主轴的验收结果。编号只用于身份和精准清单核对，不补造结构角色证据。

单构件兼容入口仍保留 `emit-excel`、`analyze`、`compare`；真实加工清单只作对照，不反馈修改模型识别标签。默认不生成图纸。

## 工作区与项目路标

- `src/zijinhua_tekla/`、`tests/`：正式识别代码及回归。
- `docs/design/`：当前设计与验收要求；`docs/verification/`：验证证据与历史记录。
- `cache/`、`outputs/` 及根目录 CAD/Excel：被忽略的本地业务现场，不是版本基线。
- 零件出图单独保留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，后续独立开发。

先读 [STATUS.md](STATUS.md)、[TASKLIST.md](TASKLIST.md) 和 [识别主线设计](docs/design/2026-10-10-recognition-mainline.md)。本地 `main` 仍在旧出图历史上，当前识别工作以收尾分支为准；本轮不直接重写或推送 main。
