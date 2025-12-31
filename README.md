# gpx-courses

Create course from multiple GPX files.

## Workflow
1) Create and populate the virtualenv: `make install`
2) Download the country PBF (run separately once): `make country`
3) Parse GPX files: `make parse GPX_DIR=/Users/zhenya/Downloads/aleksey-trip NAME="Soc Son"`
4) Start OSRM + Overpass: `make docker`
5) Create course: `make course`
6) Optional previews: `make plotgpx`

## Docs
- [scripts/boundary.py](docs/boundary.md)
- [scripts/extract.py](docs/extract.md)
- [scripts/filter.py](docs/filter.md)
- [scripts/gpx.py](docs/gpx.md)
- [scripts/match.py](docs/match.md)
- [scripts/plot.py](docs/plot.md)
- [scripts/plotgpx.py](docs/plotgpx.md)
- [scripts/trip.py](docs/trip.md)
- [scripts/ways.py](docs/ways.md)