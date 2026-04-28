import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import polyline

from scripts.trip import NO_TRIPS_CODE, TripError, get_trip


class FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class TripTests(unittest.TestCase):
    def test_get_trip_retries_no_trips_then_raises(self):
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
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("NoTrips", str(err.exception))
        self.assertEqual(mock_get.call_count, 3)

    def test_get_trip_raises_when_trips_missing(self):
        df = pd.DataFrame(
            [{"lat": 21.0, "lon": 105.0}, {"lat": 21.1, "lon": 105.1}]
        )
        response = FakeResponse(200, {"code": "Ok"})

        with mock.patch("scripts.trip.requests.get", return_value=response):
            with self.assertRaises(TripError) as err:
                get_trip(df, "unused.csv")

        self.assertIn("did not include any trips", str(err.exception))

    def test_get_trip_retries_and_writes_decoded_geometry_csv(self):
        df = pd.DataFrame(
            [
                {"lat": 21.0000, "lon": 105.0000},
                {"lat": 21.0001, "lon": 105.0001},
                {"lat": 21.2000, "lon": 105.2000},
                {"lat": 21.3000, "lon": 105.3000},
            ]
        )
        first_response = FakeResponse(
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

        geometry = polyline.encode([(21.0, 105.0), (21.3, 105.3)], precision=6)
        second_response = FakeResponse(
            200, {"code": "Ok", "trips": [{"geometry": geometry}]}
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            trip_csv = Path(tmpdir) / "trip.csv"
            with mock.patch(
                "scripts.trip.requests.get",
                side_effect=[first_response, second_response],
            ) as mock_get:
                get_trip(df, str(trip_csv))

            written = pd.read_csv(trip_csv)

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(list(written.columns), ["lat", "lon"])
        self.assertEqual(len(written), 2)

        second_call_url = mock_get.call_args_list[1][0][0]
        second_call_coords = second_call_url.split("/trip/v1/foot/")[-1]
        self.assertEqual(len(second_call_coords.split(";")), 3)


if __name__ == "__main__":
    unittest.main()
