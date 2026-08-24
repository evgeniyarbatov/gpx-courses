# Roadmap

Builds a clean course GPX from raw activity traces: simplify → clip local OSM → match to OSM ways (OSRM + Overpass) → filter noise → generate optimized route → export.

## Shipped

Full pipeline with a single `make run` wrapping it end-to-end, Docker-based local OSRM/Overpass stack, shared OSM cache with `dotfiles`, ruff/mypy --strict pass, portable paths.

## Next

- Confirm/streamline the external-tool bootstrap (see TODO.md) — six prerequisites is a lot for "one command to run."
- Basic pipeline tests (see TODO.md), at least a golden-file regression test on one known GPX input.
