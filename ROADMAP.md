# Roadmap

## Why keep going

This is the shared plumbing (simplify → clip → match to OSM ways → filter → export) that turns messy raw traces into clean, reusable course geometry. Its value isn't the six-step pipeline itself — it's that this exact shape (raw GPX in, OSM-matched clean route out) is the prerequisite for every other repo that needs a trustworthy course rather than a raw recording.

## What it opens up

Once the external-tool bootstrap is streamlined and the pipeline has even one golden-file regression test, this stops being "my personal course-cleaning script" and becomes something you could point at any GPX-heavy project (race prep, route sharing) with confidence it won't silently corrupt a route. The current six-prerequisite setup is the actual barrier to that.

## Capability this builds

Matching noisy GPS traces to authoritative map data (OSRM + Overpass) reliably — a core competency that most of the other GPX/routing repos in this portfolio depend on without owning the matching logic themselves.

## Connects to

- [private]
- **[private]**, [private], **[private]** — race-prep repos that need exactly this "raw trace → clean course" step, currently each solving it ad hoc or not at all.
- **[private]** — the natural quality check for the OSRM matching this pipeline depends on.
