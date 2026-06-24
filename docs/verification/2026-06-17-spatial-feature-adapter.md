# Spatial Feature Adapter Verification

## 变更范围

本次没有先修改 `I:\xingcaisuanfa` 的 Tekla C# 导出器，而是在 `I:\zijinhuatekla` 中新增空间特征适配层：

- `src/zijinhua_tekla/spatial_features.py`
  - 从 member `Classification.PartRoles` 识别主体零件：`web_candidate`、`flange_candidate`、`wall_candidate`。
  - 从 bundle `relationships` 聚合附属件簇。
  - 从 `boundingBox`、`centroid`、member `AxisSegments` 推导：
    - `root_contact_ratio`
    - `cantilever_ratio`
    - `span_along_axis`
    - `assembly_span`
    - `centroid_outside_body`
    - `has_end_connection_signal`
  - 直接生成 `AppendageClusterFeatures`，并喂给 `BracketClassifier`。
- `src/zijinhua_tekla/bracket_classifier.py`
  - 收紧牛腿判定：必须包含 `NOT_END_CONNECTION`，避免端部连接件被当作牛腿。
- `tests/test_spatial_features.py`
  - 新增合成 bundle/member 的空间适配测试。

## 为什么先不改导出器

当前 `I:\xingcaisuanfa` 的 bundle 已经包含足够启动第一轮空间推导的字段：

- `parts[].centroid`
- `parts[].boundingBox`
- `parts[].volume`
- `parts[].thickness`
- `relationships[].edgeType`
- `member.AxisSegments`
- `member.Classification.PartRoles`

因此当前优先在 `zijinhuatekla` 建适配层，可以更快验证牛腿/附属件簇算法边界。后续只有当 root/contact/overhang 精度不足时，再回到 C# 导出器补更细字段。

## 验证命令

```powershell
python -m unittest tests.test_algorithm_interfaces tests.test_spatial_features
python -m unittest discover -s tests
```

T3-5GKZ-10 空间诊断命令：

```powershell
python - <<'PY'
import json
from pathlib import Path
from collections import Counter
from zijinhua_tekla.spatial_features import appendage_cluster_features_from_bundle, classify_appendage_clusters_from_bundle
root = Path(r'I:\xingcaisuanfa\cache\codex_reexport_probe_20260617_1')
member = json.loads((root / 'members' / 'member_T3-5GKZ-10.json').read_text(encoding='utf-8'))
bundle = json.loads((root / 'tekla-body-bracket-export.bundle.json').read_text(encoding='utf-8'))
assembly_id = str(member['Member']['AssemblyId'])
assembly = next(item for item in bundle['assemblies'] if str(item['assemblyId']) == assembly_id)
features = appendage_cluster_features_from_bundle(assembly, member)
classes = classify_appendage_clusters_from_bundle(assembly, member)
print('clusters', len(features))
print('roles', Counter(c.role for c in classes))
PY
```

## 验证结果

- `tests.test_algorithm_interfaces tests.test_spatial_features`：11 tests OK。
- `python -m unittest discover -s tests`：20 tests OK。
- T3-5GKZ-10 空间诊断：
  - 附属件簇：`15`
  - 分类计数：`Unknown=13`、`Bracket=2`

收紧 `NOT_END_CONNECTION` 后，端部连接信号为 true 的候选不再判为 Bracket。

## 结论

现有导出字段已经足够先做第一轮空间特征适配和牛腿候选识别，不需要立即修改 `I:\xingcaisuanfa` 导出器。

下一步应围绕真实样例人工校准两个 Bracket 候选是否准确。如果误判，再归因到：

- root contact 估计粗糙；
- body envelope 过粗；
- cluster BFS 关系边过宽或过窄；
- end connection signal 需要更细的端部/连接板语义。

只有归因为字段不足时，再修改 Tekla C# 导出器补字段。
