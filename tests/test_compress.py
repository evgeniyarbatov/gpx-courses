import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.compress import _compress_one_file, main


class CompressTests(unittest.TestCase):
    def test_compress_one_file_invokes_gpsbabel_with_expected_args(self):
        with mock.patch("scripts.compress.subprocess.run") as mock_run:
            _compress_one_file(Path("src.gpx"), Path("dst.gpx"))

        mock_run.assert_called_once_with(
            [
                "gpsbabel",
                "-i",
                "gpx",
                "-f",
                "src.gpx",
                "-x",
                "simplify,crosstrack,error=0.01k",
                "-o",
                "gpx",
                "-F",
                "dst.gpx",
            ],
            check=True,
        )

    def test_main_raises_when_input_directory_has_no_gpx_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit) as err:
                main(tmpdir)

        self.assertIn("No .gpx files found", str(err.exception))

    def test_main_processes_all_gpx_files_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "out"
            source_dir.mkdir(parents=True, exist_ok=True)

            (source_dir / "b.gpx").write_text("<gpx/>", encoding="utf-8")
            (source_dir / "a.gpx").write_text("<gpx/>", encoding="utf-8")
            (source_dir / "readme.txt").write_text("skip", encoding="utf-8")

            with mock.patch("scripts.compress._compress_one_file") as mock_compress:
                main(source_dir, output_dir)

        self.assertEqual(mock_compress.call_count, 2)
        first_source, first_target = mock_compress.call_args_list[0].args
        second_source, second_target = mock_compress.call_args_list[1].args

        self.assertEqual(first_source.name, "a.gpx")
        self.assertEqual(second_source.name, "b.gpx")
        self.assertEqual(first_target, output_dir / "a.gpx")
        self.assertEqual(second_target, output_dir / "b.gpx")


if __name__ == "__main__":
    unittest.main()
