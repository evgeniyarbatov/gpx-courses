# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
VENV_PATH := .venv

GPX_DIR ?=
NAME ?=

OSM_DIR := osm
OSM_URL := https://download.geofabrik.de/asia/vietnam-latest.osm.pbf
include $(HOME)/gitRepo/dotfiles/make/osm-country.mk

.PHONY: \
	install lock test \
	clean clean-data clean-data-gpx \
	gpx-input-check \
	plotgpx compress extract boundary country osmextract docker docker-stop match filter trip gpx parse course help

install:
	@uv sync

lock:
	@uv lock

test: install
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

clean: clean-data

clean-data:
	@find data -mindepth 1 ! -name ".gitignore" -delete
	@echo "Cleaned data directory (preserved data/.gitignore)."

clean-data-gpx:
	@find data -type f -name "*.gpx" -delete

gpx-input-check:
	@test -n "$(strip $(GPX_DIR))" || (echo "Error: GPX_DIR is required. Example: make parse GPX_DIR=/path/to/gpx-dir" >&2; exit 1)
	@test -d "$(GPX_DIR)" || (echo "Error: GPX_DIR does not exist: $(GPX_DIR)" >&2; exit 1)

plotgpx: install gpx-input-check
	@uv run python scripts/plotgpx.py \
	$(GPX_DIR) \
	"Original GPX" \
	data/original-gpx.jpeg

compress: install gpx-input-check clean-data-gpx
	@uv run python scripts/compress.py "$(GPX_DIR)"

extract: install
	@uv run python scripts/extract.py
	@uv run python scripts/plotgpx.py \
	data/gpx_compressed \
	"Simplified GPX" \
	data/simplified-gpx.jpeg

boundary: install
	@uv run python scripts/boundary.py

osmextract:
	@mkdir -p $(OSM_DIR)/foot $(OSM_DIR)/overpass-api
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=data/boundary.poly -o=$(OSM_DIR)/foot/gpx.osm.pbf
	@osmium cat --overwrite $(OSM_DIR)/foot/gpx.osm.pbf -o $(OSM_DIR)/gpx.osm
	@bzip2 -c $(OSM_DIR)/gpx.osm > $(OSM_DIR)/overpass-api/gpx.osm.bz2

docker:
	@colima status >/dev/null 2>&1 || colima start
	@runtime=$$(colima status -j | python3 -c "import json,sys; print(json.load(sys.stdin)['runtime'])"); \
	if [ "$$runtime" = "docker" ]; then \
		docker compose down --remove-orphans || true; \
		docker compose up --build -d; \
	else \
		colima nerdctl -- compose down --remove-orphans || true; \
		colima nerdctl -- compose up --build -d; \
	fi

docker-stop:
	@colima status >/dev/null 2>&1 || exit 0
	@runtime=$$(colima status -j | python3 -c "import json,sys; print(json.load(sys.stdin)['runtime'])"); \
	if [ "$$runtime" = "docker" ]; then \
		docker compose down --remove-orphans; \
	else \
		colima nerdctl -- compose down --remove-orphans; \
	fi

match: install
	@echo "Matching..."
	@uv run python scripts/match.py
	@uv run python scripts/plot.py \
	data/osm-gpx.csv \
	"OSRM-Matched Points with OSM Way IDs" \
	data/osm-match.jpeg

filter: install
	@echo "Filtering..."
	@uv run python scripts/filter.py
	@uv run python scripts/plot.py \
	data/filtered-osm-gpx.csv \
	"Center-Distance Filtered Match Points" \
	data/osm-filter.jpeg

trip: install
	@echo "Making trip..."
	@uv run python scripts/trip.py
	@uv run python scripts/plot.py \
	data/trip.csv \
	"OSRM Trip Route (CSV Output)" \
	data/trip-gpx.jpeg

gpx: install
	@test -n "$(strip $(NAME))" || (echo "Error: NAME is required. Example: make gpx NAME=\"Soc Son\"" >&2; exit 1)
	@echo "Writing GPX..."
	@uv run python scripts/gpx.py "$(NAME)"
	@if ls data/trip-route-*.gpx >/dev/null 2>&1; then \
		for file in data/trip-route-*.gpx; do \
			gpsbabel -i gpx -f "$$file" \
			-x simplify,crosstrack,error=0.01k \
			-o gpx -F "data/simplified-$$(basename $$file)"; \
		done; \
	else \
		gpsbabel -i gpx -f data/trip.gpx \
		-x simplify,crosstrack,error=0.01k \
		-o gpx -F data/simplified-trip.gpx; \
	fi
	@if ls data/trip-route-*.gpx >/dev/null 2>&1; then \
		uv run python scripts/plotgpx.py "data/trip-route-*.gpx" "Generated Trip GPX Routes" data/trip-gpx.jpeg; \
	else \
		uv run python scripts/plotgpx.py "data/trip.gpx" "Generated Trip GPX Routes" data/trip-gpx.jpeg; \
	fi

parse: compress extract boundary osmextract
	@echo "Parsing complete."

course: match filter trip gpx
	@echo "Course route complete."

help:
	@echo "install         - uv sync deps"
	@echo "lock            - refresh uv.lock"
	@echo "test            - run unit tests"
	@echo "clean/clean-data - clear data/ directory"
	@echo "clean-data-gpx  - clear *.gpx files in data/"
	@echo "country         - one-time download of country OSM PBF"
	@echo "plotgpx GPX_DIR=... - plot original GPX"
	@echo "compress GPX_DIR=... - compress GPX files"
	@echo "extract         - extract flattened GPX points"
	@echo "boundary        - compute boundary polygon"
	@echo "osmextract      - clip country OSM to boundary"
	@echo "docker/docker-stop - start/stop OSRM + Overpass containers"
	@echo "match/filter/trip/gpx - course pipeline stages"
	@echo "parse           - compress + extract + boundary + osmextract"
	@echo "course NAME=... - match + filter + trip + gpx"
