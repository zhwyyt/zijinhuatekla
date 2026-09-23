# Tekla 导出识别 GUI

## 目标

提供一个本地 GUI，支持从打开的 Tekla 模型导出当前选择集，并把导出结果汇总成一个 Excel。

## 模块

1. 模式1 - Tekla 在线导出：选择输出文件夹，调用本机 `TeklaSectionClassifier.Runner.exe --output <文件夹>`，只导出 Tekla 当前选择集中的构件；导出完成后立即校验 bundle 和 `members/member_*.json`，并自动把结果切换到模式2。
2. 模式2 - 已导出文件分析：选择导出根目录或直接选择 `tekla-body-bracket-export.bundle.json`，输入项目名称和工程区域，选择输出目录后生成单个 Excel。

## 输出

- 文件名：`{项目名称}_{工程区域}.xlsx`；重名时追加时间戳。
- Sheet：
  - `零件特征`
  - `构件复杂度`

## 启动

```powershell
$env:PYTHONPATH='src'; python -m zijinhua_tekla.gui.report_gui
```

也可使用：

```powershell
$env:PYTHONPATH='src'; python -m zijinhua_tekla.cli gui
```

## Acceptance Criteria

- 模式1缺少输出文件夹或导出程序时拒绝执行；Tekla 未连接、导出进程失败或导出结果无效时显示错误。
- 模式1导出成功后显示构件数量，并自动把导出目录回填到模式2。
- 缺少 bundle、项目名称或工程区域时拒绝生成。
- 部分构件失败时不中断整包输出，并明确显示失败数量。
- GUI 读取大 bundle 时在后台线程执行，界面不冻结。

## Verification Plan

- 单元测试覆盖临时导出包、两个 sheet、文件名清洗和无效根目录。
- 单元测试 mock 导出进程，覆盖 `--output` 参数、导出程序不存在、输出目录为空和导出结果校验。
- 用最新 289 装配真实导出包做 smoke。
