import shutil
import subprocess
import unittest
from pathlib import Path

_make_path = shutil.which("make")
if _make_path is None:
    raise RuntimeError("make not found on PATH")
MAKE_PATH: str = _make_path


class MakefileTests(unittest.TestCase):
    def test_compress_uses_script_wrapper(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(  # noqa: S603
            [MAKE_PATH, "-n", "compress", "GPX_DIR=/tmp/input-gpx"],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn('scripts/compress.py "/tmp/input-gpx"', result.stdout)

    def test_parse_deletes_existing_data_gpx_files_first(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(  # noqa: S603
            [MAKE_PATH, "-n", "parse"],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn(
            'find data -type f -name "*.gpx" -delete',
            result.stdout,
        )

    def test_gpx_plots_trip_outputs_instead_of_compressed_inputs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(  # noqa: S603
            [MAKE_PATH, "-n", "gpx"],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn('scripts/plotgpx.py "data/trip-route-*.gpx"', result.stdout)
        self.assertNotIn("scripts/plotgpx.py data/gpx_compressed", result.stdout)


if __name__ == "__main__":
    unittest.main()
