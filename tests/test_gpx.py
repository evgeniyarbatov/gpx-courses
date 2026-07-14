import tempfile
import unittest
from pathlib import Path

import gpxpy
import pandas as pd

from scripts.gpx import write_gpx_files


class GpxTests(unittest.TestCase):
    def test_write_single_route_file(self) -> None:
        df = pd.DataFrame(
            [
                {"lat": 21.0, "lon": 105.0},
                {"lat": 21.1, "lon": 105.1},
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "trip.gpx"
            output_paths = write_gpx_files(df, "Test Trip", output)

            self.assertEqual(output_paths, [str(output)])
            self.assertTrue(output.exists())

            with output.open("r") as f:
                gpx = gpxpy.parse(f)

            self.assertEqual(len(gpx.tracks), 1)
            self.assertEqual(len(gpx.tracks[0].segments), 1)
            self.assertEqual(len(gpx.tracks[0].segments[0].points), 2)

    def test_write_multi_route_files(self) -> None:
        df = pd.DataFrame(
            [
                {"lat": 21.0, "lon": 105.0, "route_id": 2},
                {"lat": 21.1, "lon": 105.1, "route_id": 2},
                {"lat": 20.0, "lon": 104.0, "route_id": 1},
                {"lat": 20.1, "lon": 104.1, "route_id": 1},
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "trip.gpx"
            output_paths = write_gpx_files(df, "Split Trip", output)

            expected_paths = [
                str(Path(tmpdir) / "trip-route-01.gpx"),
                str(Path(tmpdir) / "trip-route-02.gpx"),
            ]
            self.assertEqual(output_paths, expected_paths)
            self.assertTrue(Path(expected_paths[0]).exists())
            self.assertTrue(Path(expected_paths[1]).exists())


if __name__ == "__main__":
    unittest.main()
