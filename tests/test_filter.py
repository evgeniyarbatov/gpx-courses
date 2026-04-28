import unittest

import pandas as pd

from scripts.filter import filter_by_center_distance


class FilterTests(unittest.TestCase):
    def test_filter_keeps_furthest_points_when_capped(self):
        df = pd.DataFrame(
            [
                {"lat": 0.0, "lon": 0.0},
                {"lat": 0.0, "lon": 0.001},
                {"lat": 0.0, "lon": 0.010},
                {"lat": 0.0, "lon": -0.010},
                {"lat": 0.0, "lon": 0.005},
            ]
        )

        filtered = filter_by_center_distance(
            df,
            min_distance_meters=0,
            max_points=2,
        )

        self.assertEqual(len(filtered), 2)
        self.assertAlmostEqual(filtered.iloc[0]["lon"], 0.010)
        self.assertAlmostEqual(filtered.iloc[1]["lon"], -0.010)

    def test_filter_enforces_minimum_spacing(self):
        df = pd.DataFrame(
            [
                {"lat": 0.0, "lon": 0.0200},
                {"lat": 0.0, "lon": 0.0205},
                {"lat": 0.0, "lon": -0.0200},
            ]
        )

        filtered = filter_by_center_distance(
            df,
            min_distance_meters=100,
            max_points=None,
        )

        lons = set(round(lon, 4) for lon in filtered["lon"].tolist())
        self.assertTrue({0.0200, 0.0205}.intersection(lons))
        self.assertFalse({0.0200, 0.0205}.issubset(lons))

    def test_filter_preserves_original_input_order(self):
        df = pd.DataFrame(
            [
                {"lat": 0.0, "lon": 0.0001},
                {"lat": 0.0, "lon": 0.0200},
                {"lat": 0.0, "lon": -0.0200},
            ]
        )

        filtered = filter_by_center_distance(
            df,
            min_distance_meters=0,
            max_points=2,
        )

        self.assertEqual(filtered["lon"].tolist(), [0.0200, -0.0200])

    def test_filter_handles_empty_dataframe(self):
        df = pd.DataFrame(columns=["lat", "lon"])

        filtered = filter_by_center_distance(df)

        self.assertTrue(filtered.empty)

    def test_filter_rejects_invalid_max_points(self):
        df = pd.DataFrame([{"lat": 0.0, "lon": 0.0}])

        with self.assertRaises(ValueError):
            filter_by_center_distance(df, max_points=0)


if __name__ == "__main__":
    unittest.main()
