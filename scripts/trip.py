import sys
import logging

import pandas as pd
import polyline
import requests

OSRM_TRIP_URL = "http://localhost:6000/trip/v1/foot/"
MIN_TRIP_POINTS = 2
NO_TRIPS_CODE = "NoTrips"
RETRY_REDUCTION_RATIO = 0.85
logger = logging.getLogger(__name__)


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


def _evenly_spaced_indices(total_count, target_count):
    if target_count >= total_count:
        return list(range(total_count))
    if target_count == 1:
        return [0]

    step = (total_count - 1) / (target_count - 1)
    raw_indices = [round(step * i) for i in range(target_count)]

    unique_indices = []
    seen = set()
    for idx in raw_indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)

    for idx in range(total_count):
        if len(unique_indices) >= target_count:
            break
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)

    unique_indices.sort()
    return unique_indices


def _select_retry_points(df, target_count):
    if target_count >= len(df):
        return df

    keep_indices = _evenly_spaced_indices(len(df), target_count)
    return df.loc[keep_indices].reset_index(drop=True)


def _next_retry_size(current_size):
    reduced_size = int(current_size * RETRY_REDUCTION_RATIO)
    reduced_size = min(current_size - 1, reduced_size)
    return max(MIN_TRIP_POINTS, reduced_size)


def get_trip(df, trip_csv_file):
    if df.empty:
        raise TripError("Trip input CSV has no points.")

    source_df = df.reset_index(drop=True)
    attempt_df = source_df
    retries = 0
    attempt = 1

    while len(attempt_df) >= MIN_TRIP_POINTS:
        logger.info(
            "OSRM trip attempt %s: using %s points.",
            attempt,
            len(attempt_df),
        )
        try:
            encoded_geometry = _request_trip(attempt_df)
            coordinates = polyline.decode(encoded_geometry, precision=6)

            output_df = pd.DataFrame(coordinates, columns=["lat", "lon"])
            output_df.to_csv(trip_csv_file, index=False)
            logger.info(
                "OSRM trip succeeded after %s retries, using %s points.",
                retries,
                len(attempt_df),
            )
            return
        except TripError as exc:
            if exc.code != NO_TRIPS_CODE:
                raise
            if len(attempt_df) == MIN_TRIP_POINTS:
                logger.info(
                    "OSRM trip failed after %s retries; final attempt used %s points.",
                    retries,
                    len(attempt_df),
                )
                raise TripError(
                    "OSRM trip failed after "
                    f"{retries} retries. Last attempt used {len(attempt_df)} points.",
                    code=NO_TRIPS_CODE,
                    status_code=exc.status_code,
                ) from exc

            next_size = _next_retry_size(len(attempt_df))
            retries += 1
            logger.info(
                "OSRM returned %s on attempt %s. Retry %s with %s points.",
                NO_TRIPS_CODE,
                attempt,
                retries,
                next_size,
            )
            attempt_df = _select_retry_points(source_df, next_size)
            attempt += 1

    raise TripError(
        "OSRM trip failed after "
        f"{retries} retries. Last attempt used {len(attempt_df)} points.",
        code=NO_TRIPS_CODE,
    )


def main(
    gpx_csv_file,
    trip_csv_file,
):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    df = pd.read_csv(gpx_csv_file)

    try:
        get_trip(df, trip_csv_file)
    except TripError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main(*sys.argv[1:])
