import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from scripts import ways


class WaysTests(unittest.TestCase):
    def test_write_csv_maps_way_nodes_to_coordinate_lists(self):
        nodes = {
            1: (21.0, 105.0),
            2: (21.1, 105.1),
            3: (21.2, 105.2),
        }
        way_map = {
            10: [1, 2, 9],
            20: [3],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_csv = Path(tmpdir) / "ways.csv"
            ways.write_csv(nodes, way_map, output_csv)
            written = pd.read_csv(output_csv)

        self.assertEqual(list(written.columns), ["way_id", "nodes"])
        self.assertEqual(written["way_id"].tolist(), [10, 20])
        self.assertIn("(21.0, 105.0)", written.iloc[0]["nodes"])
        self.assertIn("(21.1, 105.1)", written.iloc[0]["nodes"])
        self.assertNotIn("9", written.iloc[0]["nodes"])

    def test_main_applies_handler_and_writes_csv(self):
        fake_handler = mock.Mock()
        fake_handler.nodes = {1: (21.0, 105.0)}
        fake_handler.ways = {10: [1]}

        with mock.patch("scripts.ways.WayNodeHandler", return_value=fake_handler):
            with mock.patch("scripts.ways.write_csv") as mock_write_csv:
                ways.main("input.osm", "out.csv")

        fake_handler.apply_file.assert_called_once_with("input.osm", locations=True)
        mock_write_csv.assert_called_once_with(fake_handler.nodes, fake_handler.ways, "out.csv")


if __name__ == "__main__":
    unittest.main()
