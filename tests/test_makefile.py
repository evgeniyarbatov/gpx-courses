import subprocess
import unittest
from pathlib import Path


class MakefileTests(unittest.TestCase):
    def test_parse_deletes_existing_data_gpx_files_first(self):
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["make", "-n", "parse"],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn(
            'find data -type f -name "*.gpx" -delete',
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
