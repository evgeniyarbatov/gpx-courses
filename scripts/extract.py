import sys
import gpxpy
import os

import pandas as pd


def main(gpx_dir, csv_file):
    points = []

    for filename in os.listdir(gpx_dir):
        if filename.endswith(".gpx"):
            filepath = os.path.join(gpx_dir, filename)
            with open(filepath, "r") as gpx_file:
                gpx = gpxpy.parse(gpx_file)
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            points.append(
                                {
                                    "lat": point.latitude,
                                    "lon": point.longitude,
                                }
                            )

    df = pd.DataFrame(points)
    df.to_csv(csv_file, index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
