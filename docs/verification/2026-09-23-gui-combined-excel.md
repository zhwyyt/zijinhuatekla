# 2026-09-23 Tekla 导出识别 GUI 验证

## 单元测试

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
```

结果：`241 tests OK`。

## 真实数据 smoke

- 输入：`cache/20260922_173818`
- 输出：`outputs/gui-smoke-20260923/GUI验证_真实数据.xlsx`
- 结果：289 装配、4044 行零件特征、289 行构件复杂度、0 错误。
- Sheet：`零件特征`、`构件复杂度`。

## 未验证

- 模式1未真实触发 Tekla 导出；已确认默认导出程序存在，并用 mock 进程验证参数和导出结果校验。
- 未做人工作业级图面复核；GUI 交互按钮仅通过类构造、CLI help 和共享导出函数验证。
