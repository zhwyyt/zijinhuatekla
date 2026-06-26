# BOX Main Wall Axis Expansion Regression

## Context

New selected Tekla member cache: `I:\zijinhuatekla\cache\20260624_150131`, member `T3-5GKZ-2`.

The previous smoke only confirmed the first 4 section-seeded main wall plates:

- `T3-P-5606`
- `T3-P-5604`
- `T3-P-5589`
- `T3-P-5605`

User correction: these 4 are valid seed main plates, but the algorithm must continue along the member axis with double verification and identify adjacent main wall segments such as `T3-P-4897`, `T3-P-4895`, `T3-P-4907`, `T3-P-4899`.

## Root Cause

The BOX main wall trace algorithm was still present, but the expansion gate was too narrow.

`_expanded_wall_trace_group()` starts from section closed-loop seed parts and then considers axis-continuous candidate parts. Before checking station continuity, it calls `_is_unsampled_body_wall_candidate()`.

That gate only accepted:

- `member Classification.PartRoles.Role == wall_candidate`, or
- `name == COLUMN`, or
- Case Bank confirmed positions.

In the new exporter/classifier data for `T3-5GKZ-2`, the later main wall segments are exported as:

- `mainMaterialEvidence.isBodyWallPlateCandidate = true`
- station-continuous from about `3164.98` to `6015.9`
- member role `flange_candidate` / `web_candidate`

Therefore the candidates were valid main wall candidates, but were rejected before axis continuity could be evaluated. This is a FEATURE/SCORING evidence-contract mismatch, not a part-number issue.

## Fix

The expansion gate now requires exporter main-wall candidacy first, then accepts the current section role vocabulary:

- `wall_candidate`
- `flange_candidate`
- `web_candidate`

This keeps thickness/name auxiliary and preserves the double-verification flow:

1. section closed-loop seed main wall plates;
2. axis station continuity expansion;
3. section/topology evidence remains in the confirmed set evidence codes.

No member id, part position, project name, or hardcoded Tekla id was added.

## Regression Test

Added `test_expands_section_seed_to_adjacent_flange_role_wall_candidates` in `tests/test_box_main_material_segments.py`.

The test reproduces the failure mode:

- seed plates at station `0-3165` are section-sampled;
- next plates at `3164.98-6016` are `flange_candidate` / `web_candidate` and `isBodyWallPlateCandidate=true`;
- thickness changes from 16 to 30;
- an isolated far attachment-like candidate remains excluded.

Red result before fix: only seed plates returned.
Green result after fix: seed + adjacent role candidates returned.

## Verification

Commands:

```powershell
python -m unittest tests.test_box_main_material_segments
python -m unittest discover -s tests
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_150131 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-2 --out outputs\selected-T3-5GKZ-2-mainwall-expand-smoke-20260624
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_144128 --truth-root I:\xingcaisuanfa\cache\20260615_161938 --member-id T3-5GKZ-10 --out outputs\T3-5GKZ-10-mainwall-expand-regression-20260624
```

Results:

- Unit tests: `78 tests OK`.
- `T3-5GKZ-2` confirmed main wall set now has 16 Tekla entities, including `T3-P-4895`, `T3-P-4897`, `T3-P-4907`, `T3-P-4899`.
- `T3-5GKZ-2` relation distribution: `MAIN_WALL=16`, `INSIDE_BODY=122`, `OUTSIDE_ATTACHMENT=82`, `BOUNDARY_OR_THROUGH=8`.
- `T3-5GKZ-2` topology diagnostics: `CLOSED_WITH_CAVITY=77`, `CLOSED_WITHOUT_CAVITY=12`, all `BODY_CORE=89`.
- `T3-5GKZ-10` regression remains 13 unique confirmed main wall positions over 16 Tekla entities; `T3-P-4918` remains included and `T3-P-4916` remains excluded.

`T3-5GKZ-2` confirmed positions after fix:

```text
T3-P-5606;T3-P-5604;T3-P-5589;T3-P-5605;T3-P-4895;T3-P-4897;T3-P-4907;T3-P-4899;T3-P-4902;T3-P-4904;T3-P-4904;T3-P-4902;T3-P-4892;T3-P-4891;T3-P-4892;T3-P-4893
```
