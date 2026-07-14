import argparse
from typing import Any

import pandas as pd
from geopy.distance import geodesic

FILTER_DISTANCE_METERS = 100
CENTER_MODE_MEDIAN = "median"
CENTER_MODE_MEAN = "mean"
CENTER_MODES = (CENTER_MODE_MEDIAN, CENTER_MODE_MEAN)
DEFAULT_INPUT_CSV = "data/osm-gpx.csv"
DEFAULT_OUTPUT_CSV = "data/filtered-osm-gpx.csv"


def _get_center(df: pd.DataFrame, center_mode: str) -> tuple[float, float]:
    if center_mode == CENTER_MODE_MEDIAN:
        return (df["lat"].median(), df["lon"].median())
    if center_mode == CENTER_MODE_MEAN:
        return (df["lat"].mean(), df["lon"].mean())

    raise ValueError(
        f"Unsupported center mode '{center_mode}'. Expected one of: {', '.join(CENTER_MODES)}."
    )


def _distance_to_center(point: tuple[float, float], center: tuple[float, float]) -> float:
    return float(geodesic(point, center).meters)


def _cell_as_float(value: Any) -> float:
    return float(value)


def filter_by_center_distance(
    df: pd.DataFrame,
    min_distance_meters: float = FILTER_DISTANCE_METERS,
    max_points: int | None = None,
    center_mode: str = CENTER_MODE_MEDIAN,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    if max_points is not None and max_points < 1:
        raise ValueError("max_points must be at least 1 when provided.")

    center = _get_center(df, center_mode)

    ranked_indices = sorted(
        df.index,
        key=lambda idx: (
            -_distance_to_center(
                (_cell_as_float(df.at[idx, "lat"]), _cell_as_float(df.at[idx, "lon"])),
                center,
            ),
            idx,
        ),
    )

    kept_indices: list[int] = []

    for idx in ranked_indices:
        current_point = (_cell_as_float(df.at[idx, "lat"]), _cell_as_float(df.at[idx, "lon"]))
        too_close = False

        for kept_idx in kept_indices:
            kept_point = (
                _cell_as_float(df.at[kept_idx, "lat"]),
                _cell_as_float(df.at[kept_idx, "lon"]),
            )
            if geodesic(current_point, kept_point).meters <= min_distance_meters:
                too_close = True
                break

        if not too_close:
            kept_indices.append(idx)
            if max_points is not None and len(kept_indices) >= max_points:
                break

    kept_indices.sort()
    return df.loc[kept_indices].reset_index(drop=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Keep points furthest from route center first while enforcing minimum spacing."
        )
    )
    parser.add_argument("gpx_csv_file", nargs="?", default=DEFAULT_INPUT_CSV)
    parser.add_argument("filtered_gpx_csv_file", nargs="?", default=DEFAULT_OUTPUT_CSV)
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
    return parser.parse_args()


def main(
    gpx_csv_file: str,
    filtered_gpx_csv_file: str,
    distance_meters: float = FILTER_DISTANCE_METERS,
    max_points: int | None = None,
    center_mode: str = CENTER_MODE_MEDIAN,
) -> None:
    df = pd.read_csv(gpx_csv_file)

    df = filter_by_center_distance(
        df,
        min_distance_meters=distance_meters,
        max_points=max_points,
        center_mode=center_mode,
    )

    df.to_csv(filtered_gpx_csv_file, index=False)


if __name__ == "__main__":
    args = _parse_args()
    main(
        args.gpx_csv_file,
        args.filtered_gpx_csv_file,
        distance_meters=args.distance_meters,
        max_points=args.max_points,
        center_mode=args.center_mode,
    )
