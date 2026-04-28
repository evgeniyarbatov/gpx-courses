# scripts/match.py

## What it does
Map-matches consecutive GPS points against a local OSRM foot profile, then queries Overpass to retrieve OSM way IDs for the matched nodes. Produces a CSV of snapped points plus the associated ways.

## Services/Dependencies
- OSRM backend running on `http://localhost:6000` (see `docker-compose.yaml`, port 6000 maps to the container's 5000).
- Overpass API running on `http://localhost:18080` with the clipped dataset produced by `osmextract`.
- pandas, requests.

## Arguments
1) `csv_file` - input CSV with `lat,lon` columns (typically `data/gpx.csv`).
2) `matched_csv_file` - output CSV path.

## Output
CSV columns:
- `lat`, `lon` - snapped coordinates returned by OSRM match.
- `ways` - list of OSM way IDs intersecting the nearest nodes (deduplicated by coordinate).

## Example
```bash
python scripts/match.py data/gpx.csv data/osm-gpx.csv
```

## Notes
- Each adjacent pair of points is sent to OSRM `match` with a 20 m radius per point (`MATCH_RADIUS_METERS`).
- Overpass endpoint defaults to `http://localhost:18080/api/interpreter`; override with `OVERPASS_API_URL` if needed.
- When OSRM returns multiple tracepoints, each is enriched with way IDs from Overpass; entries with no ways are skipped.
- Output rows are deduplicated on `lat,lon` before writing.
- Ensure OSRM/Overpass containers are running (`make docker`) and that `osmextract` has generated `osm/gpx.osm` and the Overpass database before matching.
