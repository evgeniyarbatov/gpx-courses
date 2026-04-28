# gpx-courses

Create a single route/course from multiple GPX files by:
1) extracting and simplifying source traces,
2) clipping local OSM data to the activity area,
3) snapping points to real OSM ways via OSRM + Overpass,
4) thinning noisy points,
5) building an optimized trip path,
6) exporting final GPX.

## Overall design

### Inputs
- One or more source GPX files in `GPX_DIR`.
- Country-level OSM PBF (downloaded once by `make country`).

### Core components
- Python scripts in `scripts/` handle data preparation, matching, filtering, and export.
- `osmconvert` + `osmium` clip OSM to the GPX boundary.
- OSRM (foot profile) provides `nearest`, `match`, and `trip` APIs.
- Overpass runs on the clipped dataset to map matched nodes back to OSM way IDs.

### Data flow
1) GPX files are optionally simplified (`make compress` via `gpsbabel`).
2) `scripts/extract.py` flattens all GPX points into `data/gpx.csv`.
3) `scripts/boundary.py` builds `data/boundary.poly` from those points.
4) `make osmextract` clips OSM to boundary and prepares Overpass input.
5) `make docker` starts local OSRM + Overpass services.
6) `scripts/match.py` snaps points to OSM and stores matched points/ways in `data/osm-gpx.csv`.
7) `scripts/filter.py` keeps shape-defining points (furthest from route center first) and removes near-duplicates into `data/filtered-osm-gpx.csv`.
8) `scripts/trip.py` requests OSRM trip optimization, recursively splits unsolved point sets on `NoTrips`, then runs chunk-set optimization to minimize route count; unsplittable tiny chunks use passthrough geometry only as last fallback, and output is written with `route_id` to `data/trip.csv`.
9) `scripts/gpx.py` converts route CSV to GPX. It writes one GPX when a single route is solvable, or multiple `data/trip-route-*.gpx` files when splitting is required.

## End-to-end workflow
1) Create and populate virtualenv: `make install`
2) Download country PBF once: `make country`
3) Parse source GPX and clip OSM data:
   - `make parse GPX_DIR=/Users/zhenya/Downloads/aleksey-trip NAME="Soc Son"`
4) Start OSRM + Overpass: `make docker`
5) Build final course: `make course`
   - Optional filter tuning: `make filter FILTER_DISTANCE_METERS=80 FILTER_MAX_POINTS=500 FILTER_CENTER_MODE=median`
6) Optional visualization: `make plotgpx`

## Script steps

### `scripts/extract.py`
1) Iterate files in the input directory and keep `*.gpx`.
2) Parse each GPX with `gpxpy`.
3) Traverse every track -> segment -> point.
4) Collect `lat`/`lon` rows.
5) Write a single CSV output.

### `scripts/boundary.py`
1) Load point CSV (`lat`, `lon`) into GeoDataFrame (EPSG:4326).
2) Reproject to EPSG:3857 so distance-based operations are in meters.
3) Build convex hull of all points.
4) Apply fixed 100 m buffer to hull.
5) Reproject buffered polygon back to EPSG:4326.
6) Write polygon coordinates to `.poly` format (`boundary` ... `END`).

### `scripts/ways.py`
1) Parse OSM file with `osmium.SimpleHandler`.
2) Store all node IDs -> `(lat, lon)` coordinates.
3) Store all way IDs -> ordered node ID lists.
4) Materialize each way as `way_id` + resolved node coordinates.
5) Write result CSV.

### `scripts/match.py`
1) Read input CSV points.
2) For each adjacent point pair:
3) Call OSRM `/match/v1/foot` with 20 m radiuses.
4) For each returned tracepoint, call OSRM `/nearest/v1/foot` to get nearby node IDs.
5) Query Overpass (`way(bn)`) for way IDs using those nodes.
6) Keep matched points that have non-empty way lists.
7) Drop duplicate coordinates and write CSV (`lat`, `lon`, `ways`).

### `scripts/filter.py`
1) Read matched point CSV.
2) Compute route center (`median` by default, `mean` optional).
3) Rank points by distance from center (furthest first).
4) Keep ranked points while enforcing minimum spacing (`100 m` default).
5) Optionally cap retained points via `--max-points`.
6) Re-sort kept points to original input order and write filtered CSV.

### `scripts/trip.py`
1) Read filtered point CSV.
2) Build OSRM `/trip/v1/foot` coordinate string (`lon,lat;...`).
3) Request full overview polyline (`polyline6`).
4) If OSRM returns `NoTrips`, split points into two spatial chunks and retry per chunk.
5) Optimize chunk grouping (exact search for practical chunk counts) to minimize final route count when OSRM can solve combined chunks.
6) Apply bounded fallback downsampling only for tiny chunks that cannot be split further.
7) If OSRM still cannot solve a tiny chunk, emit passthrough geometry for that chunk so coverage is preserved.
8) Validate response status and payload (`code=Ok`, trip exists, geometry exists).
9) Decode polyline geometry to `(lat, lon)` sequence.
10) Write route CSV with `route_id`.

### `scripts/gpx.py`
1) Read route CSV.
2) Create GPX document with metadata (`name`, fixed author).
3) Group by `route_id` when present.
4) Append each CSV point as a GPX track point.
5) Serialize one GPX (`trip.gpx`) or multiple split GPX files (`trip-route-*.gpx`).

### `scripts/plot.py`
1) Read CSV points.
2) Scatter points on a Matplotlib axis.
3) Add CartoDB Positron basemap via `contextily`.
4) Auto-fit extent to point bounds and hide ticks.
5) Save image.

### `scripts/plotgpx.py`
1) Collect all GPX files in a directory.
2) Parse each file and build `LineString` geometries per segment.
3) Create per-file colored GeoDataFrames.
4) Reproject to EPSG:3857 and plot on shared axis.
5) Add basemap + legend and save image.

## Script docs
- [scripts/boundary.py](docs/boundary.md)
- [scripts/extract.py](docs/extract.md)
- [scripts/filter.py](docs/filter.md)
- [scripts/gpx.py](docs/gpx.md)
- [scripts/match.py](docs/match.md)
- [scripts/plot.py](docs/plot.md)
- [scripts/plotgpx.py](docs/plotgpx.md)
- [scripts/trip.py](docs/trip.md)
- [scripts/ways.py](docs/ways.md)
