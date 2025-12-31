# scripts/gpx.py

## What it does
Converts a CSV of points into a single-track GPX file suitable for exporting or loading into navigation apps.

## Arguments
1) `name` - GPX track name.
2) `trip_csv` - CSV with `lat,lon` columns (usually produced by `trip.py`).
3) `trip_gpx` - output GPX filepath.

## Output
A GPX file containing one track with one segment built from the CSV points. The author is set to "Evgeny Arbatov" in the metadata.

## Dependencies
- gpxpy
- pandas

## Example
```bash
python scripts/gpx.py "Soc Son" data/trip.csv data/trip.gpx
```

## Notes
- Points are written in CSV order; no additional simplification or snapping occurs here.
- The Makefile runs `gpsbabel` afterward to simplify the generated GPX (`gpx` target).
