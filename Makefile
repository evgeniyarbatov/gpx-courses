# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
DATA_ROOT ?= $(HOME)/data
REPO_NAME := $(notdir $(CURDIR))
DATA_DIR  ?= $(DATA_ROOT)/$(REPO_NAME)

VENV_PATH := .venv

GPX_DIR ?=
NAME ?=

# Set before the dotfiles include: osm-country.mk uses OSM_DIR ?=, so this earlier assignment wins.
OSM_DIR := $(DATA_DIR)/osm
OSM_URL := https://download.geofabrik.de/asia/vietnam-latest.osm.pbf

DOTFILES_MK := $(HOME)/gitRepo/dotfiles/make/osm-country.mk

.PHONY: country osm-country-fetch

ifneq ($(wildcard $(DOTFILES_MK)),)
include $(DOTFILES_MK)
else
COUNTRY_OSM_FILE ?= $(notdir $(OSM_URL))

country osm-country-fetch:
	@echo "error: '$@' needs evgeniyarbatov/dotfiles (private helper); not found at $(DOTFILES_MK)." >&2
	@echo "Fetch manually: download $(OSM_URL) into $(OSM_DIR)/$(COUNTRY_OSM_FILE), then retry." >&2
	@exit 1
endif

.PHONY: \
	install lock test \
	clean clean-data clean-data-gpx \
	gpx-input-check \
	plotgpx compress extract boundary country osmextract docker docker-stop match filter trip gpx parse course run help

install:
	@uv sync

lock:
	@uv lock

test: install
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

clean: clean-data

clean-data:
	@[ -d "$(DATA_DIR)" ] && find $(DATA_DIR) -mindepth 1 -delete || true
	@echo "Cleaned $(DATA_DIR)."

clean-data-gpx:
	@[ -d "$(DATA_DIR)" ] && find $(DATA_DIR) -type f -name "*.gpx" -delete || true

gpx-input-check:
	@test -n "$(strip $(GPX_DIR))" || (echo "Error: GPX_DIR is required. Example: make parse GPX_DIR=/path/to/gpx-dir" >&2; exit 1)
	@test -d "$(GPX_DIR)" || (echo "Error: GPX_DIR does not exist: $(GPX_DIR)" >&2; exit 1)

plotgpx: install gpx-input-check
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/plotgpx.py \
	$(GPX_DIR) \
	"Original GPX" \
	$(DATA_DIR)/original-gpx.jpeg

compress: install gpx-input-check clean-data-gpx
	@uv run python scripts/compress.py "$(GPX_DIR)" --output-dir $(DATA_DIR)/gpx_compressed

extract: install
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/extract.py $(DATA_DIR)/gpx_compressed $(DATA_DIR)/gpx.csv
	@uv run python scripts/plotgpx.py \
	$(DATA_DIR)/gpx_compressed \
	"Simplified GPX" \
	$(DATA_DIR)/simplified-gpx.jpeg

boundary: install
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/boundary.py $(DATA_DIR)/gpx.csv $(DATA_DIR)/boundary.poly

osmextract:
	@mkdir -p $(OSM_DIR)/foot $(OSM_DIR)/overpass-api
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=$(DATA_DIR)/boundary.poly -o=$(OSM_DIR)/foot/gpx.osm.pbf
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
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/match.py $(DATA_DIR)/gpx.csv $(DATA_DIR)/osm-gpx.csv
	@uv run python scripts/plot.py \
	$(DATA_DIR)/osm-gpx.csv \
	"OSRM-Matched Points with OSM Way IDs" \
	$(DATA_DIR)/osm-match.jpeg

filter: install
	@echo "Filtering..."
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/filter.py $(DATA_DIR)/osm-gpx.csv $(DATA_DIR)/filtered-osm-gpx.csv
	@uv run python scripts/plot.py \
	$(DATA_DIR)/filtered-osm-gpx.csv \
	"Center-Distance Filtered Match Points" \
	$(DATA_DIR)/osm-filter.jpeg

trip: install
	@echo "Making trip..."
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/trip.py $(DATA_DIR)/filtered-osm-gpx.csv $(DATA_DIR)/trip.csv
	@uv run python scripts/plot.py \
	$(DATA_DIR)/trip.csv \
	"OSRM Trip Route (CSV Output)" \
	$(DATA_DIR)/trip-gpx.jpeg

gpx: install
	@test -n "$(strip $(NAME))" || (echo "Error: NAME is required. Example: make gpx NAME=\"Soc Son\"" >&2; exit 1)
	@echo "Writing GPX..."
	@mkdir -p $(DATA_DIR)
	@uv run python scripts/gpx.py "$(NAME)" $(DATA_DIR)/trip.csv $(DATA_DIR)/trip.gpx
	@if ls $(DATA_DIR)/trip-route-*.gpx >/dev/null 2>&1; then \
		for file in $(DATA_DIR)/trip-route-*.gpx; do \
			gpsbabel -i gpx -f "$$file" \
			-x simplify,crosstrack,error=0.01k \
			-o gpx -F "$(DATA_DIR)/simplified-$$(basename $$file)"; \
		done; \
	else \
		gpsbabel -i gpx -f $(DATA_DIR)/trip.gpx \
		-x simplify,crosstrack,error=0.01k \
		-o gpx -F $(DATA_DIR)/simplified-trip.gpx; \
	fi
	@if ls $(DATA_DIR)/trip-route-*.gpx >/dev/null 2>&1; then \
		uv run python scripts/plotgpx.py "$(DATA_DIR)/trip-route-*.gpx" "Generated Trip GPX Routes" $(DATA_DIR)/trip-gpx.jpeg; \
	else \
		uv run python scripts/plotgpx.py "$(DATA_DIR)/trip.gpx" "Generated Trip GPX Routes" $(DATA_DIR)/trip-gpx.jpeg; \
	fi

parse: compress extract boundary osmextract
	@echo "Parsing complete."

course: match filter trip gpx
	@echo "Course route complete."

# Entry point: full pipeline (assumes `make country` was already run once).
# Usage: make run GPX_DIR=/path/to/gpx-dir NAME="Course Name"
run: parse docker course
	@echo "Run complete."

help:
	@echo "install         - uv sync deps"
	@echo "lock            - refresh uv.lock"
	@echo "test            - run unit tests"
	@echo "clean/clean-data - clear \$$(DATA_DIR) (default: ~/data/gpx-courses)"
	@echo "clean-data-gpx  - clear *.gpx files in \$$(DATA_DIR)"
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
	@echo "run GPX_DIR=... NAME=... - entry point: parse + docker + course (after one-time 'make country')"
	@echo ""
	@echo "Generated data goes to \$$(DATA_DIR), default ~/data/gpx-courses."
	@echo "Override with DATA_ROOT=/path (keeps repo-name suffix) or DATA_DIR=/exact/path."
