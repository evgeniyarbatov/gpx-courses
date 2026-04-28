import sys
import requests
import polyline
import math

import pandas as pd

OSRM_TRIP_URL = "http://localhost:6000/trip/v1/foot/"
MIN_TRIP_POINTS = 2


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

    # with open(trip_csv_file, "w") as file:
    #     json.dump(trip_data, file, indent=4)

    return _extract_trip_geometry(response)


def _reduce_points(df, target_count):
    point_count = len(df)
    if target_count >= point_count:
        return df

    step = (point_count - 1) / (target_count - 1)
    indices = []
    for i in range(target_count):
        indices.append(int(round(i * step)))

    deduped_indices = []
    seen = set()
    for idx in indices:
        if idx in seen:
            continue
        deduped_indices.append(idx)
        seen.add(idx)

    if deduped_indices[-1] != point_count - 1:
        deduped_indices[-1] = point_count - 1

    return df.iloc[deduped_indices].reset_index(drop=True)


def _next_target_count(current_count):
    reduced = int(math.ceil(current_count * 0.75))
    if reduced >= current_count:
        reduced = current_count - 1
    return max(MIN_TRIP_POINTS, reduced)


def get_trip(df, trip_csv_file):
    if df.empty:
        raise TripError("Trip input CSV has no points.")

    current_df = df
    last_error = None

    while len(current_df) >= MIN_TRIP_POINTS:
        try:
            encoded_geometry = _request_trip(current_df)
            coordinates = polyline.decode(encoded_geometry, precision=6)

            output_df = pd.DataFrame(coordinates, columns=["lat", "lon"])
            output_df.to_csv(trip_csv_file, index=False)
            return
        except TripError as exc:
            last_error = exc
            if exc.code != "NoTrips":
                raise

            if len(current_df) == MIN_TRIP_POINTS:
                break

            next_count = _next_target_count(len(current_df))
            print(
                "OSRM returned NoTrips with "
                f"{len(current_df)} points. "
                f"Retrying with {next_count} points..."
            )
            current_df = _reduce_points(current_df, next_count)

    raise TripError(
        "OSRM trip could not be generated after reducing points to "
        f"{len(current_df)}. Last error: {last_error}",
        code=last_error.code if last_error else None,
        status_code=last_error.status_code if last_error else None,
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
