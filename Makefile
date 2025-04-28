PROJECT_NAME := $(shell basename $(PWD))
VENV_PATH = ~/.venv/$(PROJECT_NAME)

GPX_DIR = /Users/zhenya/Documents/gpx/ecopark

GPX_CSV = data/gpx.csv
BOUNDARY_POLY = data/boundary.poly

OSM_DIR = osm
OSM_GPX_CSV = data/osm-gpx.csv

OSM_URL = https://download.geofabrik.de/asia/vietnam-latest.osm.pbf
COUNTRY_OSM_FILE = $$(basename $(OSM_URL))

GPX_COMPRESSED_DIR = data/gpx_compressed

GPX_FILES := $(wildcard $(GPX_DIR)/*.gpx)
COMPRESSED_GPX_FILES := $(patsubst $(GPX_DIR)/%.gpx,$(GPX_COMPRESSED_DIR)/%.gpx,$(GPX_FILES))

OSM_MATCH_PLOT = data/matched-osm.jpeg

TRIP_CSV = data/trip.csv
TRIP_GPX = data/trip.gpx

SIMPLIFIED_TRIP_GPX = data/simplified-trip.gpx

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@source $(VENV_PATH)/bin/activate && \
	pip install --disable-pip-version-check -q -r requirements.txt

compress: $(COMPRESSED_GPX_FILES)

$(GPX_COMPRESSED_DIR)/%.gpx: $(GPX_DIR)/%.gpx
	@echo "Processing $< -> $@"
	@gpsbabel -i gpx -f $< \
	-x simplify,crosstrack,error=0.01k \
	-o gpx -F $@

extract:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/extract.py \
	$(GPX_COMPRESSED_DIR) \
	$(GPX_CSV)

boundary:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/boundary.py \
	$(GPX_CSV) \
	$(BOUNDARY_POLY)

country:
	if [ ! -f $(OSM_DIR)/$(COUNTRY_OSM_FILE) ]; then \
		wget $(OSM_URL) -P $(OSM_DIR); \
	fi

osmextract:
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=$(BOUNDARY_POLY) -o=$(OSM_DIR)/foot/gpx.osm.pbf
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=$(BOUNDARY_POLY) -o=$(OSM_DIR)/bicycle/gpx.osm.pbf
	@osmium cat --overwrite $(OSM_DIR)/foot/gpx.osm.pbf -o $(OSM_DIR)/gpx.osm

docker:
	@open -a Docker
	@while ! docker info > /dev/null 2>&1; do \
			sleep 1; \
	done
	@docker stop $$(docker ps -a -q)
	@docker compose up --build -d

match:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/match.py \
	$(GPX_CSV) \
	$(OSM_GPX_CSV)

plot:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(OSM_GPX_CSV) \
	$(OSM_MATCH_PLOT)

trip:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/trip.py \
	$(OSM_GPX_CSV) \
	$(TRIP_CSV)

gpx:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/gpx.py \
	$(TRIP_CSV) \
	$(TRIP_GPX)

simplifygpx:
	@gpsbabel -i gpx -f $(TRIP_GPX) \
	-x simplify,crosstrack,error=0.01k \
	-o gpx -F $(SIMPLIFIED_TRIP_GPX)