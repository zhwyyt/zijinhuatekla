# Tekla 导出识别 GUI

## 目标

提供一个本地 GUI，把 Tekla 导出根目录识别结果汇总成一个 Excel。

## 模块

1. Tekla 模型导出信息：选择导出根目录或直接选择 `tekla-body-bracket-export.bundle.json`，显示 bundle 与构件文件检查结果。
2. Excel 输出：输入项目名称和工程区域，选择输出目录后生成单个 Excel。

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

- 缺少 bundle、项目名称或工程区域时拒绝生成。
- 部分构件失败时不中断整包输出，并明确显示失败数量。
- GUI 读取大 bundle 时在后台线程执行，界面不冻结。

## Verification Plan

- 单元测试覆盖临时导出包、两个 sheet、文件名清洗和无效根目录。
- 用最新 289 装配真实导出包做 smoke。
