import shutil
import subprocess
import unittest
from pathlib import Path

_make_path = shutil.which("make")
if _make_path is None:
    raise RuntimeError("make not found on PATH")
MAKE_PATH: str = _make_path

TEST_DATA_ROOT = "/tmp/gpx-courses-test-data"
TEST_DATA_DIR = f"{TEST_DATA_ROOT}/gpx-courses"


class MakefileTests(unittest.TestCase):
    def _dry_run(self, *args: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(  # noqa: S603
            [MAKE_PATH, "-n", *args, f"DATA_ROOT={TEST_DATA_ROOT}"],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout

    def test_compress_uses_script_wrapper(self) -> None:
        stdout = self._dry_run("compress", "GPX_DIR=/tmp/input-gpx")

        self.assertIn('scripts/compress.py "/tmp/input-gpx"', stdout)
        self.assertIn(f"--output-dir {TEST_DATA_DIR}/gpx_compressed", stdout)

    def test_parse_deletes_existing_data_gpx_files_first(self) -> None:
        stdout = self._dry_run("parse")

        self.assertIn(
            f'find {TEST_DATA_DIR} -type f -name "*.gpx" -delete',
            stdout,
        )

    def test_gpx_plots_trip_outputs_instead_of_compressed_inputs(self) -> None:
        stdout = self._dry_run("gpx", 'NAME=Test')

        self.assertIn(f'scripts/plotgpx.py "{TEST_DATA_DIR}/trip-route-*.gpx"', stdout)
        self.assertNotIn(f"scripts/plotgpx.py {TEST_DATA_DIR}/gpx_compressed", stdout)


if __name__ == "__main__":
    unittest.main()
