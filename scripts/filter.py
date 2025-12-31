import sys

import pandas as pd

from geopy.distance import geodesic

FILTER_DISTANCE_METERS = 100


def filter_by_distance(df):
    filtered = [df.iloc[0]]

    for idx in range(1, len(df)):
        current_point = (df.iloc[idx]["lat"], df.iloc[idx]["lon"])
        too_close = False

        for kept in filtered:
            kept_point = (kept["lat"], kept["lon"])
            if geodesic(current_point, kept_point).meters <= FILTER_DISTANCE_METERS:
                too_close = True
                break

        if not too_close:
            filtered.append(df.iloc[idx])

    filtered_df = pd.DataFrame(filtered)
    return filtered_df


def main(
    gpx_csv_file,
    filtered_gpx_csv_file,
):
    df = pd.read_csv(gpx_csv_file)

    df = filter_by_distance(df)

    df.to_csv(filtered_gpx_csv_file, index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
