# scripts/plot.py

## What it does
Creates a static scatter plot of points over a CartoDB Positron basemap and saves it as an image.

## Arguments
1) `input_filename` - CSV with `lat,lon` columns.
2) `title` - title placed on the plot.
3) `plot_filename` - output image path (e.g., `.jpeg`, `.png`).

## Output
Image file showing all points as red dots with axes and ticks hidden. Basemap is pulled via `contextily` using EPSG:4326 coordinates.

## Dependencies
- pandas
- matplotlib
- contextily

## Example
```bash
python scripts/plot.py data/osm-gpx.csv "OSM Match and Overpass API Filter" data/osm-match.jpeg
```

## Notes
- The script auto-scales axes to the min/max of provided coordinates.
- Requires internet access (or cached tiles) for the CartoDB basemap unless the tile source is changed.
