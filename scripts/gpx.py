import sys
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


def main(
    name,
    trip_csv,
    trip_gpx,
):
    df = pd.read_csv(trip_csv)

    make_gpx(df, name, trip_gpx)


if __name__ == "__main__":
    main(*sys.argv[1:])
