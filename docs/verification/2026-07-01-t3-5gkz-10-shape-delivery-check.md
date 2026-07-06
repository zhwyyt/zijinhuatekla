# T3-5GKZ-10 Shape And Delivery Check - 2026-07-01

## Scope

- Member: `T3-5GKZ-10`
- Excel truth: `I:\zijinhuatekla\T3楼五节柱零构件清单(1).xls`, sheet `Θ零件清单Θ`
- Tekla export used for this check: `I:\zijinhuatekla\cache\20260624_165835`
- Output directory: `outputs\T3-5GKZ-10-shape-delivery-check-20260701`

Note: no `T3-5GKZ-10` member export newer than `20260624_165835` was found under `I:\zijinhuatekla\cache` or `I:\xingcaisuanfa\cache` during this check. The Excel file timestamp was `2026-07-01 09:15:28`.

## Delivery Rule

- BOX main material and BOX inside-body parts should be delivered to `箱型中线`.
- Other parts should be delivered to `吴继伟`.
- Rows with no exact Tekla `partPosition` match were kept as unverified; no geometry-similar substitute was treated as an automatic match.

## Commands

```powershell
python -m zijinhua_tekla.cli analyze --root I:\zijinhuatekla\cache\20260624_165835 --truth-root I:\zijinhuatekla --member-id T3-5GKZ-10 --out outputs\T3-5GKZ-10-shape-delivery-check-20260701
```

Additional local extraction generated:

- `outputs\T3-5GKZ-10-shape-delivery-check-20260701\T3-5GKZ-10-shape-delivery-check-ascii.csv`
- `outputs\T3-5GKZ-10-shape-delivery-check-20260701\T3-5GKZ-10-shape-delivery-summary-ascii.json`

## Results

- Excel rows for `T3-5GKZ-10`: `62`
- Strict numbering alignment: `MATCH=35`, `DATA_MISSING=23`, `MATCH_CONFLICT=4`
- Shape check:
  - `MATCH=39`
  - `UNVERIFIED_NO_TEKLA=19`
  - `UNVERIFIED_NO_TEKLA_EMPTY_TRUTH=4`
  - `MISMATCH=0`
- Delivery check:
  - `MATCH=37`
  - `MISMATCH=2`
  - `UNVERIFIED_NO_TEKLA=23`
- BOX spatial relation entity counts:
  - `INSIDE_BODY=186`
  - `MAIN_WALL=16`
  - `OUTSIDE_ATTACHMENT=57`

## Delivery Mismatches

Both mismatches are exact `partPosition` matches and were classified as BOX inside-body parts:

| Part | Profile | Length | Qty | Excel delivery | Expected delivery | BOX relation | Evidence |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| `T3-P-4967` | `PL16*30` | `968` | `2` | `吴继伟` | `箱型中线` | `INSIDE_BODY` | `PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE`; `POINT_IN_CAVITY_LOOP`; `CONNECTED_TO_MAIN_WALL` |
| `T3-P-4968` | `PL16*30` | `936` | `2` | `吴继伟` | `箱型中线` | `INSIDE_BODY` | `PROJECTED_CENTROID_INSIDE_MAIN_WALL_ENCLOSURE`; `POINT_IN_CAVITY_LOOP`; `CONNECTED_TO_MAIN_WALL` |

## Unverified Rows

The following rows had no exact Tekla entity in the available export and were not used to confirm shape or delivery:

`T3-DB-33`, `T3-DB-48`, `T3-DB-50`, `T3-P-957`, `T3-P-3302`, `T3-P-3449`, `T3-P-4661`, `T3-P-4891`, `T3-P-4892`, `T3-P-4895`, `T3-P-4897`, `T3-P-4910`, `T3-P-4914`, `T3-P-4969`, `T3-P-5252`, `T3-P-5254`, `T3-P-5540`, `T3-P-5550`, `T3-P-5570`, `T3-P-5572`, `T3-P-5573`, `T3-PR-28`, `T3-PX-113`.

## Conclusion

For rows that could be checked against exact Tekla positions, shape classification is consistent with the Excel sheet. Delivery responsibility has two mismatches: `T3-P-4967` and `T3-P-4968` should be changed from `吴继伟` to `箱型中线` if the stated delivery rule is the acceptance criterion.
