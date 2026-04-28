import sys

import pandas as pd
import polyline
import requests
from geopy.distance import geodesic

OSRM_TRIP_URL = "http://localhost:6000/trip/v1/foot/"
MIN_TRIP_POINTS = 2
NO_TRIPS_CODE = "NoTrips"
RETRY_REDUCTION_RATIO = 0.85


class TripError(RuntimeError):
    def __init__(self, message, code=None, status_code=None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _extract_trip_geometry(response):
    try:
        trip_data = response.json()
    except ValueError as exc:
        raise TripError(
            "OSRM trip returned a non-JSON response "
            f"(HTTP {response.status_code})."
        ) from exc

    if response.status_code != 200:
        code = (
            trip_data.get("code", "Unknown")
            if isinstance(trip_data, dict)
            else "Unknown"
        )
        message = (
            trip_data.get("message", response.text)
            if isinstance(trip_data, dict)
            else response.text
        )
        error_prefix = (
            "OSRM trip request failed "
            f"(HTTP {response.status_code}, code={code}): "
        )
        raise TripError(
            f"{error_prefix}{message}",
            code=code,
            status_code=response.status_code,
        )

    if not isinstance(trip_data, dict):
        raise TripError("OSRM trip returned an unexpected payload format.")

    if trip_data.get("code") != "Ok":
        raise TripError(
            f"OSRM trip failed with code={trip_data.get('code')}: "
            f"{trip_data.get('message', 'Unknown error')}",
            code=trip_data.get("code"),
            status_code=response.status_code,
        )

    trips = trip_data.get("trips")
    if not trips:
        raise TripError("OSRM trip response did not include any trips.")

    first_trip = trips[0]
    if not isinstance(first_trip, dict):
        raise TripError("OSRM trip response has an invalid trip payload.")

    encoded_geometry = first_trip.get("geometry")
    if not encoded_geometry:
        raise TripError("OSRM trip response is missing geometry.")

    return encoded_geometry


def _request_trip(df):
    if len(df) < MIN_TRIP_POINTS:
        raise TripError(
            f"Trip requires at least {MIN_TRIP_POINTS} points.",
        )

    coords = ";".join(
        f"{row.lon},{row.lat}" for row in df.itertuples(index=False)
    )

    url = f"{OSRM_TRIP_URL}{coords}"
    params = {
        "geometries": "polyline6",
        "overview": "full",
        "annotations": "false",
        "steps": "false",
    }
    response = requests.get(url, params=params, timeout=30)

    return _extract_trip_geometry(response)


def _distance_from_center(df):
    center = (df["lat"].median(), df["lon"].median())
    return df.apply(
        lambda row: geodesic((row["lat"], row["lon"]), center).meters,
        axis=1,
    )


def _select_high_priority_points(df, target_count):
    if target_count >= len(df):
        return df

    distances = _distance_from_center(df)
    ranked_indices = (
        distances.sort_values(ascending=False, kind="mergesort")
        .head(target_count)
        .index
    )
    keep_indices = sorted(ranked_indices)
    return df.loc[keep_indices].reset_index(drop=True)


def _next_retry_size(current_size):
    reduced_size = int(current_size * RETRY_REDUCTION_RATIO)
    reduced_size = min(current_size - 1, reduced_size)
    return max(MIN_TRIP_POINTS, reduced_size)


def get_trip(df, trip_csv_file):
    if df.empty:
        raise TripError("Trip input CSV has no points.")

    attempt_df = df.reset_index(drop=True)

    while len(attempt_df) >= MIN_TRIP_POINTS:
        try:
            encoded_geometry = _request_trip(attempt_df)
            coordinates = polyline.decode(encoded_geometry, precision=6)

            output_df = pd.DataFrame(coordinates, columns=["lat", "lon"])
            output_df.to_csv(trip_csv_file, index=False)
            return
        except TripError as exc:
            if exc.code != NO_TRIPS_CODE or len(attempt_df) == MIN_TRIP_POINTS:
                raise

            next_size = _next_retry_size(len(attempt_df))
            attempt_df = _select_high_priority_points(df, next_size)

    raise TripError(
        "OSRM trip failed after retrying with fewer points.",
        code=NO_TRIPS_CODE,
    )


def main(
    gpx_csv_file,
    trip_csv_file,
):
    df = pd.read_csv(gpx_csv_file)

    try:
        get_trip(df, trip_csv_file)
    except TripError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main(*sys.argv[1:])
