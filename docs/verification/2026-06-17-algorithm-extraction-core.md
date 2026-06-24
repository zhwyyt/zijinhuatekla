# Algorithm Extraction Core Verification

## 变更范围

本次把三个参考项目中已经可落地的算法口径抽到 `src/zijinhua_tekla/`：

- `features.py`
  - 建立 `PartFeatureSnapshot` 作为统一零件特征契约。
  - 支持当前 bundle JSON adapter。
  - 增加 `teklatest` `PartFeatures` adapter，承接孔、螺栓孔、内部孔、倒角、剖口、缺口、折弯、焊缝和形状分类字段。
  - 保留 `snapshot_to_part_dict` 兼容桥，现有 Data Quality Gate 不需要重写。
- `member_classifier.py`
  - 建立 `MemberBodyClassifier` 输出：`body_type`、`confidence`、`reason_code`、`evidence_codes`。
  - 支持读取已有 `Classification`。
  - 增加基于 `PartFeatureSnapshot.profile` 的 `BH/H/BOX` profile-family 证据。
- `part_roles.py`
  - 从 `cli.py` 抽出零件角色、工序、形状推断。
  - CLI 改为调用 `classify_part_role`，避免继续在命令入口堆业务规则。
  - 将 `T3-PR` 等项目前缀写法改为通用编号系列识别，例如 `A1-PR-42`。
- `rules.py`
  - 将 BH 拆板派生从 `T3-H-xxx[s/x/f]` 改为通用 `*-H-xxx[s/x/f]` 系列识别。
- `bracket_classifier.py`
  - 建立牛腿/附属件簇分类入口。
  - 抽取 `lingjianjuesemimo` 中牛腿核心证据：`ROOT_LOCAL_ATTACHMENT`、`OVERHANG_DOMINANT`、`AXIS_SPAN_LIMITED`、`EXTERNAL_CENTROID`、`NOT_END_CONNECTION`。
  - 当前只实现可解释 Bracket 判定；证据不足时返回 `Unknown`，不硬凑。
- `casebank.py`
  - 建立人工反馈案例入口：`DATA`、`FEATURE`、`SCORING`、`NEW_TYPE`。

## 未完成范围

- `autoteklasuanfa` 的截面 trace、闭环拓扑、station ratio 还没有完整迁入 Python；当前 `MemberBodyClassifier` 先接 profile-family 证据和已有分类结果。
- `lingjianjuesemimo` 的附属件簇提取、RootZone 自动识别、Overhang 几何计算还没有在当前 bundle 数据上完整重建；当前先定义可消费这些特征的分类入口。
- `teklatest` 的 Tekla API 侧提取逻辑没有复制到 Python；当前通过 adapter 接收其导出结果，避免绑定 Tekla API 类。

这些未完成项属于导出字段和空间/拓扑证据补强，不应通过单个构件号或零件号补丁解决。

## 验证命令

```powershell
python -m unittest tests.test_feature_snapshot
python -m unittest tests.test_algorithm_interfaces
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\algorithm-extraction-smoke-20260617
```

## 验证结果

- `tests.test_feature_snapshot`：4 tests OK。
- `tests.test_algorithm_interfaces`：7 tests OK。
- `python -m unittest discover -s tests`：16 tests OK。
- T3-5GKZ-10 CLI smoke 输出成功生成：
  - `outputs\algorithm-extraction-smoke-20260617\T3-5GKZ-10-alignment.csv`
  - `outputs\algorithm-extraction-smoke-20260617\T3-5GKZ-10-alignment.json`
  - `outputs\algorithm-extraction-smoke-20260617\T3-5GKZ-10-analysis.md`

T3-5GKZ-10 样例结果保持基线：

- `MATCH=55`
- `MATCH_CONFLICT=4`
- `DATA_MISSING=3`
- Excel 行数 `62`

## 结论

第一阶段算法抽取已经完成到工程可继续演进的程度：零件特征契约、主材分类接口、零件角色/工序/形状算法、牛腿证据分类入口、Case Bank 和回归测试均已落地。

下一步不是继续在业务判断里补零碎规则，而是补导出器/Feature Snapshot 的截面拓扑、空间关系、root/contact/overhang 字段，再把参考项目中更深的主材拓扑和牛腿簇提取策略接入现有接口。
