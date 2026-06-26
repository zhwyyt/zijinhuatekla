# New Export Contract Project Audit

## Scope

User asked to audit the whole `I:\zijinhuatekla` project against the new Tekla export, to avoid missing pipeline/report/test/documentation updates.

Caches used:

- New selected member: `I:\zijinhuatekla\cache\20260624_150131`, member `T3-5GKZ-2`.
- Regression member: `I:\zijinhuatekla\cache\20260624_144128`, member `T3-5GKZ-10`.

## Audit Checklist

Checked the full offline chain:

1. Export contract fields exist in real cache.
2. Python consumers read `mainMaterialEvidence`, `sectionProjectionEvidence`, `boxSectionEvidence.stationLoops`, `sectionLoops`, and `segments`.
3. BOX main wall confirmed set flows into BOX inside/outside relation classification.
4. BOX main wall confirmed set also flows into station topology diagnostics.
5. Reports write JSON/CSV for main wall groups, inside/outside relations, and station topology diagnostics.
6. CLI prints every generated report path.
7. Unit tests cover report paths and pipeline result fields.
8. Design/verification docs record the new section topology contract.

## Findings

### 1. CLI output was incomplete

Reports already generated these files, but CLI did not print them:

- `*-box-part-spatial-relations.json/csv`
- `*-box-station-topology-diagnostics.json/csv`

Fix: updated `src/zijinhua_tekla/cli.py` to print both report pairs.

### 2. Report tests did not lock station topology output

`tests/test_reports_offline.py` covered BOX main material and BOX inside/outside relation outputs, but did not assert station topology diagnostics JSON/CSV paths, flattened rows, or Markdown section.

Fix: added a `BoxStationTopologyDiagnostic` sample and assertions for:

- diagnostics JSON path;
- diagnostics CSV path;
- flattened `topology_status`, `station_scope`, `trigger_part_positions`;
- Markdown `BOX Station Topology 诊断` summary and output links.

### 3. Pipeline test did not prove station topology result propagation

`tests/test_pipeline_offline.py` verified BOX inside/outside relations but did not include `metadata.boxSectionEvidence.stationLoops` in the fixture, so it could not prove topology diagnostics are wired through `run_offline_analysis`.

Fix: added a minimal `teklaSolidFaceSectionSegments.v2` fixture and asserted one `box_station_topology_diagnostics` result.

### 4. Design contract still stopped at the older main-material fields

`docs/design/2026-06-23-main-material-segment-export-contract.md` covered `memberAxisEvidence`, `mainMaterialEvidence`, and `sectionProjectionEvidence`, but did not promote the 2026-06-24 section segment/loop topology export as formal project contract.

Fix: added `Box Section Topology Evidence` section documenting:

- `metadata.boxSectionEvidence.source=teklaSolidFaceSectionSegments.v2`;
- station-level `sectionSegments`, `sectionLoops`, counts, and diagnostics;
- part-loop-level `segments`, `sectionLoops`, loop status, area, validity, bounds, diagnostics;
- Python consumer priority: `sectionLoops` -> `segments` polygonize -> old `points` fallback.

## Real Cache Contract Check

Command:

```powershell
python -c "... inspect I:\zijinhuatekla\cache\20260624_150131 ..."
```

Result for `T3-5GKZ-2`:

- `boxSectionEvidence.source = teklaSolidFaceSectionSegments.v2`
- station loops: `89`
- stations with `sectionLoops`: `89`
- stations with `sectionSegments`: `89`
- part loops: `1229`
- part loops with `sectionLoops`: `1227`
- part loops with `segments`: `1229`
- parts with `mainMaterialEvidence`: `228 / 228`
- `isBodyWallPlateCandidate=true`: `211`

## Verification Commands

```powershell
python -m unittest tests.test_reports_offline tests.test_pipeline_offline tests.test_box_station_topology_diagnostics tests.test_box_part_spatial_relations tests.test_box_main_material_segments
python -m py_compile src\zijinhua_tekla\cli.py src\zijinhua_tekla\reports\offline.py src\zijinhua_tekla\pipeline\offline.py tests\test_reports_offline.py tests\test_pipeline_offline.py
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_150131 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-2 --out outputs\selected-T3-5GKZ-2-contract-audit-20260624
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_144128 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\T3-5GKZ-10-contract-audit-20260624
node C:\Users\Administrator\.agents\skills\ccg\tools\verify-change\scripts\change_analyzer.js --json
```

Results:

- Targeted tests: `25 tests OK`.
- Py compile: exit `0`.
- Full tests: `78 tests OK`.
- CCG change analyzer: `passed=true`; remaining notes are informational about new module README/config documentation. The section topology contract and verification docs have been updated.

## Smoke Results

### T3-5GKZ-2

Output: `outputs\selected-T3-5GKZ-2-contract-audit-20260624`.

- File count: `23`.
- Has `box-part-spatial-relations.json/csv`: yes.
- Has `box-station-topology-diagnostics.json/csv`: yes.
- Confirmed main wall Tekla entities: `16`.
- Confirmed main wall positions:

```text
T3-P-5606;T3-P-5604;T3-P-5589;T3-P-5605;T3-P-4895;T3-P-4897;T3-P-4907;T3-P-4899;T3-P-4902;T3-P-4904;T3-P-4904;T3-P-4902;T3-P-4892;T3-P-4891;T3-P-4892;T3-P-4893
```

Inside/outside relation distribution:

- `INSIDE_BODY=122`
- `OUTSIDE_ATTACHMENT=82`
- `MAIN_WALL=16`
- `BOUNDARY_OR_THROUGH=8`

Station topology distribution:

- `CLOSED_WITH_CAVITY=77`
- `CLOSED_WITHOUT_CAVITY=12`
- `BODY_CORE=89`

### T3-5GKZ-10 Regression

Output: `outputs\T3-5GKZ-10-contract-audit-20260624`.

- File count: `23`.
- Has `box-part-spatial-relations.json/csv`: yes.
- Has `box-station-topology-diagnostics.json/csv`: yes.
- Confirmed main wall Tekla entities: `16`.
- Confirmed unique main wall positions: `13`.
- Confirmed main wall positions include `T3-P-4918` and exclude `T3-P-4916`.

Inside/outside relation distribution:

- `OUTSIDE_ATTACHMENT=75`
- `INSIDE_BODY=150`
- `MAIN_WALL=16`
- `BOUNDARY_OR_THROUGH=18`

Station topology distribution:

- `CLOSED_WITH_CAVITY=101`
- `CLOSED_WITHOUT_CAVITY=47`
- `END_TRANSITION_NOT_BODY_CORE=4`
- `BODY_CORE=148`
- `END_TRANSITION_OR_ATTACHMENT_TRIGGERED=4`

## Conclusion

The new export contract is now connected across the project:

- data contract documented;
- main wall expansion consumes new candidate role vocabulary;
- inside/outside relation consumes exported topology;
- station topology diagnostics are generated, flattened, printed, and summarized;
- tests cover pipeline and report outputs;
- new and regression caches both produce complete report sets.

No part number, member id, or project-specific hardcoded rule was added.

## Follow-up Migration Audit - 2026-06-24 v2

User clarified this audit is not only about BOX main wall detection. The project must keep equivalent behavior after the exporter moved from older `member.Samples/SectionParts/SectionFeatures/PartRoles` assumptions to the new assembly-level evidence contract.

Additional old-contract dependency findings:

1. `box_main_material_segments.py` still used `member.Samples[].SectionParts` as the only section seed path. If a future new export keeps `metadata.boxSectionEvidence` but drops old member samples, BOX main wall confirmation would fall back to radial/bodyFace buckets. Fix: added a new `boxSectionEvidence.stationLoops[].partLoops[].sectionLoops/segments` seed path, with old `Samples` retained only as fallback.
2. The first topology seed attempt was too broad: station outer shell can include large short transition/end/attachment loops. Fix: topology seed now filters to long-axis wall candidates before outer-shell extraction, using station coverage and `sectionProjectionEvidence.normalProjectionMagnitude` as feature evidence, not part-number rules.
3. `spatial_features.py` used `Classification.PartRoles` to define body ids for appendage clusters. New offline pipeline now passes the confirmed BOX main wall ids from `classify_main_material_segment_groups` into appendage clustering. Old `PartRoles` and `mainPartId` remain fallback only.
4. Earlier migration fixes remain in force: station topology diagnostics consume `sectionLoops` first, then `segments`, then old `points`; manufacturing scope station continuity prefers `mainMaterialEvidence.axisStationStart/End` before old centroid/plateLongDirection estimation.

Regression tests added:

- `test_uses_box_section_evidence_loops_as_main_wall_seed_without_member_samples`
- `test_box_section_topology_seed_ignores_short_transition_loops_even_when_large`
- `test_bundle_cluster_uses_confirmed_body_ids_when_old_member_roles_are_missing`
- Existing manufacturing scope and station topology diagnostics tests cover exported station ranges and segment-only topology.

## Verification Commands - v2

```powershell
python -m unittest tests.test_spatial_features tests.test_box_main_material_segments
python -m unittest tests.test_pipeline_offline tests.test_reports_offline tests.test_box_part_spatial_relations tests.test_box_station_topology_diagnostics tests.test_manufacturing_scope tests.test_main_material_segments
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_150131 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-2 --out outputs\selected-T3-5GKZ-2-contract-migration-audit-20260624-v3
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_144128 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\T3-5GKZ-10-contract-migration-audit-20260624-v3
```

Results:

- Targeted spatial + BOX main wall tests: `18 tests OK`.
- Targeted pipeline/report/topology/manufacturing tests: `23 tests OK`.
- Full test suite: `83 tests OK`. `openpyxl` still emits the existing `datetime.utcnow()` deprecation warning.
- Both smoke commands wrote 23 report files, including box main material, box part spatial relations, and station topology diagnostics JSON/CSV.

## Smoke Results - v3

### T3-5GKZ-2

Output: `outputs\selected-T3-5GKZ-2-contract-migration-audit-20260624-v3`.

- Confirmed main wall group: `BOX_MAIN_WALL_CONFIRMED_SET`.
- Main wall Tekla entities: `16`.
- Unique main wall positions: `13`.
- User-called examples remain included: `T3-P-4897`, `T3-P-4895`, `T3-P-4907`, `T3-P-4899`.
- Position list:

```text
T3-P-5606;T3-P-5604;T3-P-5589;T3-P-5605;T3-P-4895;T3-P-4897;T3-P-4907;T3-P-4899;T3-P-4902;T3-P-4904;T3-P-4904;T3-P-4902;T3-P-4892;T3-P-4891;T3-P-4892;T3-P-4893
```

Inside/outside relation distribution:

- `INSIDE_BODY=122`
- `OUTSIDE_ATTACHMENT=82`
- `MAIN_WALL=16`
- `BOUNDARY_OR_THROUGH=8`

Station topology distribution:

- `CLOSED_WITH_CAVITY=77`
- `CLOSED_WITHOUT_CAVITY=12`
- `BODY_CORE=89`

Appendage cluster role distribution after confirmed body ids are passed into clustering:

- `Bracket=3`
- `Unknown=22`

### T3-5GKZ-10 Regression

Output: `outputs\T3-5GKZ-10-contract-migration-audit-20260624-v3`.

- Confirmed main wall group: `BOX_MAIN_WALL_CONFIRMED_SET`.
- Main wall Tekla entities: `16`.
- Unique main wall positions: `13`.
- Expected corrected main wall set: missing `[]`, extra `[]`.
- `T3-P-4918` included; `T3-P-4916` excluded.
- The broad topology seed regression was reproduced once in `v2` output, then fixed before this final `v3` smoke. The fix is feature-based: long-axis wall candidate filter + normal projection filter, no part-number special cases.

Inside/outside relation distribution:

- `INSIDE_BODY=150`
- `OUTSIDE_ATTACHMENT=75`
- `BOUNDARY_OR_THROUGH=18`
- `MAIN_WALL=16`

Station topology distribution:

- `CLOSED_WITH_CAVITY=101`
- `CLOSED_WITHOUT_CAVITY=47`
- `END_TRANSITION_NOT_BODY_CORE=4`
- `BODY_CORE=148`
- `END_TRANSITION_OR_ATTACHMENT_TRIGGERED=4`

Appendage cluster role distribution after confirmed body ids are passed into clustering:

- `Bracket=2`
- `Unknown=13`

## Updated Contract-Migration Decision

The project now treats the new exporter contract as the primary evidence source where it changes behavior:

1. BOX main wall seed: `metadata.boxSectionEvidence.stationLoops[].partLoops[].sectionLoops/segments` -> old `member.Samples` fallback -> old face/station fallback.
2. BOX inside/outside: exported station topology loops -> exported segments polygonize -> old point fallback -> projected bounds fallback only when topology is absent.
3. Station diagnostics: exported section loops -> exported segments polygonize -> old point fallback, with BODY vs end-transition station scope.
4. Manufacturing station continuity: exported `mainMaterialEvidence.axisStationStart/End` -> old centroid/plateLongDirection estimate.
5. Appendage clustering body boundary: confirmed main wall ids from new main-material classifier -> old `Classification.PartRoles` -> `mainPartId` fallback.

The audit intentionally keeps old fields as compatibility fallbacks. They are no longer the only path for the affected modules.