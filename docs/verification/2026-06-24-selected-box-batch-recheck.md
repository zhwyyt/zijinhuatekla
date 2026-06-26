# Selected BOX Batch Recheck

## Context

User selected a new batch of BOX columns in Tekla and requested a fresh export and recheck after the pure-geometry BOX internal cavity fix.

## Export

Command run on 2026-06-24:

```powershell
I:\xingcaisuanfa\TeklaSectionClassifier.Runner\bin\Debug\net48\TeklaSectionClassifier.Runner.exe --body-bracket-export --out I:\zijinhuatekla\cache\20260624_selected_box_batch_recheck
```

Exporter wrote the timestamped output directory:

- `I:\zijinhuatekla\cache\20260624_165835`
- Bundle: `I:\zijinhuatekla\cache\20260624_165835\tekla-body-bracket-export.bundle.json`
- Member JSON directory: `I:\zijinhuatekla\cache\20260624_165835\members`

Exporter result:

- `MemberCount=16`
- `PartCount=3914`
- Members: `T3-5GKZ-1` through `T3-5GKZ-16`

## Analysis

Commands run:

```powershell
python -m zijinhua_tekla.cli analyze --root cache\20260624_165835 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-8 --out outputs\selected-box-batch-recheck-20260624\T3-5GKZ-8
```

Then all 16 members were analyzed into:

- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-1`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-2`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-3`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-4`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-5`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-6`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-7`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-8`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-9`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-10`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-11`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-12`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-13`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-14`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-15`
- `outputs\selected-box-batch-recheck-20260624\T3-5GKZ-16`

All 16 CLI runs exited with code 0.

## BOX Spatial Relation Summary

All 16 members produced exactly one `BOX_MAIN_WALL_CONFIRMED_SET` group.

Members with no `BOUNDARY_OR_THROUGH` rows:

- `T3-5GKZ-1`
- `T3-5GKZ-2`
- `T3-5GKZ-3`
- `T3-5GKZ-4`
- `T3-5GKZ-6`
- `T3-5GKZ-8`
- `T3-5GKZ-11`
- `T3-5GKZ-12`
- `T3-5GKZ-13`
- `T3-5GKZ-14`
- `T3-5GKZ-15`
- `T3-5GKZ-16`

Residual `BOUNDARY_OR_THROUGH` rows:

| Member | Part position | Part id | Station range | Section relation | Evidence |
| --- | --- | --- | --- | --- | --- |
| `T3-5GKZ-5` | `T3-P-4896` | `71773268` | `9342.1-10472.3` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |
| `T3-5GKZ-5` | `T3-P-4916` | `72800071` | `9560.7-9971.8` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |
| `T3-5GKZ-7` | `T3-P-3449` | `72793950` | `9560.7-9971.8` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |
| `T3-5GKZ-9` | `T3-P-3449` | `72780856` | `9560.7-9971.8` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |
| `T3-5GKZ-10` | `T3-P-4896` | `72805785` | `9342.1-10472.4` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |
| `T3-5GKZ-10` | `T3-P-4916` | `72806770` | `9560.6-9971.8` | `projected_centroid_mixed_across_station_loops` | `PROJECTED_CENTROID_MIXED_ACROSS_STATION_LOOPS` |

These 6 rows are not the same failure mode as the previously reviewed 16 obvious internal cavity rows in `T3-5GKZ-8`. They are concentrated around station `9342-10472` / `9560-9972`, connect to a single main wall plate, and the evidence is mixed results across nearby station loops.

## Topology Notes

For the 4 members with residual boundary rows, the relevant station bands include valid full cavity topology and nearby partial/transition topology:

- `T3-5GKZ-5`: in `9305-10488`, early stations include `CLOSED_WITHOUT_CAVITY`, middle body stations are `CLOSED_WITH_CAVITY`, and later stations become `END_TRANSITION_NOT_BODY_CORE`.
- `T3-5GKZ-7`: around `9522-10005`, sampled stations are `BODY_CORE / CLOSED_WITH_CAVITY`.
- `T3-5GKZ-9`: around `9522-10005`, sampled stations are `BODY_CORE / CLOSED_WITH_CAVITY`.
- `T3-5GKZ-10`: in `9305-10488`, early stations include `CLOSED_WITHOUT_CAVITY`, middle body stations are `CLOSED_WITH_CAVITY`, and later stations become `END_TRANSITION_NOT_BODY_CORE`.

The remaining 6 rows should therefore stay as review candidates until there is stronger geometry evidence for a deterministic inside/outside decision. They should not be globally forced to `INSIDE_BODY` by suppressing `BOUNDARY_OR_THROUGH`.

## Conclusion

The new selected BOX batch validates the previous pure-geometry fix for the original `T3-5GKZ-8` issue:

- `T3-5GKZ-8`: `INSIDE_BODY=165`, `OUTSIDE_ATTACHMENT=58`, `MAIN_WALL=16`, `BOUNDARY_OR_THROUGH=0`.
- Across 16 selected BOX members, 12 members have `BOUNDARY_OR_THROUGH=0`.
- The only residual `BOUNDARY_OR_THROUGH` rows are 6 repeatable mixed-station-loop candidates in 4 members.

No code change was made in this recheck.
## Follow-up: Inner-Wall Station Mix Fix

User confirmed `T3-5GKZ-10 / T3-P-4916` is a part tight against the inner wall, and asked whether the other residual rows are similar. A direct geometry recheck showed the 6 residual rows are all inside/inner-wall cases, not outside attachments:

| Member | Part position | Profile | Geometry result |
| --- | --- | --- | --- |
| `T3-5GKZ-5` | `T3-P-4896` | `PL16*200` | inner-wall / cavity-side |
| `T3-5GKZ-5` | `T3-P-4916` | `PL30*100` | tight against inner wall |
| `T3-5GKZ-7` | `T3-P-3449` | `PL30*100` | tight against inner wall |
| `T3-5GKZ-9` | `T3-P-3449` | `PL30*100` | tight against inner wall |
| `T3-5GKZ-10` | `T3-P-4896` | `PL16*200` | inner-wall / cavity-side |
| `T3-5GKZ-10` | `T3-P-4916` | `PL30*100` | tight against inner wall |

The fix is pure geometry: station relation mixes containing only `inside`, `cavity`, and `boundary` are now treated as internal. Mixed relations containing `outside` still remain `BOUNDARY_OR_THROUGH`.

Regression test added:

```powershell
python -m unittest tests.test_box_part_spatial_relations
```

TDD red/green evidence:

- Before the code change, `test_treats_inside_and_cavity_station_mix_as_inside_body` failed because `A-P-tight-inner` was classified as `BOUNDARY_OR_THROUGH` instead of `INSIDE_BODY`.
- After the code change, `tests.test_box_part_spatial_relations` passed: 11 tests OK.

Selected BOX batch recheck after the fix:

```powershell
python -m zijinhua_tekla.cli analyze --root cache\20260624_165835 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id <T3-5GKZ-1..16> --out outputs\selected-box-batch-recheck-20260624-after-inner-wall-fix\<member>
```

Result across all 16 selected BOX members:

- `BOUNDARY_OR_THROUGH=0`
- `INSIDE_BODY=2692`
- `OUTSIDE_ATTACHMENT=966`
- `MAIN_WALL=256`

The 6 reviewed rows all became `INSIDE_BODY` with evidence `POINT_IN_CAVITY_LOOP` and `CONNECTED_TO_MAIN_WALL`.

Full verification:

```powershell
python -m unittest discover -s tests
```

Result: 85 tests OK. Existing `openpyxl` `datetime.utcnow()` deprecation warning remains unrelated.
