PROJECT_NAME := $(shell basename $(PWD))
VENV_PATH = ~/.venv/$(PROJECT_NAME)

GPX_DIR = /Users/zhenya/Documents/gpx/ecopark

GPX_CSV = data/gpx.csv
BOUNDARY_POLY = data/boundary.poly

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@source $(VENV_PATH)/bin/activate && \
	pip install --disable-pip-version-check -q -r requirements.txt

extract:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/extract.py \
	$(GPX_DIR) \
	$(GPX_CSV)

boundary:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/boundary.py \
	$(GPX_CSV) \
	$(BOUNDARY_POLY)