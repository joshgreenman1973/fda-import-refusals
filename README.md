# Refused at the border

Every shipment the U.S. Food and Drug Administration turned away at the border since 2002 —
525,457 refused entry lines from 207 countries — searchable by country, firm, product and the
statutory charge that stopped it.

The charge language is quoted verbatim from FDA's own crosswalk. The most-used food charge,
code 249, reads in part: the article "appears to consist in whole or in part of a filthy, putrid,
or decomposed substance." It has been used 39,779 times.

## Data

- Refusals: FDA Data Dashboard API, `https://api-datadashboard.fda.gov/v1/import_refusals`
  (free authorization key required; not stored here)
- Charge text: [ACT_SECTION_CHARGES.CSV](https://datadashboard.fda.gov/oii/download/ACT_SECTION_CHARGES.CSV)

## Rebuild

```
export FDA_USER="you@example.com" FDA_KEY="..."
python3 fetch_fda.py 2002-01 2026-08 fda_refusals.jsonl
python3 build_fda.py
```

`build_fda.py` writes `out_fda/`; copy those files to `data/`. FDA updates the report monthly.

See [methodology.html](methodology.html) for scope, counting rules and limits.
