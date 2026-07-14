import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.extract import main

SIMPLE_GPX = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<gpx version=\"1.1\" creator=\"test\">
  <trk>
    <name>T</name>
    <trkseg>
      <trkpt lat=\"21.0\" lon=\"105.0\" />
      <trkpt lat=\"21.1\" lon=\"105.1\" />
    </trkseg>
  </trk>
</gpx>
"""


class ExtractTests(unittest.TestCase):
    def test_main_extracts_points_from_all_gpx_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "gpx"
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "a.gpx").write_text(SIMPLE_GPX, encoding="utf-8")
            (source_dir / "b.gpx").write_text(SIMPLE_GPX, encoding="utf-8")
            (source_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            output_csv = Path(tmpdir) / "points.csv"
            main(str(source_dir), str(output_csv))

            written = pd.read_csv(output_csv)

        self.assertEqual(list(written.columns), ["lat", "lon"])
        self.assertEqual(len(written), 4)
        rows = zip(written["lat"].tolist(), written["lon"].tolist(), strict=True)
        self.assertEqual(
            sorted((round(lat, 3), round(lon, 3)) for lat, lon in rows),
            [(21.0, 105.0), (21.0, 105.0), (21.1, 105.1), (21.1, 105.1)],
        )


if __name__ == "__main__":
    unittest.main()
