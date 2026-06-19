# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Builds a clean course GPX from raw activity traces: simplify source GPX → clip local OSM to the activity area → match traces to real OSM ways (OSRM + Overpass) → filter noisy matched points → generate optimized trip route geometry → export final GPX route(s).

## Commands

- `make install` — create venv, install `requirements.txt`
- `make test` — `unittest discover -s tests -p "test_*.py"`; run a single test with `.venv/bin/python -m unittest tests.test_trip.TestTrip.test_name`
- `make country` — one-time download of the country OSM PBF (`OSM_URL` in Makefile)
- `make parse GPX_DIR=/path/to/gpx` — runs `compress → extract → boundary → osmextract`
- `make docker` — starts colima (if not already running) and brings up OSRM + Overpass via compose; detects whether colima's active runtime is `docker` or `containerd` and dispatches to `docker compose` or `colima nerdctl -- compose` accordingly
- `make course NAME="Ba Vi"` — runs `match → filter → trip → gpx`
- `make clean-data` / `make clean-data-gpx` — clear `data/` (all generated files, or just `*.gpx`)

Full end-to-end sequence and prerequisites (`gpsbabel`, `osmconvert`, `osmium`, `wget`, `bzip2`, `colima`) are in README.md.

## Architecture

Each pipeline stage is a standalone script in `scripts/`, wired together by Makefile targets, communicating via files in `data/` (CSV/GPX/poly/jpeg) rather than function calls. There's no orchestration layer — the Makefile *is* the pipeline DAG (`parse` and `course` are the two composite targets).

Stage flow and contracts:
1. `compress.py` / `extract.py` — read raw GPX dir → `data/gpx_compressed`, flattened `data/gpx.csv` (lat/lon points)
2. `boundary.py` — convex hull of points in metric CRS + 100m buffer → `data/boundary.poly`
3. `osmextract` (Makefile target, no script) — `osmconvert` clips the country PBF to the boundary, `osmium` converts to `.osm`, `bzip2` compresses for Overpass → `osm/foot/gpx.osm.pbf`, `osm/overpass-api/gpx.osm.bz2`
4. `docker` target — starts OSRM (serving the clipped PBF) and Overpass (serving the bz2 dump) containers per `docker-compose.yaml`
5. `match.py` — OSRM `/match/v1/foot` + `/nearest/v1/foot`, then Overpass for way IDs → `data/osm-gpx.csv` (lat, lon, ways)
6. `filter.py` — greedy farthest-point-first selection enforcing minimum spacing (`--distance-meters`, default 100m), optional `--max-points` / `--center-mode` → `data/filtered-osm-gpx.csv`
7. `trip.py` — OSRM `/trip/v1/foot`; on `NoTrips` recursively splits into chunks, uses exact optimization for small chunk counts and greedy merge for larger ones, falls back to bounded downsampling or passthrough geometry for unsolvable tiny chunks → `data/trip.csv` (with `route_id`)
8. `gpx.py` — trip CSV → GPX; single route writes the requested path, multiple routes write `data/trip-route-NN.gpx`

`plot.py` / `plotgpx.py` are side-effect visualization helpers invoked after several stages (not part of the data dependency chain) — they render CartoDB Positron basemaps to `data/*.jpeg`.

OSRM and Overpass are reached over HTTP from the Python scripts (ports 6000 and 18080 respectively, per `docker-compose.yaml`) — they are not Python dependencies, so a script's correctness depends on the container being up via `make docker`.
