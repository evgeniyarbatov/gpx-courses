# scripts/plotgpx.py

## What it does
Plots multiple GPX tracks on a basemap, coloring each file separately, and saves the visualization.

## Arguments
1) `gpx_dir` - directory containing `.gpx` files to plot.
2) `title` - plot title.
3) `gpx_plot_filename` - output image path.

## Output
Basemap image with lines for every track/segment found. Each GPX file gets a distinct color and legend entry. Ticks are removed; aspect is equal.

## Dependencies
- gpxpy
- geopandas
- shapely
- matplotlib
- contextily

## Example
```bash
python scripts/plotgpx.py data/gpx_compressed "Original GPX" data/original-gpx.jpeg
```

## Notes
- Tracks are converted to `LineString` geometries; segments with fewer than two points are skipped.
- Coordinates are reprojected to EPSG:3857 for plotting tiles, so unusual CRS GPX files should be reprojected beforehand.
- Relies on CartoDB Positron tiles via `contextily`.
