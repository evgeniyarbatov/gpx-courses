import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import polyline

from scripts.trip import TripError, get_trip


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class TripTests(unittest.TestCase):
    def test_get_trip_raises_for_no_trips_error(self):
        df = pd.DataFrame(
            [{"lat": 21.0, "lon": 105.0}, {"lat": 21.1, "lon": 105.1}]
        )
        response = FakeResponse(
            400,
            {
                "message": "No trip visiting all destinations possible.",
                "code": "NoTrips",
            },
            text=(
                '{"message":"No trip visiting all destinations possible.",'
                '"code":"NoTrips"}'
            ),
        )

        with mock.patch("scripts.trip.requests.get", return_value=response):
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("NoTrips", str(err.exception))

    def test_get_trip_raises_when_trips_missing(self):
        df = pd.DataFrame(
            [{"lat": 21.0, "lon": 105.0}, {"lat": 21.1, "lon": 105.1}]
        )
        response = FakeResponse(200, {"code": "Ok"})

        with mock.patch("scripts.trip.requests.get", return_value=response):
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("did not include any trips", str(err.exception))

    def test_get_trip_writes_decoded_geometry_csv(self):
        df = pd.DataFrame(
            [{"lat": 21.0, "lon": 105.0}, {"lat": 21.1, "lon": 105.1}]
        )
        geometry = polyline.encode([(21.0, 105.0), (21.1, 105.1)], precision=6)
        response = FakeResponse(
            200, {"code": "Ok", "trips": [{"geometry": geometry}]}
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            trip_csv = Path(tmpdir) / "trip.csv"
            with mock.patch(
                "scripts.trip.requests.get", return_value=response
            ):
                get_trip(df, str(trip_csv))

            written = pd.read_csv(trip_csv)

        self.assertEqual(list(written.columns), ["lat", "lon"])
        self.assertEqual(len(written), 2)
        self.assertAlmostEqual(written.iloc[0]["lat"], 21.0)
        self.assertAlmostEqual(written.iloc[0]["lon"], 105.0)

    def test_get_trip_retries_with_fewer_points_on_no_trips(self):
        df = pd.DataFrame(
            [
                {"lat": 21.00, "lon": 105.00},
                {"lat": 21.01, "lon": 105.01},
                {"lat": 21.02, "lon": 105.02},
                {"lat": 21.03, "lon": 105.03},
            ]
        )
        no_trips_response = FakeResponse(
            400,
            {
                "message": "No trip visiting all destinations possible.",
                "code": "NoTrips",
            },
            text=(
                '{"message":"No trip visiting all destinations possible.",'
                '"code":"NoTrips"}'
            ),
        )
        geometry = polyline.encode([(21.0, 105.0), (21.1, 105.1)], precision=6)
        success_response = FakeResponse(
            200, {"code": "Ok", "trips": [{"geometry": geometry}]}
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            trip_csv = Path(tmpdir) / "trip.csv"
            with mock.patch(
                "scripts.trip.requests.get",
                side_effect=[no_trips_response, success_response],
            ) as mock_get:
                get_trip(df, str(trip_csv))

            written = pd.read_csv(trip_csv)

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(len(written), 2)
        self.assertAlmostEqual(written.iloc[0]["lat"], 21.0)
        self.assertAlmostEqual(written.iloc[0]["lon"], 105.0)

    def test_get_trip_raises_after_reducing_to_min_points(self):
        df = pd.DataFrame(
            [
                {"lat": 21.00, "lon": 105.00},
                {"lat": 21.01, "lon": 105.01},
                {"lat": 21.02, "lon": 105.02},
                {"lat": 21.03, "lon": 105.03},
            ]
        )
        no_trips_response = FakeResponse(
            400,
            {
                "message": "No trip visiting all destinations possible.",
                "code": "NoTrips",
            },
            text=(
                '{"message":"No trip visiting all destinations possible.",'
                '"code":"NoTrips"}'
            ),
        )

        with mock.patch(
            "scripts.trip.requests.get",
            side_effect=[
                no_trips_response,
                no_trips_response,
                no_trips_response,
            ],
        ):
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("after reducing points", str(err.exception))
        self.assertIn("NoTrips", str(err.exception))


if __name__ == "__main__":
    unittest.main()
