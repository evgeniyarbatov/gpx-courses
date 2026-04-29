import argparse
import subprocess
from pathlib import Path

DEFAULT_COMPRESSED_GPX_DIR = Path("data/gpx_compressed")


def _compress_one_file(source_path, target_path):
    subprocess.run(
        [
            "gpsbabel",
            "-i",
            "gpx",
            "-f",
            str(source_path),
            "-x",
            "simplify,crosstrack,error=0.01k",
            "-o",
            "gpx",
            "-F",
            str(target_path),
        ],
        check=True,
    )


def main(input_gpx_dir, output_gpx_dir=DEFAULT_COMPRESSED_GPX_DIR):
    source_dir = Path(input_gpx_dir)
    output_dir = Path(output_gpx_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gpx_files = sorted(source_dir.glob("*.gpx"))
    if not gpx_files:
        raise SystemExit(f"No .gpx files found in input directory: {source_dir}")

    for source_path in gpx_files:
        target_path = output_dir / source_path.name
        _compress_one_file(source_path, target_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simplify GPX files with gpsbabel into data/gpx_compressed."
    )
    parser.add_argument("input_gpx_dir", help="Directory containing source .gpx files.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_COMPRESSED_GPX_DIR),
        help="Directory to write compressed .gpx files.",
    )
    args = parser.parse_args()
    main(args.input_gpx_dir, args.output_dir)
