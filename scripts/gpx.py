import sys
from pathlib import Path
import gpxpy

import pandas as pd


def make_gpx(df, name, trip_gpx):
    gpx = gpxpy.gpx.GPX()

    gpx.name = name
    gpx.author_name = "Evgeny Arbatov"

    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for _, row in df.iterrows():
        point = gpxpy.gpx.GPXTrackPoint(latitude=row["lat"], longitude=row["lon"])
        gpx_segment.points.append(point)

    with open(trip_gpx, "w") as f:
        f.write(gpx.to_xml())


def _route_output_path(base_gpx_path, route_id, route_count):
    if route_count == 1:
        return str(base_gpx_path)

    return str(
        base_gpx_path.with_name(
            f"{base_gpx_path.stem}-route-{route_id:02d}{base_gpx_path.suffix}"
        )
    )


def write_gpx_files(df, name, output_gpx_path):
    if "route_id" not in df.columns:
        make_gpx(df, name, output_gpx_path)
        return [str(output_gpx_path)]

    route_ids = sorted(int(route_id) for route_id in df["route_id"].unique())
    output_paths = []

    for route_id in route_ids:
        route_df = df[df["route_id"] == route_id].reset_index(drop=True)
        route_path = _route_output_path(output_gpx_path, route_id, len(route_ids))
        make_gpx(route_df, f"{name} (Route {route_id})", route_path)
        output_paths.append(route_path)

    return output_paths


def main(
    name,
    trip_csv,
    trip_gpx,
):
    df = pd.read_csv(trip_csv)

    output_paths = write_gpx_files(df, name, Path(trip_gpx))
    for output_path in output_paths:
        print(output_path)


if __name__ == "__main__":
    main(*sys.argv[1:])
