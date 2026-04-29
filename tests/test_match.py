import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import requests

from scripts import match


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class MatchTests(unittest.TestCase):
    def test_get_nodes_returns_empty_when_waypoints_missing(self):
        with mock.patch("scripts.match.requests.get", return_value=FakeResponse({})):
            nodes = match.get_nodes(21.0, 105.0)

        self.assertEqual(nodes, [])

    def test_get_nodes_flattens_waypoint_node_ids(self):
        response = FakeResponse(
            {"waypoints": [{"nodes": [101, 102]}, {"nodes": [103, 104]}]}
        )

        with mock.patch("scripts.match.requests.get", return_value=response):
            nodes = match.get_nodes(21.0, 105.0)

        self.assertEqual(nodes, [101, 102, 103, 104])

    def test_get_ways_returns_only_way_ids(self):
        response = FakeResponse(
            {
                "elements": [
                    {"type": "node", "id": 1},
                    {"type": "way", "id": 222},
                    {"type": "way", "id": 333},
                ]
            }
        )

        with mock.patch("scripts.match.requests.get", return_value=response) as mock_get:
            way_ids = match.get_ways([11, 22])

        self.assertEqual(way_ids, [222, 333])
        self.assertEqual(mock_get.call_args.kwargs["params"].keys(), {"data"})

    def test_get_matched_pair_returns_none_on_request_failure(self):
        with mock.patch(
            "scripts.match.requests.get",
            side_effect=requests.RequestException("boom"),
        ):
            matched = match.get_matched_pair((21.0, 105.0), (21.1, 105.1))

        self.assertIsNone(matched)

    def test_get_matched_pair_resolves_tracepoints_to_way_ids(self):
        response = FakeResponse(
            {
                "tracepoints": [
                    {"location": [105.01, 21.01]},
                    {"location": [105.02, 21.02]},
                ]
            }
        )

        with mock.patch("scripts.match.requests.get", return_value=response):
            with mock.patch(
                "scripts.match.get_nodes",
                side_effect=[[1, 2], [3, 4]],
            ) as mock_nodes:
                with mock.patch(
                    "scripts.match.get_ways",
                    side_effect=[[1001], [1002, 1003]],
                ) as mock_ways:
                    matched = match.get_matched_pair((21.0, 105.0), (21.1, 105.1))

        self.assertEqual(
            matched,
            [
                [21.01, 105.01, [1001]],
                [21.02, 105.02, [1002, 1003]],
            ],
        )
        self.assertEqual(mock_nodes.call_count, 2)
        self.assertEqual(mock_ways.call_count, 2)

    def test_main_writes_deduplicated_points_with_non_empty_ways(self):
        df = pd.DataFrame(
            [
                {"lat": 21.0, "lon": 105.0},
                {"lat": 21.1, "lon": 105.1},
                {"lat": 21.2, "lon": 105.2},
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_csv = Path(tmpdir) / "in.csv"
            output_csv = Path(tmpdir) / "out.csv"
            df.to_csv(input_csv, index=False)

            mocked_pairs = [
                [[21.01, 105.01, [10]], [21.02, 105.02, []]],
                [[21.01, 105.01, [10]], [21.03, 105.03, [20, 30]]],
            ]

            with mock.patch(
                "scripts.match.get_matched_pair", side_effect=mocked_pairs
            ):
                match.main(str(input_csv), str(output_csv))

            written = pd.read_csv(output_csv)

        self.assertEqual(list(written.columns), ["lat", "lon", "ways"])
        self.assertEqual(len(written), 2)
        self.assertEqual(
            sorted((round(r.lat, 2), round(r.lon, 2)) for r in written.itertuples()),
            [(21.01, 105.01), (21.03, 105.03)],
        )


if __name__ == "__main__":
    unittest.main()
