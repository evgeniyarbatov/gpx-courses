VENV_PATH := .venv

PYTHON := $(VENV_PATH)/bin/python
PIP := $(VENV_PATH)/bin/pip
REQUIREMENTS := requirements.txt

GPX_DIR := /Users/zhenya/Downloads/aleksey-trip
GPX_COMPRESSED_DIR := data/gpx_compressed
GPX_FILES := $(wildcard $(GPX_DIR)/*.gpx)
COMPRESSED_GPX_FILES := $(patsubst $(GPX_DIR)/%.gpx,$(GPX_COMPRESSED_DIR)/%.gpx,$(GPX_FILES))

GPX_CSV := data/gpx.csv
BOUNDARY_POLY := data/boundary.poly

OSM_DIR := osm
OSM_URL := https://download.geofabrik.de/asia/vietnam-latest.osm.pbf
COUNTRY_OSM_FILE := $$(basename $(OSM_URL))

OSM_WAYS := data/osm-ways.csv
OSM_GPX_CSV := data/osm-gpx.csv
FILTERED_OSM_GPX_CSV := data/filtered-osm-gpx.csv
INTERPOLATED_OSM_GPX_CSV := data/interpolated-osm-gpx.csv
SORTED_OSM_GPX_CSV := data/sorted-osm-gpx.csv
OSM_MATCH_PLOT := data/matched-osm.jpeg

TRIP_CSV := data/trip.csv
TRIP_GPX := data/trip.gpx
SIMPLIFIED_TRIP_GPX := data/simplified-trip.gpx
NAME := "Soc Son"

FILTER_DISTANCE_METERS ?= 100
FILTER_CENTER_MODE ?= median
FILTER_MAX_POINTS ?=
FILTER_MAX_POINTS_ARG := $(if $(FILTER_MAX_POINTS), --max-points $(FILTER_MAX_POINTS),)

.PHONY: clean clean-data clean-data-gpx

clean: clean-data

clean-data:
	@find data -mindepth 1 ! -name ".gitignore" -delete
	@echo "Cleaned data directory (preserved data/.gitignore)."

clean-data-gpx:
	@find data -type f -name "*.gpx" -delete

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@$(PIP) install --disable-pip-version-check -q --upgrade pip
	@$(PIP) install --disable-pip-version-check -q -r $(REQUIREMENTS)

plotgpx:
	@$(PYTHON) scripts/plotgpx.py \
	$(GPX_DIR) \
	"Original GPX" \
	data/original-gpx.jpeg

compress: clean-data-gpx $(COMPRESSED_GPX_FILES)

$(GPX_COMPRESSED_DIR)/%.gpx: $(GPX_DIR)/%.gpx
	@mkdir -p $(GPX_COMPRESSED_DIR)

	@gpsbabel -i gpx -f $< \
	-x simplify,crosstrack,error=0.01k \
	-o gpx -F $@

extract:
	@$(PYTHON) scripts/extract.py \
	$(GPX_COMPRESSED_DIR) \
	$(GPX_CSV)

	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plotgpx.py \
	$(GPX_COMPRESSED_DIR) \
	"Simplified GPX" \
	data/simplified-gpx.jpeg

boundary:
	@$(PYTHON) scripts/boundary.py \
	$(GPX_CSV) \
	$(BOUNDARY_POLY)

country:
	if [ ! -f $(OSM_DIR)/$(COUNTRY_OSM_FILE) ]; then \
		wget $(OSM_URL) -P $(OSM_DIR); \
	fi

osmextract:
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=$(BOUNDARY_POLY) -o=$(OSM_DIR)/foot/gpx.osm.pbf
	@osmium cat --overwrite $(OSM_DIR)/foot/gpx.osm.pbf -o $(OSM_DIR)/gpx.osm

	@bzip2 -c $(OSM_DIR)/gpx.osm > $(OSM_DIR)/overpass-api/gpx.osm.bz2

	@$(PYTHON) scripts/ways.py \
	$(OSM_DIR)/gpx.osm \
	$(OSM_WAYS)

docker:
	@colima start --runtime containerd
	@while ! colima status 2>&1 | grep -qi "running"; do \
		sleep 1; \
	done
	@colima nerdctl -- compose down --remove-orphans || true
	@colima nerdctl -- compose up --build -d

match:
	@echo "Matching..."
	@$(PYTHON) scripts/match.py \
	$(GPX_CSV) \
	$(OSM_GPX_CSV)

	@$(PYTHON) scripts/plot.py \
	$(OSM_GPX_CSV) \
	"OSM Match and Overpass API Filter" \
	data/osm-match.jpeg

filter:
	@echo "Filtering..."
	@$(PYTHON) scripts/filter.py \
	$(OSM_GPX_CSV) \
	$(FILTERED_OSM_GPX_CSV) \
	--distance-meters $(FILTER_DISTANCE_METERS) \
	--center-mode $(FILTER_CENTER_MODE)$(FILTER_MAX_POINTS_ARG)

	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(FILTERED_OSM_GPX_CSV) \
	"Filter by Way Count and Distance between Points" \
	data/osm-filter.jpeg

trip:
	@echo "Making trip..."
	@$(PYTHON) scripts/trip.py \
	$(FILTERED_OSM_GPX_CSV) \
	$(TRIP_CSV)

	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(TRIP_CSV) \
	"Trip GPX" \
	data/trip-gpx.jpeg

gpx:
	@echo "Writing GPX..."
	@$(PYTHON) scripts/gpx.py \
	$(NAME) \
	$(TRIP_CSV) \
	$(TRIP_GPX)

	@if ls data/trip-route-*.gpx >/dev/null 2>&1; then \
		for file in data/trip-route-*.gpx; do \
			gpsbabel -i gpx -f "$$file" \
			-x simplify,crosstrack,error=0.01k \
			-o gpx -F "data/simplified-$$(basename $$file)"; \
		done; \
	else \
		gpsbabel -i gpx -f $(TRIP_GPX) \
		-x simplify,crosstrack,error=0.01k \
		-o gpx -F $(SIMPLIFIED_TRIP_GPX); \
	fi

	@$(PYTHON) scripts/plotgpx.py \
	$(GPX_COMPRESSED_DIR) \
	"Trip GPX" \
	data/trip-gpx.jpeg

parse: compress extract boundary osmextract
	@echo "Parsing complete."

course: match filter trip gpx
	@echo "Course route complete."
