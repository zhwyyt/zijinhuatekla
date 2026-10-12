# Qt6 桌面版验收与源码收尾

## 人工验收

2026-10-12 用户明确确认：“Qt6 界面和 exe 打包相关源码已经验证过了，没问题。”据此记录桌面交付已人工验收，提交 `feat/recognition-mainline` 上此前未提交的 Qt6、导出日志、打包脚本和相关测试。收尾前 HEAD 为 `1853090`，本轮不修改已验收实现。

验收范围是两个桌面模块与 exe 打包，不自动扩展为全部构件/零件业务标签、跨所有电脑或其它 Tekla 版本已验收。此前助手的进一步界面自动化被用户 Esc 中断；不能把该历史操作写成已完成的 979 构件 GUI 自动回归。用户本次确认结束桌面验收待办，不再要求重复操作。

## 交付内容

- PySide6/Qt6 替代 Tkinter；模块1指定导出存放目录，读取 Tekla 已打开模型中的当前选择集，每次生成唯一数据集目录；模块2指定数据集目录或 bundle、项目名/区域、结果目录，调用正式三表报告入口。
- QThread 后台执行，信号更新日志与进度；运行中防重复启动与关闭；失败恢复操作。完成、部分失败、主轴复核分别提示，日志保存到输出目录的 logs，目录写入失败时尝试用户本地日志目录。
- Runner 标准输出/错误实时读取、隐藏控制台、超时处理、空选择校验；构件数量按 bundle 装配计数，避免同号 member 文件数代替装配实例数。
- 单文件 exe 内置 Python/Qt 和 Runner 三个文件；不含模型、Excel、cache 或商业 Tekla API DLL。构建命令和运行前提见 [使用说明](../desktop-user-guide.md)。

## 自动证据

已有最终源码测试 `outputs/qt6-desktop-20261010/tests-fixed.log`：**302 tests，OK**。覆盖原识别规则、Qt 后台任务/锁定/恢复/提示、目录规范化、导出独立目录、子进程非零退出/超时/空选择、构建 PATH 隔离。本轮仅核验已有结果并补齐文档，没有为文档收尾重复执行整批联调。

`build-fixed.log` 和 `build/qt6-desktop/startup-verification.json` 记录实际打包 exe 启动：Qt 6.11.2、platform=windows、window_visible=true、modules=2。2026-10-12 重新计算现有 exe SHA256，与清单一致：

- 路径：`dist/ZijinhuaTekla/ZijinhuaTekla.exe`
- 大小：98,877,580 字节。
- SHA256：`a4c9445e5fecf525cf76a07c96d53ee495bdcd95d07daa7cbb1a67adfa3f00d4`
- 发行清单：同目录 `build-manifest.json`，仅供校验，不是运行依赖。

GUI 的 CCG quality/security 检查已通过：质量检查保留 UI 初始化 54 行的提示，`closeEvent` 是 Qt 固定回调名；安全扫描未报发现。提交前核对当前打包脚本/入口与导出器，执行窄范围安全检查及 CCG staged 变更检查，实际文件数量和 `git diff --cached --check` 一并校验。扫描原始输出保存在忽略的 outputs 目录，二进制不推 Git。

2026-10-12 收尾检查结果：当前打包脚本、入口、导出器 3 文件安全扫描通过；CCG 暂存检查通过，覆盖 17 文件，与 Git 实际暂存范围一致，空白检查通过。新增模块及依赖变更提示已由 README、使用说明与本记录覆盖。输出见 `outputs/qt6-desktop-20261012/`。

## 首次打包失败及复盘

首次 exe 启动报 `DLL load failed while importing QtCore: 找不到指定的程序`。构建依赖表证明 PyInstaller 从继承的 PATH 中收进 Poppler 的 `icuuc.dll`；对照 PE 符号表，Qt6 所需的 20 个 ICU 接口在该 DLL 中全部缺失，而系统 ICU 全部提供。修复仅隔离打包子进程 PATH，不更改全局环境或 Qt 算法；新依赖表不再包含误收的 ICU 库。

新增实际发行文件启动门槛：构建脚本运行生成的 exe，创建 Windows Qt 窗口并验证后再输出清单。适用于原生依赖桌面程序的经验是：源代码测试和打包成功不能替代发行物运行；构建机工具链的同名 DLL 会污染依赖解析。以后同时检查依赖来源、符号兼容和最终可执行文件启动，避免只验证开发环境。

主轴、主材判定规则及独立出图 worktree 未在桌面收尾中修改。
