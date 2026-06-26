# T2-3GL-55 异形 H/GL 主板人工确认

日期：2026-06-26

## 背景

最新 Tekla 选择集导出构件为 `T2-3GL-55`，导出目录：`I:\zijinhuatekla\cache\20260626_134928`。

算法初判：

- 构件类别：H/GL 类异形梁，不是 BOX。
- 证据标签：`section-height-varies`、`section-variation-irregular`、`h-irregular-nonparallel-flange`、`many-local-stiffeners`、`endplates-present`。
- 主材候选：
  - `263127110 / T2-3B-526 / PL30*400 / web_candidate`
  - `263127116 / T2-3B-797 / PL14 / flange_candidate`
  - `263271361 / T2-3B-508 / PL30*400 / wall_candidate / continuous plate fallback`

## 人工确认

用户确认：`T2-3B-508` 是主板。

因此当前业务口径改为：

- 确认主板：`T2-3B-526`、`T2-3B-797`、`T2-3B-508`。
- `T2-3B-508` 不再表述为“需人工复核候选”；它是已人工确认的异形 H/GL 主板。
- 后续报告中若同时输出算法来源，应表达为：`wall_candidate (human_confirmed_main_plate)`，而不是“候选待复核”。

## Case Bank

已写入 `cases\seed.json`：

- `case_id`: `T2-3GL-55:h-gl-confirmed-main-plates`
- `expected_label`: `H_GL_CONFIRMED_MAIN_PLATES`
- `human_note`: 人工确认 `T2-3B-526`、`T2-3B-797`、`T2-3B-508` 都属于异形 H/GL 构件主板。

## 后续建议

当前 pipeline 只有 BOX 分段 confirmed case 的消费逻辑。若要让报告自动把 H/GL 人工确认主板升级为 confirmed，需要新增通用读取口径，例如：

- `member_id:h-gl-confirmed-main-plates`
- 从 human note 或结构化字段解析确认主板 partPosition。
- 输出层区分 `algorithm_role` 与 `confirmation_level`。
