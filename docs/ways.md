# scripts/ways.py

## What it does
Extracts node coordinates and way node lists from an OSM PBF/XML file and writes them to CSV. Used to inspect the clipped dataset before matching.

## Arguments
1) `osm_filename` - input OSM file (e.g., `osm/gpx.osm`).
2) `osm_ways_filename` - output CSV path.

## Output
CSV columns:
- `way_id` - OSM way identifier.
- `nodes` - list of `(lat, lon)` tuples for the way's nodes (only nodes present in the file are kept).

## Dependencies
- osmium
- pandas

## Example
```bash
python scripts/ways.py osm/gpx.osm data/osm-ways.csv
```

## Notes
- The handler stores all nodes in memory; for very large extracts, consider streaming or filtering tags.
- Typically invoked by the `osmextract` Make target after clipping the country PBF and before starting OSRM/Overpass containers.
