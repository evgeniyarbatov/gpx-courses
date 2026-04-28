import sys
import logging

import pandas as pd
import polyline
import requests

OSRM_TRIP_URL = "http://localhost:6000/trip/v1/foot/"
MIN_TRIP_POINTS = 2
NO_TRIPS_CODE = "NoTrips"
RETRY_REDUCTION_RATIO = 0.85
MIN_CHUNK_SPLIT_POINTS = 4
MIN_DOWNSAMPLED_POINT_RATIO = 0.85
MAX_EXACT_OPTIMIZATION_CHUNKS = 12
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


def _decode_geometry(encoded_geometry):
    coordinates = polyline.decode(encoded_geometry, precision=6)
    return pd.DataFrame(coordinates, columns=["lat", "lon"])


def _passthrough_route(df):
    return df[["lat", "lon"]].reset_index(drop=True)


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


def _chunk_centroid(df):
    return (df["lat"].mean(), df["lon"].mean())


def _split_chunk(df):
    if len(df) < MIN_CHUNK_SPLIT_POINTS:
        raise TripError(
            "Unable to split route chunk further while keeping at least "
            f"{MIN_TRIP_POINTS} points per route."
        )

    lat_span = df["lat"].max() - df["lat"].min()
    lon_span = df["lon"].max() - df["lon"].min()
    primary_axis = "lon" if lon_span >= lat_span else "lat"
    secondary_axis = "lat" if primary_axis == "lon" else "lon"

    ordered = df.sort_values([primary_axis, secondary_axis]).reset_index(drop=True)
    split_index = len(ordered) // 2

    left = ordered.iloc[:split_index].reset_index(drop=True)
    right = ordered.iloc[split_index:].reset_index(drop=True)
    if len(left) < MIN_TRIP_POINTS or len(right) < MIN_TRIP_POINTS:
        raise TripError(
            "Route split produced an invalid chunk with fewer than "
            f"{MIN_TRIP_POINTS} points."
        )

    return left, right


def _try_chunk_downsampling(df):
    attempt_df = df
    retries = 0
    min_allowed_points = max(
        MIN_TRIP_POINTS,
        int(len(df) * MIN_DOWNSAMPLED_POINT_RATIO),
    )

    while len(attempt_df) >= MIN_TRIP_POINTS:
        logger.info(
            "OSRM fallback attempt %s for chunk with %s source points: using %s points.",
            retries + 1,
            len(df),
            len(attempt_df),
        )
        logger.info(
            "OSRM trip attempt (chunked mode): using %s points.",
            len(attempt_df),
        )

        try:
            encoded_geometry = _request_trip(attempt_df)
            return {
                "source_df": df,
                "used_df": attempt_df,
                "route_df": _decode_geometry(encoded_geometry),
                "retries": retries,
                "osrm_solved": True,
            }
        except TripError as exc:
            if exc.code != NO_TRIPS_CODE:
                raise
            if len(attempt_df) <= min_allowed_points:
                logger.info(
                    "OSRM could not solve chunk with %s points. "
                    "Using passthrough geometry to preserve coverage.",
                    len(df),
                )
                return {
                    "source_df": df,
                    "used_df": df,
                    "route_df": _passthrough_route(df),
                    "retries": retries,
                    "osrm_solved": False,
                }

            next_size = _next_retry_size(len(attempt_df))
            if next_size < min_allowed_points:
                next_size = min_allowed_points
            if next_size >= len(attempt_df):
                logger.info(
                    "OSRM could not solve chunk with %s points. "
                    "Using passthrough geometry to preserve coverage.",
                    len(df),
                )
                return {
                    "source_df": df,
                    "used_df": df,
                    "route_df": _passthrough_route(df),
                    "retries": retries,
                    "osrm_solved": False,
                }

            retries += 1
            logger.info(
                "OSRM returned %s in chunked fallback. Retry %s with %s points.",
                NO_TRIPS_CODE,
                retries,
                next_size,
            )
            attempt_df = _select_retry_points(df, next_size)

    raise TripError(
        "OSRM could not solve a route chunk.",
        code=NO_TRIPS_CODE,
    )


def _solve_chunks(df):
    pending_chunks = [df.reset_index(drop=True)]
    solved_chunks = []

    while pending_chunks:
        chunk_df = pending_chunks.pop(0)
        logger.info(
            "OSRM chunk attempt: trying %s points.",
            len(chunk_df),
        )
        if len(chunk_df) < MIN_CHUNK_SPLIT_POINTS:
            logger.info(
                "Chunk with %s points cannot be split safely; trying bounded downsampling.",
                len(chunk_df),
            )
            solved_chunks.append(_try_chunk_downsampling(chunk_df))
            continue

        try:
            encoded_geometry = _request_trip(chunk_df)
            solved_chunks.append(
                {
                    "source_df": chunk_df,
                    "used_df": chunk_df,
                    "route_df": _decode_geometry(encoded_geometry),
                    "retries": 0,
                    "osrm_solved": True,
                }
            )
            continue
        except TripError as exc:
            if exc.code != NO_TRIPS_CODE:
                raise

            left_chunk, right_chunk = _split_chunk(chunk_df)
            logger.info(
                "OSRM returned %s for %s points. Splitting into %s + %s points.",
                NO_TRIPS_CODE,
                len(chunk_df),
                len(left_chunk),
                len(right_chunk),
            )
            pending_chunks.insert(0, right_chunk)
            pending_chunks.insert(0, left_chunk)

    return solved_chunks


def _combine_chunk_sources(solved_chunks, indices):
    return pd.concat(
        [solved_chunks[idx]["source_df"] for idx in indices],
        ignore_index=True,
    )


def _mask_indices(mask):
    indices = []
    idx = 0
    while mask:
        if mask & 1:
            indices.append(idx)
        mask >>= 1
        idx += 1
    return indices


def _solve_mask(mask, solved_chunks, cache):
    if mask in cache:
        return cache[mask]

    indices = _mask_indices(mask)
    if len(indices) == 1:
        chunk = solved_chunks[indices[0]]
        cache[mask] = {
            "source_df": chunk["source_df"].reset_index(drop=True),
            "used_df": chunk["used_df"].reset_index(drop=True),
            "route_df": chunk["route_df"].reset_index(drop=True),
            "retries": chunk["retries"],
            "osrm_solved": chunk.get("osrm_solved", True),
        }
        return cache[mask]

    if any(not solved_chunks[idx].get("osrm_solved", True) for idx in indices):
        cache[mask] = None
        return None

    combined_source = _combine_chunk_sources(solved_chunks, indices)
    logger.info(
        "Attempting exact optimization merge for %s chunks (%s points).",
        len(indices),
        len(combined_source),
    )
    try:
        encoded_geometry = _request_trip(combined_source)
    except TripError as exc:
        if exc.code == NO_TRIPS_CODE:
            cache[mask] = None
            return None
        raise

    cache[mask] = {
        "source_df": combined_source.reset_index(drop=True),
        "used_df": combined_source.reset_index(drop=True),
        "route_df": _decode_geometry(encoded_geometry),
        "retries": 0,
        "osrm_solved": True,
    }
    return cache[mask]


def _iter_submasks_including(mask, first_bit):
    submask = mask
    while submask:
        if submask & first_bit:
            yield submask
        submask = (submask - 1) & mask


def _optimize_chunks_exact(solved_chunks):
    chunk_count = len(solved_chunks)
    if chunk_count <= 1:
        return solved_chunks

    full_mask = (1 << chunk_count) - 1
    cache = {}
    best_partition = []

    def _search(remaining_mask, current_partition):
        nonlocal best_partition
        if remaining_mask == 0:
            if not best_partition or len(current_partition) < len(best_partition):
                best_partition = current_partition[:]
            return

        if best_partition and len(current_partition) >= len(best_partition):
            return

        first_bit = remaining_mask & -remaining_mask
        candidates = list(_iter_submasks_including(remaining_mask, first_bit))
        candidates.sort(key=lambda value: (bin(value).count("1"), value), reverse=True)

        for submask in candidates:
            solved = _solve_mask(submask, solved_chunks, cache)
            if solved is None:
                continue
            current_partition.append(submask)
            _search(remaining_mask ^ submask, current_partition)
            current_partition.pop()

    _search(full_mask, [])
    if not best_partition:
        raise TripError("OSRM could not optimize chunks into final routes.")

    logger.info(
        "Exact optimization selected %s route chunk(s) from %s atomic chunks.",
        len(best_partition),
        chunk_count,
    )
    return [_solve_mask(mask, solved_chunks, cache) for mask in best_partition]


def _optimize_chunks_greedy(solved_chunks):
    if len(solved_chunks) <= 1:
        return solved_chunks

    merged_chunks = solved_chunks[:]
    merged = True
    while merged and len(merged_chunks) > 1:
        merged = False
        pair_candidates = []
        for i in range(len(merged_chunks)):
            for j in range(i + 1, len(merged_chunks)):
                first_center = _chunk_centroid(merged_chunks[i]["source_df"])
                second_center = _chunk_centroid(merged_chunks[j]["source_df"])
                distance_sq = (
                    (first_center[0] - second_center[0]) ** 2
                    + (first_center[1] - second_center[1]) ** 2
                )
                pair_candidates.append((distance_sq, i, j))

        pair_candidates.sort(key=lambda item: item[0])

        for _, first_idx, second_idx in pair_candidates:
            first_chunk = merged_chunks[first_idx]
            second_chunk = merged_chunks[second_idx]
            combined_source = pd.concat(
                [first_chunk["source_df"], second_chunk["source_df"]],
                ignore_index=True,
            )

            logger.info(
                "Attempting greedy merge for chunks of %s and %s points.",
                len(first_chunk["source_df"]),
                len(second_chunk["source_df"]),
            )
            try:
                encoded_geometry = _request_trip(combined_source)
            except TripError as exc:
                if exc.code == NO_TRIPS_CODE:
                    continue
                raise

            combined_route = _decode_geometry(encoded_geometry)
            merged_chunk = {
                "source_df": combined_source.reset_index(drop=True),
                "used_df": combined_source.reset_index(drop=True),
                "route_df": combined_route,
                "retries": 0,
                "osrm_solved": True,
            }

            next_chunks = []
            for idx, chunk in enumerate(merged_chunks):
                if idx in (first_idx, second_idx):
                    continue
                next_chunks.append(chunk)
            next_chunks.append(merged_chunk)
            merged_chunks = next_chunks
            merged = True
            logger.info(
                "Greedy merge succeeded; remaining route chunks: %s.",
                len(merged_chunks),
            )
            break

    return merged_chunks


def _optimize_chunks(solved_chunks):
    if len(solved_chunks) <= MAX_EXACT_OPTIMIZATION_CHUNKS:
        return _optimize_chunks_exact(solved_chunks)

    logger.info(
        "Skipping exact chunk optimization because %s chunks exceed limit %s; using greedy merge.",
        len(solved_chunks),
        MAX_EXACT_OPTIMIZATION_CHUNKS,
    )
    return _optimize_chunks_greedy(solved_chunks)


def _write_trip_csv(solved_chunks, trip_csv_file):
    output_frames = []
    for route_id, chunk in enumerate(solved_chunks, start=1):
        route_df = chunk["route_df"].copy()
        route_df["route_id"] = route_id
        output_frames.append(route_df)

    output_df = pd.concat(output_frames, ignore_index=True)
    output_df.to_csv(trip_csv_file, index=False)


def get_trip(df, trip_csv_file):
    if df.empty:
        raise TripError("Trip input CSV has no points.")

    source_df = df.reset_index(drop=True)
    solved_chunks = _solve_chunks(source_df)
    optimized_chunks = _optimize_chunks(solved_chunks)

    source_points = sum(len(chunk["source_df"]) for chunk in optimized_chunks)
    used_points = sum(len(chunk["used_df"]) for chunk in optimized_chunks)
    dropped_points = source_points - used_points
    passthrough_chunks = sum(
        1 for chunk in optimized_chunks if not chunk.get("osrm_solved", True)
    )

    if not optimized_chunks:
        raise TripError("OSRM did not produce any route chunks.")

    _write_trip_csv(optimized_chunks, trip_csv_file)
    logger.info(
        "OSRM trip completed using %s route chunk(s). Kept %s/%s points (%s dropped in bounded fallback).",
        len(optimized_chunks),
        used_points,
        source_points,
        dropped_points,
    )

    if dropped_points > 0:
        logger.info(
            "Some points were dropped only inside unsplittable chunks. "
            "Increase source density or adjust filtering if needed."
        )
    if passthrough_chunks > 0:
        logger.info(
            "%s chunk(s) were exported with passthrough geometry because "
            "OSRM could not route those points.",
            passthrough_chunks,
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
