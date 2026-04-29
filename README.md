# gpx-courses

Build a clean course GPX from raw activity traces by:
1. simplifying source GPX files,
2. clipping local OSM to the activity area,
3. matching traces to real OSM ways (OSRM + Overpass),
4. filtering noisy matched points,
5. generating optimized trip route geometry,
6. exporting one or more final GPX routes.

<p align="center">
  <img src="https://github.com/user-attachments/assets/56eea2f9-a106-4bbb-b6e4-d648704262da" width="40%" />
  <img src="https://github.com/user-attachments/assets/42aa2469-6862-480e-98a5-0f171e8b214b" width="40%" />
</p>

## Prerequisites
- Python 3 + `venv`
- `gpsbabel`
- `osmconvert`
- `osmium` CLI
- `wget`
- `bzip2`
- `colima` + `nerdctl` (for local OSRM + Overpass via `docker-compose.yaml`)

## Key Makefile variables
- `GPX_DIR` (required for `make plotgpx` and `make parse`)
- `NAME` (required for `make gpx` / `make course`)

Example override:
`make parse GPX_DIR=/Users/zhenya/Documents/gpx/bavi`

## End-to-end workflow
1. Install Python environment and dependencies:
   `make install`
2. Run tests:
   `make test`
3. Download country OSM PBF once:
   `make country`
4. Parse and prepare clipped OSM input:
   `make parse GPX_DIR=/Users/zhenya/Documents/gpx/bavi`
5. Start OSRM + Overpass services:
   `make docker`
6. Build final course GPX:
   `make course NAME="Ba Vi"`

Optional filter tuning (script-level):
`./.venv/bin/python scripts/filter.py data/osm-gpx.csv data/filtered-osm-gpx.csv --distance-meters 80 --max-points 500 --center-mode median`

## Makefile target map
- `make parse`: runs `compress -> extract -> boundary -> osmextract`
- `make course`: runs `match -> filter -> trip -> gpx`
- `make clean-data`: clears generated files under `data/` except `data/.gitignore`
- `make clean-data-gpx`: removes only generated `*.gpx` files under `data/`
- `make plotgpx`: plots raw GPX files from `GPX_DIR` into `data/original-gpx.jpeg`

## Main outputs
- `data/gpx.csv`: flattened points from compressed source GPX files
- `data/boundary.poly`: buffered convex hull used for OSM clipping
- `data/osm-gpx.csv`: matched points with OSM way IDs
- `data/filtered-osm-gpx.csv`: spacing-filtered points
- `data/trip.csv`: route geometry with `route_id`
- `data/trip.gpx` (single-route case) or `data/trip-route-*.gpx` (multi-route case)
- `data/simplified-trip.gpx` or `data/simplified-trip-route-*.gpx` (post-`gpsbabel` simplified outputs)
- plots:
  - `data/original-gpx.jpeg`
  - `data/simplified-gpx.jpeg`
  - `data/osm-match.jpeg`
  - `data/osm-filter.jpeg`
  - `data/trip-gpx.jpeg`

## Scripts

### `scripts/extract.py`
- Reads every `*.gpx` file from an input directory.
- Extracts all track point lat/lon pairs.
- Writes a single CSV.

### `scripts/boundary.py`
- Loads `lat/lon` CSV into GeoDataFrame.
- Builds convex hull in metric CRS and applies fixed 100 m buffer.
- Writes `.poly` boundary file.

### `scripts/ways.py`
- Parses local OSM with `osmium`.
- Collects way IDs and their resolved node coordinates.
- Writes ways CSV.

### `scripts/match.py`
- For each adjacent point pair, calls OSRM `/match/v1/foot`.
- Calls OSRM `/nearest/v1/foot` for matched tracepoints.
- Queries Overpass for way IDs from nearest nodes.
- Writes deduplicated matched points (`lat`, `lon`, `ways`).

### `scripts/filter.py`
- Keeps points furthest from route center first.
- Enforces minimum spacing (`--distance-meters`, default `100`).
- Supports optional caps (`--max-points`) and center mode (`--center-mode`).
- Preserves original point order in output.

### `scripts/trip.py`
- Calls OSRM `/trip/v1/foot` on filtered points.
- On `NoTrips`, recursively splits chunks.
- Uses exact chunk optimization for smaller chunk counts, greedy merge for larger ones.
- Uses bounded downsampling for unsplittable tiny chunks; if still unsolved, exports passthrough geometry for that chunk.
- Writes CSV with `route_id`.

### `scripts/gpx.py`
- Converts trip CSV to GPX track(s).
- Single route: writes the requested output path (usually `data/trip.gpx`).
- Multiple routes: writes numbered files like `data/trip-route-01.gpx`, `data/trip-route-02.gpx`, etc.

### `scripts/plot.py`
- Plots CSV points on CartoDB Positron basemap and saves image.

### `scripts/plotgpx.py`
- Accepts either a directory or a glob pattern (for example `data/trip-route-*.gpx`).
- Plots one or more GPX tracks on a shared basemap and saves image.
