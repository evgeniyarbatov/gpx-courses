VENV_PATH := .venv

PYTHON := $(VENV_PATH)/bin/python
PIP := $(VENV_PATH)/bin/pip
REQUIREMENTS := requirements.txt

GPX_DIR ?=
NAME ?=

OSM_DIR := osm
OSM_URL := https://download.geofabrik.de/asia/vietnam-latest.osm.pbf
COUNTRY_OSM_FILE := $$(basename $(OSM_URL))

.PHONY: \
	venv install test \
	clean clean-data clean-data-gpx \
	gpx-input-check \
	plotgpx compress extract boundary country osmextract docker match filter trip gpx parse course

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@$(PIP) install --disable-pip-version-check -q --upgrade pip
	@$(PIP) install --disable-pip-version-check -q -r $(REQUIREMENTS)

test:
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

clean: clean-data

clean-data:
	@find data -mindepth 1 ! -name ".gitignore" -delete
	@echo "Cleaned data directory (preserved data/.gitignore)."

clean-data-gpx:
	@find data -type f -name "*.gpx" -delete

gpx-input-check:
	@test -n "$(strip $(GPX_DIR))" || (echo "Error: GPX_DIR is required. Example: make parse GPX_DIR=/path/to/gpx-dir" >&2; exit 1)
	@test -d "$(GPX_DIR)" || (echo "Error: GPX_DIR does not exist: $(GPX_DIR)" >&2; exit 1)

plotgpx: gpx-input-check
	@$(PYTHON) scripts/plotgpx.py \
	$(GPX_DIR) \
	"Original GPX" \
	data/original-gpx.jpeg

compress: gpx-input-check clean-data-gpx
	@$(PYTHON) scripts/compress.py "$(GPX_DIR)"

extract:
	@$(PYTHON) scripts/extract.py

	@$(PYTHON) scripts/plotgpx.py \
	data/gpx_compressed \
	"Simplified GPX" \
	data/simplified-gpx.jpeg

boundary:
	@$(PYTHON) scripts/boundary.py

country:
	@if [ ! -f $(OSM_DIR)/$(COUNTRY_OSM_FILE) ]; then \
		wget $(OSM_URL) -P $(OSM_DIR); \
	fi

osmextract:
	@osmconvert $(OSM_DIR)/$(COUNTRY_OSM_FILE) -B=data/boundary.poly -o=$(OSM_DIR)/foot/gpx.osm.pbf
	@osmium cat --overwrite $(OSM_DIR)/foot/gpx.osm.pbf -o $(OSM_DIR)/gpx.osm
	@bzip2 -c $(OSM_DIR)/gpx.osm > $(OSM_DIR)/overpass-api/gpx.osm.bz2

docker:
	@colima start --runtime containerd
	@while ! colima status 2>&1 | grep -qi "running"; do \
		sleep 1; \
	done
	@colima nerdctl -- compose down --remove-orphans || true
	@colima nerdctl -- compose up --build -d

match:
	@echo "Matching..."
	@$(PYTHON) scripts/match.py

	@$(PYTHON) scripts/plot.py \
	data/osm-gpx.csv \
	"OSRM-Matched Points with OSM Way IDs" \
	data/osm-match.jpeg

filter:
	@echo "Filtering..."
	@$(PYTHON) scripts/filter.py

	@$(PYTHON) scripts/plot.py \
	data/filtered-osm-gpx.csv \
	"Center-Distance Filtered Match Points" \
	data/osm-filter.jpeg

trip:
	@echo "Making trip..."
	@$(PYTHON) scripts/trip.py

	@$(PYTHON) scripts/plot.py \
	data/trip.csv \
	"OSRM Trip Route (CSV Output)" \
	data/trip-gpx.jpeg

gpx:
	@test -n "$(strip $(NAME))" || (echo "Error: NAME is required. Example: make gpx NAME=\"Soc Son\"" >&2; exit 1)
	@echo "Writing GPX..."
	@$(PYTHON) scripts/gpx.py "$(NAME)"

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
		$(PYTHON) scripts/plotgpx.py "data/trip-route-*.gpx" "Generated Trip GPX Routes" data/trip-gpx.jpeg; \
	else \
		$(PYTHON) scripts/plotgpx.py "data/trip.gpx" "Generated Trip GPX Routes" data/trip-gpx.jpeg; \
	fi

parse: compress extract boundary osmextract
	@echo "Parsing complete."

course: match filter trip gpx
	@echo "Course route complete."
