# BOX Internal Cavity Geometry Fix

## Context

User review found 16 `BOUNDARY_OR_THROUGH` rows in `T3-5GKZ-8` that are visually inside the BOX main wall cavity. The fix must be pure geometry: no part-position, project name, or part-name special cases.

## Root Cause

`classify_box_part_spatial_relations` sampled each part at start/mid/end stations and selected the nearest station topology. Some sampled stations only contained a local single-wall topology (`CLOSED_WITHOUT_CAVITY`) with area far smaller than a full BOX section. Those local topologies were treated as if they represented the whole BOX body, so internal cavity parts were classified as outside at those stations and became `BOUNDARY_OR_THROUGH` by mixed station results.

## Change

When full cavity station topology exists, nearest station selection now ignores local incomplete station topologies whose outer area is less than 75% of the full cavity reference area. The relation remains geometric: it chooses a representative BOX section topology before evaluating point-in-cavity / point-in-body. It does not use part names, part numbers, or business labels.

## Verification

Commands run on 2026-06-24:

```powershell
python -m unittest tests.test_box_part_spatial_relations
python -m zijinhua_tekla.cli analyze --root cache\20260624_161006 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-8 --out outputs\T3-5GKZ-8-geometry-cavity-fix-20260624
python -m zijinhua_tekla.cli analyze --root cache\20260624_144128 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\T3-5GKZ-10-geometry-cavity-fix-20260624
python -m unittest discover -s tests
```

Results:

- `tests.test_box_part_spatial_relations`: 10 tests OK.
- Full unit suite: 84 tests OK. Existing `openpyxl` `datetime.utcnow()` deprecation warning remains unrelated.
- `T3-5GKZ-8`: relation distribution changed to `INSIDE_BODY=165`, `OUTSIDE_ATTACHMENT=58`, `MAIN_WALL=16`; `BOUNDARY_OR_THROUGH=0`.
- The 16 reviewed part ids are all now `INSIDE_BODY`: `72748651`, `72748660`, `72748685`, `72748712`, `72748730`, `72748739`, `72748748`, `72748757`, `72748910`, `72748920`, `72748930`, `72748947`, `72748963`, `72748973`, `72748983`, `72748993`.
- `T3-5GKZ-10`: relation distribution is `INSIDE_BODY=184`, `OUTSIDE_ATTACHMENT=57`, `MAIN_WALL=16`, `BOUNDARY_OR_THROUGH=2`, so real boundary cases are not globally suppressed.

## Output Files

- `outputs\T3-5GKZ-8-geometry-cavity-fix-20260624\T3-5GKZ-8-box-part-spatial-relations.csv`
- `outputs\T3-5GKZ-10-geometry-cavity-fix-20260624\T3-5GKZ-10-box-part-spatial-relations.csv`
