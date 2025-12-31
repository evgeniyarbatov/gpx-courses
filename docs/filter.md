# scripts/filter.py

## What it does
Filters GPS points so that no kept point lies within 100 m of an earlier kept point (geodesic distance). Helps thin dense traces before routing.

## Arguments
1) `gpx_csv_file` - input CSV with `lat,lon` columns.
2) `filtered_gpx_csv_file` - output CSV path for the thinned points.

## Output
CSV with `lat,lon` for the retained points. The first point is always kept.

## Dependencies
- pandas
- geopy

## Example
```bash
python scripts/filter.py data/osm-gpx.csv data/filtered-osm-gpx.csv
```

## Notes
- Distance threshold is fixed at 100 m (`FILTER_DISTANCE_METERS`).
- Algorithm is O(n^2) over kept points; for very large traces consider refactoring to a spatial index.
- Used after OSM/OSRM matching and before requesting a trip route (see `trip.py`).
