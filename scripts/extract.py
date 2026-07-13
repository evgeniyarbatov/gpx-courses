import argparse
import os

import gpxpy
import pandas as pd

DEFAULT_GPX_DIR = "data/gpx_compressed"
DEFAULT_GPX_CSV = "data/gpx.csv"


def main(gpx_dir, csv_file):
    points = []

    for filename in os.listdir(gpx_dir):
        if filename.endswith(".gpx"):
            filepath = os.path.join(gpx_dir, filename)
            with open(filepath) as gpx_file:
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


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract lat/lon points from GPX files into a CSV."
    )
    parser.add_argument("gpx_dir", nargs="?", default=DEFAULT_GPX_DIR)
    parser.add_argument("csv_file", nargs="?", default=DEFAULT_GPX_CSV)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main(args.gpx_dir, args.csv_file)
