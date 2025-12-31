# scripts/boundary.py

## What it does
Builds a buffered convex hull around a set of GPS points (lat/lon) and writes it in `.poly` format for `osmconvert`/`osmium` clipping.

## Arguments
1) `csv_file` - CSV with `lat` and `lon` columns in EPSG:4326.
2) `boundary_file` - output path for the `.poly` file.

## Output
A text file that starts with `boundary`, lists polygon coordinates, and ends with `END`. The polygon is the convex hull of all points buffered by 100 m, projected to EPSG:3857 for the buffer, then returned to WGS84.

## Dependencies
- pandas
- geopandas (and its GEOS/PROJ stack)

## Example
```bash
python scripts/boundary.py data/gpx.csv data/boundary.poly
```

## Notes
- Input points must have `lat`/`lon` columns; extra columns are ignored.
- The 100 m buffer is fixed in code; adjust in `boundary.py` if you need a different clip area.
- The resulting `.poly` is consumed by the `osmextract` Make target before running OSRM/Overpass containers.
