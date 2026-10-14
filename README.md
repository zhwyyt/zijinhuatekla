# Zijinhua Tekla — 零件出图

当前分支 `codex/offline-part-drawing-engine`，工作目录 `I:\zijinhuatekla`。本分支提供平板零件离线加工图：消费 Tekla 导出的 `partDrawingSnapshot.v1/v2`，按精确 `partPosition` 和制造指纹归并，输出 DXF、PDF、drawing JSON 和批次质量摘要。

识别主线和已验收 Qt6 程序保留在 `feat/recognition-mainline`；本地 `main` 是旧出图基线，不是当前识别或出图开发入口。

## 已支持与边界

- 平板轮廓、孔和加工特征，先规划尺寸链再布局避让；DXF 使用原生尺寸、孔组引出和中心线。
- v2 接收 final solid、双主面和 Boolean operative solid；仅在双主面证据充分时识别坡口并输出 `BEVEL`。
- 折弯板、曲面板和型材仍阻断自动出图；无参数曲线保留 `UNKNOWN/UNRESOLVED`。缺失或冲突证据进入质量门，不猜测补图。
- `OK` 表示自动出图完整，仍需人工复核。目标 AutoCAD 打开审计尚待完成。

## 本地运行

Python 3.10+，在仓库根执行：

```powershell
python -m pip install -e .
# 显式使用当前 checkout，避免其他 worktree 的 editable 安装影响导入。
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests
python -m zijinhua_tekla.cli draw-parts --snapshot-root tests\fixtures\part_drawing --out outputs\part-drawings --cjk-font C:\Windows\Fonts\simhei.ttf
```

真实出图将 `--snapshot-root` 换为导出快照目录。包含中文的 PDF 需要通过 `--cjk-font` 提供本机存在、可嵌入的 CJK TrueType 字体；上面的字体路径是 Windows 示例。输出放在 `outputs/`，不进入 Git。`analyze` 仍保留旧离线对齐能力，当前正式识别能力请使用识别分支。

## 文档入口

- [当前状态与交接](STATUS.md)、[未完成任务](TASKLIST.md)、[工作规则](AGENTS.md)。
- [离线出图设计](docs/design/2026-07-13-part-drawing-offline-architecture.md)、[v2 几何证据](docs/design/2026-07-14-part-drawing-v2-geometry-evidence-and-annotations.md)。
- [真实 v2 验证](docs/verification/2026-07-14-part-drawing-v2-geometry-smoke.md)、[本次整理验证](docs/verification/2026-10-14-drawing-workspace-cleanup.md)。

本地 CAD/Excel、缓存、输出、构建产物、环境和凭据由 `.gitignore` 排除。沿用 STATUS/TASKLIST 文档体系；全局文档脚本的豁免结果不能替代实际内容核对。
