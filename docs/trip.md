# scripts/trip.py

## What it does
Requests an optimized walking route (OSRM `trip` service) for a sequence of points and exports the returned geometry to CSV.

## Services/Dependencies
- OSRM backend running on `http://localhost:6000` with the prepared `gpx.osrm` dataset.
- pandas, requests, polyline.

## Arguments
1) `gpx_csv_file` - CSV with `lat,lon` columns (typically filtered points).
2) `trip_csv_file` - output CSV path.

## Output
CSV with `lat,lon` representing the decoded polyline of the computed trip (`overview=full`).

## Example
```bash
python scripts/trip.py data/filtered-osm-gpx.csv data/trip.csv
```

## Notes
- If OSRM returns an error (for example `code=NoTrips`), the script exits with a clear error message and a non-zero status.
- The response is validated (`code=Ok`, non-empty `trips`, and `geometry` present) before decoding.
- The request uses `geometries=polyline6`, `annotations=false`, `steps=false` for compact responses.
- Run after `filter.py` to trim noisy points before routing.
