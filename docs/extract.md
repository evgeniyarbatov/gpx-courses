# scripts/extract.py

## What it does
Parses every `.gpx` file in a directory and flattens all track points into a single CSV of latitude/longitude pairs.

## Arguments
1) `gpx_dir` - directory containing one or more `.gpx` files.
2) `csv_file` - output CSV path.

## Output
CSV with columns `lat,lon` (one row per point in input order across files).

## Dependencies
- gpxpy
- pandas

## Example
```bash
python scripts/extract.py data/gpx_compressed data/gpx.csv
```

## Notes
- Files ending with `.gpx` are processed; others are ignored.
- All tracks/segments inside each GPX are traversed; no deduplication or simplification occurs here.
- In the Makefile this runs after optional GPX simplification (`compress` target).
