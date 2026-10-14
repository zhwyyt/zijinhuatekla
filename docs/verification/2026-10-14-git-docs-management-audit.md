# 出图分支 Git 与文档管理检查

检查日期：2026-10-14（Asia/Shanghai）

> 本记录为整理前检查快照。用户随后授权整改、推送和主目录切换；最终状态见 [整理验证](2026-10-14-drawing-workspace-cleanup.md)。以下路径、分支占用和未推送数量描述检查当时，不代表整理后状态。

## 范围和结论

本轮操作位置使用既有 worktree `I:\tmp\zijinhuatekla-part-drawing-engine`，分支 `codex/offline-part-drawing-engine`，检查基线 `7a9fb37`。原目录 `I:\zijinhuatekla` 仍为 `feat/recognition-mainline`，未改其 checkout。未合并、重置、提交或推送；本轮只新增本记录。

结论：基础机制已建立，但出图分支尚未完全规范化。主要缺口是未推送提交、当前状态与历史混杂、README 契约版本滞后，以及现有文档检查对本仓库直接豁免。

## Git 检查

| 项目 | 实测结果 | 判断 |
| --- | --- | --- |
| 工作区 | 写入本记录前，两处 `git status --short` 均无文件改动 | 通过 |
| 分支隔离 | 识别与出图各有独立 worktree | 通过；复用出图 worktree，不强行重复检出同一分支 |
| 出图远端 | GitHub 实际分支为 `c2d9e61`；本地 `7a9fb37`，ahead 12 / behind 0 | 尚未同步 |
| 本地 main | 同样指向 `7a9fb37`；GitHub main 为 `aad1a97`，ahead 50 / behind 0 | main 与正式识别主线含义不一致；不能直接推送或混合合并 |
| 识别远端 | 本地和 GitHub `feat/recognition-mainline` 均为 `635cdd9` | 已同步 |
| 提交格式 | 出图分支最近 30 条提交标题均满足 type: summary | 通过，不代表全部历史已迁移 |
| 文件管理 | 检查前跟踪文件 191 个；无大于 10 MiB 文件；无命中敏感文件名规则的文件；无已跟踪且被 ignore 的文件 | 本轮范围通过，不是完整历史或内容级秘密扫描 |
| 忽略规则 | cache、outputs、CAD/Excel、Python/.NET 产物有规则；探针 `.env`、`.venv/probe` 未忽略 | 建议补齐本地环境忽略规则；当前未发现对应文件已入库 |
| Git 原生 hook / CI | 未配置 core.hooksPath，hooks 目录仅 sample；未跟踪 .github 工作流 | 防护依赖本机助手 hook，并非仓库自身强制门禁 |

远端通过 `git ls-remote --heads origin main codex/offline-part-drawing-engine feat/recognition-mainline` 实际核验，返回值与本地 remote-tracking refs 一致。沙箱内首次调用因 Windows schannel 凭据访问失败；获得执行扩展后只读重试成功。

## 自动 Git 机制

已读取全局 Claude settings、Codex config、`C:\Users\Administrator\git-workflow.md` 和 `C:\Users\Administrator\.claude\hooks\auto-git.ps1`：

- 两套配置均声明 Stop hook 指向 auto-git.ps1；脚本实现敏感文件名脱敏、10/50 MiB 门槛、临时分支名拦截、main/master 默认不推、exp 分支本地保留等策略。
- 这里只确认配置和代码，未执行真实 Stop 事件或制造提交来证明端到端生效。
- 脚本在工作区无改动时直接退出。因此这 12 条已有未推送提交不会仅因下一次干净会话结束而自动补推。
- 脚本使用事件的 cwd/workspaceRoot 决定仓库，不扫描其他 worktree。本聊天绑定原目录，仅给命令指定出图 workdir，不保证 Stop hook 会处理出图 worktree。
- git-workflow.md 存在文字冲突：前文说口头禁止提交无效，后文又说可以口头禁止；main 推送说明也有“个人项目例外”与实际 allow-main-push 文件门槛不一致。属于共享规范问题，本轮未修改全局文件。

## 文档检查

沿用 STATUS.md + TASKLIST.md + docs/design + docs/verification 合乎项目约定，无须新增另一套 CURRENT_STATE/TASKS/LAST_HANDOFF。

1. **当前状态混入历史**：STATUS.md 共 309 行。顶部 v2 交接已经说明真实闭环，后面仍保留“尚未实现 Tekla 导出器、没有真实模型 smoke”和旧未提交现场；旧记录有日期，但没有统一归档边界。应保留历史证据，收敛当前状态入口。
2. **任务队列未收敛**：TASKLIST.md 共 114 行，混合已完成、识别、BOX 工序和零件图任务。2026-06-26 收敛待办仍描述待提交现场；相关 topology/report 文件已由 `421320f` 等提交纳入版本管理，检查时工作区干净。
3. **README 落后于代码**：README.md:7 仅写快照 v1；snapshot_input.py:25-27 明确同时支持 v1/v2，最新验证记录描述 v2 坡口和原生标注闭环。
4. **业务约束表述不一致**：TASKLIST.md:19 写“按零件号、规格、长度、几何候选匹配”，易被理解为自动匹配；应对齐 AGENTS.md 的普通编号精确匹配、几何仅复核证据约束。本次未判断代码存在违规匹配。
5. **分支职责指引过旧**：出图 AGENTS.md 仍描述早期识别阶段，未记录当前出图 worktree、主入口、与识别主线的隔离边界；识别分支已有这些说明。
6. **文档门禁为豁免**：执行 check-docs.ps1 返回 `exempt: existing status system`，exit 0。它只验证两个文件存在便退出，不检查内容新鲜度、冲突、任务完成状态或交接质量。
7. **证据归档已有基础**：设计和验证目录已跟踪，v2 验证记录包含命令、结果和剩余边界。四个入口文件引用的 docs 路径仅 `docs/project-overview.md` 在出图 worktree 不存在；该文件属于显式忽略的本地历史笔记，不应作为可移交依赖。

历史记录中的 190 项 Python 测试、C# 测试及 CAD/PDF 结果均为原记录，本轮未重跑，不作为本轮通过项。

## 建议整改顺序

1. 先收敛出图 README、AGENTS、STATUS、TASKLIST：明确 v2 兼容 v1、当前边界和最多三项下一步；旧现场移入历史记录，清理失效待办，保留证据链接。
2. 再核对 12 个未推送提交和目标出图远端，单独完成同步；main 的定位另行决定，不把识别和出图历史直接混合。
3. 最后补本地环境 ignore，并让文档审核真正覆盖旧版状态体系；同步修正全局 Git 说明冲突，单独验证实际 Stop hook 的 worktree 路由。

## 本轮验证清单

- Git worktree、分支、工作区、upstream、最近提交、远端实际 SHA：已检查。
- 跟踪文件体积、敏感文件名、ignore 覆盖、文档引用、代码契约版本：已检查。
- check-docs.ps1：exit 0，但结果为豁免。
- git diff --check：写入前通过；本记录写入后另行复核。
- 业务测试、Tekla、AutoCAD、全历史秘密扫描、GitHub 服务端分支保护和 Stop hook 实际执行：本轮未验证。
