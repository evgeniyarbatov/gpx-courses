import tempfile
import unittest
from pathlib import Path

from scripts.boundary import main


class BoundaryTests(unittest.TestCase):
    def test_main_writes_poly_boundary_file(self):
        csv_content = "lat,lon\n21.0000,105.0000\n21.0100,105.0100\n21.0200,105.0050\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_csv = Path(tmpdir) / "gpx.csv"
            output_poly = Path(tmpdir) / "boundary.poly"
            input_csv.write_text(csv_content, encoding="utf-8")

            main(str(input_csv), str(output_poly))

            lines = output_poly.read_text(encoding="utf-8").strip().splitlines()

        self.assertGreaterEqual(len(lines), 6)
        self.assertEqual(lines[0], "boundary")
        self.assertEqual(lines[-1], "END")

        for line in lines[1:-1]:
            parts = line.split()
            self.assertEqual(len(parts), 2)
            float(parts[0])
            float(parts[1])


if __name__ == "__main__":
    unittest.main()
