VENV_PATH := .venv
PYTHON := $(VENV_PATH)/bin/python
PIP := $(VENV_PATH)/bin/pip
BLACK := $(VENV_PATH)/bin/black
FLAKE8 := $(VENV_PATH)/bin/flake8

REQUIREMENTS := requirements.txt
SCRIPTS_DIR := scripts
PYTHON_FILES := $(shell find $(SCRIPTS_DIR) -name "*.py")

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

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@$(PIP) install --disable-pip-version-check -q --upgrade pip
	@$(PIP) install --disable-pip-version-check -q -r $(REQUIREMENTS)

format:
	@if [ -n "$(PYTHON_FILES)" ]; then \
		$(BLACK) $(PYTHON_FILES); \
	else \
		echo "No Python files"; \
	fi

lint: format
	@if [ -n "$(PYTHON_FILES)" ]; then \
		$(FLAKE8) $(PYTHON_FILES); \
	else \
		echo "No Python files"; \
	fi

plotgpx:
	@$(PYTHON) scripts/plotgpx.py \
	$(GPX_DIR) \
	"Original GPX" \
	data/original-gpx.jpeg

compress: $(COMPRESSED_GPX_FILES)

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
	@open -a Docker
	@while ! docker info > /dev/null 2>&1; do \
			sleep 1; \
	done
	@docker stop $$(docker ps -a -q)
	@docker compose up --build -d

match:
	@$(PYTHON) scripts/match.py \
	$(GPX_CSV) \
	$(OSM_GPX_CSV)

	@$(PYTHON) scripts/plot.py \
	$(OSM_GPX_CSV) \
	"OSM Match and Overpass API Filter" \
	data/osm-match.jpeg

filter:
	@$(PYTHON) scripts/filter.py \
	$(OSM_GPX_CSV) \
	$(FILTERED_OSM_GPX_CSV)

	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(FILTERED_OSM_GPX_CSV) \
	"Filter by Way Count and Distance between Points" \
	data/osm-filter.jpeg

trip:
	@$(PYTHON) scripts/trip.py \
	$(FILTERED_OSM_GPX_CSV) \
	$(TRIP_CSV)

	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(TRIP_CSV) \
	"Trip GPX" \
	data/trip-gpx.jpeg

gpx:
	@$(PYTHON) scripts/gpx.py \
	$(NAME) \
	$(TRIP_CSV) \
	$(TRIP_GPX)

	@gpsbabel -i gpx -f $(TRIP_GPX) \
	-x simplify,crosstrack,error=0.01k \
	-o gpx -F $(SIMPLIFIED_TRIP_GPX)

	@$(PYTHON) scripts/plotgpx.py \
	$(GPX_COMPRESSED_DIR) \
	"Trip GPX" \
	data/trip-gpx.jpeg

cleanvenv:
	@rm -rf $(VENV_PATH)

.PHONY: venv install format lint plotgpx compress extract boundary country osmextract docker match filter trip gpx cleanvenv
