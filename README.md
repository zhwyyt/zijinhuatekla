# Zijinhua Tekla

Tekla 深化模型的构件角色、构件复杂度与零件特征识别。2026-10-10 起以已人工验收的实验成果为正式基线，当前收尾分支为 `feat/recognition-mainline`。

## 正式识别入口

安装与验证：

```powershell
python -m pip install -e .
python -m unittest discover -s tests
```

Qt6 桌面入口（2026-10-12 用户确认验收通过）：

```powershell
python -m zijinhua_tekla.cli gui
```

单文件程序位于本地 `dist/ZijinhuaTekla/ZijinhuaTekla.exe`，无需单独安装 Python 或 Qt。模块1从已打开的 Tekla 2017 模型导出当前选择集，保存到所选目录下的独立数据集；模块2选择导出目录或 bundle，输入项目名称、工程区域及结果目录后生成 Excel。两模块均在后台运行，显示日志、进度与错误提示。操作前提和构建命令见 [桌面版使用说明](docs/desktop-user-guide.md)，验收记录见 [Qt6 交付验证](docs/verification/2026-10-12-qt6-desktop-acceptance.md)。

批量命令与 GUI 共用同一报告函数：

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

同号构件可以有多个装配实例；批量识别优先按装配 ID 读取 `members/batch_summary.json` 中的完整快照，不能把最后写入的同号 member 文件用于其它实例。旧数据没有完整快照且实例身份不一致时，进入 `识别失败`，不自动替代。单构件指定 `--assembly-id` 时使用同一装配身份校验。

主材优先消费新主轴下的局部截面证据：BOX 使用闭合空腔及核心壁板身份，H 使用不同站位重复的完整上翼缘、腹板、下翼缘切片，并关联主件。完整证据确认的短分段不受旧绝对长度或整轴占比门槛否决；真实截面冲突保留 UNKNOWN。证据不足的兼容路径仍保留原筛选条件，原生型钢主件不由附属板重新定义。验证范围及待人工确认的新结果见 [局部截面主材验证](docs/verification/2026-10-10-local-section-main-material.md)。

单构件兼容入口仍保留 `emit-excel`、`analyze`、`compare`；真实加工清单只作对照，不反馈修改模型识别标签。默认不生成图纸。

## 工作区与项目路标

- `src/zijinhua_tekla/`、`tests/`：正式识别代码及回归。
- `docs/design/`：当前设计与验收要求；`docs/verification/`：验证证据与历史记录。
- `cache/`、`outputs/` 及根目录 CAD/Excel：被忽略的本地业务现场，不是版本基线。
- 零件出图单独保留在 `I:\tmp\zijinhuatekla-part-drawing-engine`、`codex/offline-part-drawing-engine`，后续独立开发。

先读 [STATUS.md](STATUS.md)、[TASKLIST.md](TASKLIST.md) 和 [识别主线设计](docs/design/2026-10-10-recognition-mainline.md)。本地 `main` 仍在旧出图历史上，当前识别工作以收尾分支为准；本轮不直接重写或推送 main。
