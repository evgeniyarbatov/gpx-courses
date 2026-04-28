import argparse
import sys

import pandas as pd
from geopy.distance import geodesic

FILTER_DISTANCE_METERS = 100
CENTER_MODE_MEDIAN = "median"
CENTER_MODE_MEAN = "mean"
CENTER_MODES = (CENTER_MODE_MEDIAN, CENTER_MODE_MEAN)


def _get_center(df, center_mode):
    if center_mode == CENTER_MODE_MEDIAN:
        return (df["lat"].median(), df["lon"].median())
    if center_mode == CENTER_MODE_MEAN:
        return (df["lat"].mean(), df["lon"].mean())

    raise ValueError(
        f"Unsupported center mode '{center_mode}'. "
        f"Expected one of: {', '.join(CENTER_MODES)}."
    )


def _distance_to_center(point, center):
    return geodesic(point, center).meters


def filter_by_center_distance(
    df,
    min_distance_meters=FILTER_DISTANCE_METERS,
    max_points=None,
    center_mode=CENTER_MODE_MEDIAN,
):
    if df.empty:
        return df.copy()

    if max_points is not None and max_points < 1:
        raise ValueError("max_points must be at least 1 when provided.")

    center = _get_center(df, center_mode)

    ranked_indices = sorted(
        df.index,
        key=lambda idx: (
            -_distance_to_center(
                (df.at[idx, "lat"], df.at[idx, "lon"]),
                center,
            ),
            idx,
        ),
    )

    kept_indices = []

    for idx in ranked_indices:
        current_point = (df.at[idx, "lat"], df.at[idx, "lon"])
        too_close = False

        for kept_idx in kept_indices:
            kept_point = (df.at[kept_idx, "lat"], df.at[kept_idx, "lon"])
            if geodesic(current_point, kept_point).meters <= min_distance_meters:
                too_close = True
                break

        if not too_close:
            kept_indices.append(idx)
            if max_points is not None and len(kept_indices) >= max_points:
                break

    kept_indices.sort()
    return df.loc[kept_indices].reset_index(drop=True)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Keep points furthest from route center first while enforcing "
            "minimum spacing."
        )
    )
    parser.add_argument("gpx_csv_file")
    parser.add_argument("filtered_gpx_csv_file")
    parser.add_argument(
        "--distance-meters",
        type=float,
        default=FILTER_DISTANCE_METERS,
        help="Minimum distance between retained points.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=None,
        help="Optional cap on number of retained points.",
    )
    parser.add_argument(
        "--center-mode",
        choices=CENTER_MODES,
        default=CENTER_MODE_MEDIAN,
        help="How to compute route center for point ranking.",
    )
    return parser.parse_args(argv)


def main(
    gpx_csv_file,
    filtered_gpx_csv_file,
    distance_meters=FILTER_DISTANCE_METERS,
    max_points=None,
    center_mode=CENTER_MODE_MEDIAN,
):
    df = pd.read_csv(gpx_csv_file)

    df = filter_by_center_distance(
        df,
        min_distance_meters=distance_meters,
        max_points=max_points,
        center_mode=center_mode,
    )

    df.to_csv(filtered_gpx_csv_file, index=False)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    main(
        args.gpx_csv_file,
        args.filtered_gpx_csv_file,
        distance_meters=args.distance_meters,
        max_points=args.max_points,
        center_mode=args.center_mode,
    )
