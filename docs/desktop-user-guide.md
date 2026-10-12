# Tekla 构件识别桌面版

双击 `ZijinhuaTekla.exe` 即可启动。Qt6 和 Python 运行环境已内置，无需单独安装 Python；首次启动会解压运行组件，可能稍慢。

目标系统为 Windows 10/11 64 位，不支持 Windows 7。只需复制 exe；旁边的 `build-manifest.json` 是版本、文件完整性与启动验证清单，程序运行不依赖它。

## 模块 1：Tekla 模型导出

1. 在本机 Tekla Structures 2017 中打开模型，选中要导出的构件或零件。
2. 选择“数据集存放目录”，点击“开始导出”。
3. 请保持模型和选择集不变，等待日志显示导出完成。所选目录内自动新建 `Tekla_日期时间_标识` 数据集，包含 bundle 和 members；每次导出独立保存。
4. 完成后自动切换模块 2 并填入数据集位置，选择结果目录即可继续。

在线导出需本机安装 Tekla 2017 和 .NET Framework 4.8；导出器已内置，默认无需指定程序。其它 Tekla 版本未验证。请让本程序与 Tekla 在同一 Windows 用户会话和相同权限级别运行。高级选项可选择兼容的自定义导出器。

## 模块 2：数据集识别

1. 选择完整的 Tekla 导出目录，或其中的 `tekla-body-bracket-export.bundle.json` 文件。
2. 填写项目名称、工程区域，并选择“结果存放目录”。
3. 点击“开始运算并生成结果”，等待保存完成。
4. 点击“打开结果文件夹”，查看 `项目名称_工程区域.xlsx`。

结果包含构件角色、构件复杂度、零件特征三张主表，必要时增加连接复核、识别失败表。离线模块不需要打开或安装 Tekla。不要只复制 bundle 而遗漏同目录的 members；同号装配实例依赖 `members/batch_summary.json`。

## 日志与错误

- 下方日志显示实时输出，完整日志保存在所选结果目录的 `logs` 文件夹。无法写入时，尝试 `%LOCALAPPDATA%\ZijinhuaTekla\logs`；“打开日志”可查看详细原因。
- 输入缺失、空选择、导出器连接失败、数据无效或写入失败会弹窗提示。任务结束后按钮恢复，可以纠正后重试。
- 部分构件失败时会生成可用结果并显示警告，失败原因在 Excel“识别失败”表及日志中。主轴复核不等于程序失败：旧缓存需要重新导出，几何缺失还需检查模型。
- 长时间导出时查看日志；任务运行中不能关闭窗口，避免损坏输出。若操作系统强制结束程序，本次数据集可能不完整，请重新导出。
- 算法输出中的 UNKNOWN 和复核项保留不确定性，不代表已经人工验收。

## 从源码构建

在项目根目录执行（Windows / Python 3.10+）：

```powershell
python -m pip install -e ".[build]"
python scripts/build_desktop.py --runner-dir I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48
```

输出为 `dist/ZijinhuaTekla/ZijinhuaTekla.exe`，同目录包含本说明及带 SHA256 的 `build-manifest.json`。Runner 目录必须来自已验收分组跨度主轴的构建，包含 Runner.exe、Runner.exe.config 和 TeklaSectionClassifier.dll；打包不携带商业 Tekla API DLL、模型或业务数据。
