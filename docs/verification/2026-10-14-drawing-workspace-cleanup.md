# 出图工作区整理验证

日期：2026-10-14（Asia/Shanghai）

## 完成范围

- 主目录 `I:\zijinhuatekla` 从识别分支实际切到 `codex/offline-part-drawing-engine`，切换前检查没有未跟踪/忽略文件与目标分支新增跟踪文件冲突。
- `feat/recognition-mainline` 保留在 `635cdd9`，未合并或重写。本地 main 保留 `7a9fb37`；其提交已由出图远端分支保存，无须为备份而推送 main。
- 旧目录 `I:\tmp\zijinhuatekla-part-drawing-engine` 留在 detached HEAD `7a9fb37`，本会话创建的检查记录经哈希一致核对后转入主目录，旧目录工作区干净。保留它的本地数据和目录。
- 原有 12 个提交已经推送：远端出图分支由 `c2d9e61` 快进到 `7a9fb37`；后续整理提交也使用同一远端分支。
- 更新 README 的 v1/v2、原生尺寸/引出、坡口证据、入口命令和边界；AGENTS 明确当前分支与识别隔离、Git 收尾和文档人工审核责任。
- STATUS 收敛为当前状态、验证和最多三项下一步；TASKLIST 仅保留未完成出图任务。原文完整归档到 [整理前历史](2026-10-14-pre-drawing-cleanup-history.md)，不丢弃旧实验或工程边界。
- `.gitignore` 补环境/凭据、CAD 锁文件，并延续识别分支对既有本地参考资料和历史 skill 预览的排除。根目录 CAD/Excel、cache、outputs、dist 没有删除或搬动。
- 业务源码和测试未修改。共享全局 hook 文件未修改；本次提交/推送按用户明确授权在会话中完成，不依赖 Stop hook 是否触发。

## 本轮实测

### 完整回归

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests
```

实际导入：`I:\zijinhuatekla\src\zijinhua_tekla\__init__.py`。

结果：190 tests OK。初次沙箱运行有 22 个临时目录访问错误，获得执行权限后原命令通过；未修改测试或算法。既有 openpyxl datetime.utcnow deprecation warning 不影响断言。测试日志中的 `REJECTED=1` 来自拒绝冲突数据的测试用例，不代表回归失败。

### CLI smoke 与文件读回

```powershell
python -B -m zijinhua_tekla.cli draw-parts --snapshot-root tests\fixtures\part_drawing --out outputs\drawing-cleanup-20261014 --cjk-font C:\Windows\Fonts\simhei.ttf
```

结果：`OK=1 / REVIEW_REQUIRED=1 / REJECTED=0`，无 load issues。

- `P-1001` 正常出图。
- 两份 v2 fixture 归并为 `P-2001`，因 principal face edge evidence unresolved 进入 `FEATURE_AMBIGUOUS` 复核，保持现有证据不足不猜测的质量门。
- 两份 DXF 重新读取后 audit 均为 `0 errors / 0 fixes`。
- 两份 PDF 均能读回，页数均为 1；本轮未做图面视觉或 AutoCAD 人工验收。

### Git 与文档审核

- 提交前检查 `git diff --check`、文档本地引用和目录边界；归档原文保留既有历史描述，不作为当前事实。
- `.env`、`.venv`、cache、outputs 和 CAD 锁文件命中 ignore；`.env.example` 保留可跟踪。
- 全局 check-docs.ps1 返回 `exempt: existing status system`，只计豁免；本轮另外核对 README 与代码契约、当前状态、未完成任务和引用文件。
- 整理文件显式暂存，检查没有业务代码、敏感文件和大文件混入；不执行全量 add。
- 收尾核对当前分支、工作区干净以及 HEAD/远端 SHA 一致；最终整理提交号由 Git 历史记录，避免文档自引用提交号。

## 保留的业务待办

AutoCAD 打开审计、真实复杂样件验收、孔阵与工序图扩展仍按 [任务队列](../../TASKLIST.md) 管理。本次整理不将这些业务待办伪记为已完成。
