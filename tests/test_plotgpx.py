import tempfile
import unittest
from pathlib import Path

from scripts.plotgpx import resolve_gpx_files


class PlotGpxTests(unittest.TestCase):
    def test_resolve_gpx_files_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "b.gpx").write_text("<gpx/>", encoding="utf-8")
            (base / "a.gpx").write_text("<gpx/>", encoding="utf-8")
            (base / "notes.txt").write_text("ignore", encoding="utf-8")

            self.assertEqual(
                resolve_gpx_files(str(base)),
                [str(base / "a.gpx"), str(base / "b.gpx")],
            )

    def test_resolve_gpx_files_from_glob_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "trip-route-02.gpx").write_text("<gpx/>", encoding="utf-8")
            (base / "trip-route-01.gpx").write_text("<gpx/>", encoding="utf-8")

            self.assertEqual(
                resolve_gpx_files(str(base / "trip-route-*.gpx")),
                [str(base / "trip-route-01.gpx"), str(base / "trip-route-02.gpx")],
            )

    def test_resolve_gpx_files_raises_for_empty_result(self) -> None:
        with self.assertRaises(ValueError):
            resolve_gpx_files("data/does-not-exist/*.gpx")


if __name__ == "__main__":
    unittest.main()
