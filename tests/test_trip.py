import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import polyline

from scripts.trip import (
    NO_TRIPS_CODE,
    TripError,
    _optimize_chunks,
    _split_chunk,
    _select_retry_points,
    get_trip,
)


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class TripTests(unittest.TestCase):
    def test_select_retry_points_keeps_even_route_spread(self):
        df = pd.DataFrame(
            [
                {"lat": 0.0, "lon": 100.0},
                {"lat": 0.0, "lon": 101.0},
                {"lat": 0.0, "lon": 102.0},
                {"lat": 0.0, "lon": 103.0},
                {"lat": 0.0, "lon": 104.0},
            ]
        )

        selected = _select_retry_points(df, 3)

        self.assertEqual(selected["lon"].tolist(), [100.0, 102.0, 104.0])

    def test_split_chunk_balances_points(self):
        df = pd.DataFrame(
            [
                {"lat": 21.0, "lon": 105.00},
                {"lat": 21.0, "lon": 105.01},
                {"lat": 21.0, "lon": 105.10},
                {"lat": 21.0, "lon": 105.11},
            ]
        )

        left, right = _split_chunk(df)

        self.assertEqual(len(left), 2)
        self.assertEqual(len(right), 2)
        self.assertLess(left["lon"].max(), right["lon"].min())

    def test_get_trip_uses_passthrough_for_unsplittable_chunks(self):
        df = pd.DataFrame(
            [
                {"lat": 21.0, "lon": 105.0},
                {"lat": 21.1, "lon": 105.1},
                {"lat": 21.2, "lon": 105.2},
                {"lat": 21.3, "lon": 105.3},
            ]
        )
        response = FakeResponse(
            400,
            {
                "message": "No trip visiting all destinations possible.",
                "code": NO_TRIPS_CODE,
            },
            text=(
                '{"message":"No trip visiting all destinations possible.",'
                '"code":"NoTrips"}'
            ),
        )

        with mock.patch(
            "scripts.trip.requests.get", return_value=response
        ) as mock_get:
            with tempfile.TemporaryDirectory() as tmpdir:
                trip_csv = Path(tmpdir) / "trip.csv"
                with self.assertLogs("scripts.trip", level="INFO") as logs:
                    get_trip(df, str(trip_csv))
                written = pd.read_csv(trip_csv)

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(len(written), 4)
        self.assertEqual(sorted(written["route_id"].unique().tolist()), [1, 2])
        self.assertTrue(
            any("Using passthrough geometry to preserve coverage." in line for line in logs.output)
        )

    def test_get_trip_raises_when_trips_missing(self):
        df = pd.DataFrame(
            [{"lat": 21.0, "lon": 105.0}, {"lat": 21.1, "lon": 105.1}]
        )
        response = FakeResponse(200, {"code": "Ok"})

        with mock.patch("scripts.trip.requests.get", return_value=response):
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("did not include any trips", str(err.exception))

    def test_get_trip_splits_and_writes_multiple_route_ids(self):
        df = pd.DataFrame(
            [
                {"lat": 21.0000, "lon": 105.0000},
                {"lat": 21.0001, "lon": 105.0001},
                {"lat": 21.2000, "lon": 105.2000},
                {"lat": 21.3000, "lon": 105.3000},
            ]
        )
        split_response = FakeResponse(
            400,
            {
                "message": "No trip visiting all destinations possible.",
                "code": NO_TRIPS_CODE,
            },
            text=(
                '{"message":"No trip visiting all destinations possible.",'
                '"code":"NoTrips"}'
            ),
        )

        geometry_left = polyline.encode(
            [(21.0, 105.0), (21.0001, 105.0001)], precision=6
        )
        geometry_right = polyline.encode(
            [(21.2, 105.2), (21.3, 105.3)], precision=6
        )
        left_response = FakeResponse(
            200, {"code": "Ok", "trips": [{"geometry": geometry_left}]}
        )
        right_response = FakeResponse(
            200, {"code": "Ok", "trips": [{"geometry": geometry_right}]}
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            trip_csv = Path(tmpdir) / "trip.csv"
            with mock.patch(
                "scripts.trip.requests.get",
                side_effect=[split_response, left_response, right_response],
            ) as mock_get:
                with mock.patch(
                    "scripts.trip._optimize_chunks", side_effect=lambda chunks: chunks
                ):
                    get_trip(df, str(trip_csv))

            written = pd.read_csv(trip_csv)

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(list(written.columns), ["lat", "lon", "route_id"])
        self.assertEqual(sorted(written["route_id"].unique().tolist()), [1, 2])
        self.assertEqual(len(written), 4)

    def test_optimize_chunks_exact_prefers_single_route_when_possible(self):
        chunk_a = {
            "source_df": pd.DataFrame(
                [{"lat": 21.0, "lon": 105.0}, {"lat": 21.01, "lon": 105.01}]
            ),
            "used_df": pd.DataFrame(
                [{"lat": 21.0, "lon": 105.0}, {"lat": 21.01, "lon": 105.01}]
            ),
            "route_df": pd.DataFrame(
                [{"lat": 21.0, "lon": 105.0}, {"lat": 21.01, "lon": 105.01}]
            ),
            "retries": 0,
        }
        chunk_b = {
            "source_df": pd.DataFrame(
                [{"lat": 21.2, "lon": 105.2}, {"lat": 21.3, "lon": 105.3}]
            ),
            "used_df": pd.DataFrame(
                [{"lat": 21.2, "lon": 105.2}, {"lat": 21.3, "lon": 105.3}]
            ),
            "route_df": pd.DataFrame(
                [{"lat": 21.2, "lon": 105.2}, {"lat": 21.3, "lon": 105.3}]
            ),
            "retries": 0,
        }

        merged_geometry = polyline.encode(
            [(21.0, 105.0), (21.01, 105.01), (21.2, 105.2), (21.3, 105.3)],
            precision=6,
        )
        response = FakeResponse(
            200,
            {"code": "Ok", "trips": [{"geometry": merged_geometry}]},
        )

        with mock.patch("scripts.trip.requests.get", return_value=response) as mock_get:
            optimized = _optimize_chunks([chunk_a, chunk_b])

        self.assertEqual(len(optimized), 1)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(len(optimized[0]["route_df"]), 4)


if __name__ == "__main__":
    unittest.main()
