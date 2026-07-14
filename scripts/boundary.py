import argparse

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

DEFAULT_GPX_CSV = "data/gpx.csv"
DEFAULT_BOUNDARY_POLY = "data/boundary.poly"


def main(csv_file: str, boundary_file: str) -> None:
    df = pd.read_csv(csv_file)

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")

    # Step 3: Project to meters (so buffer is accurate)
    gdf_meters = gdf.to_crs(epsg=3857)  # Web Mercator (meters)

    # Step 4: Create convex hull around all points
    hull = gdf_meters.geometry.union_all().convex_hull

    # Step 5: Add 100 meter buffer
    buffered = hull.buffer(100)

    # Step 6: Convert back to lat/lon
    buffered_wgs84 = gpd.GeoSeries(buffered, crs="EPSG:3857").to_crs(epsg=4326)

    # Step 7: Extract coordinates
    buffered_geometry = buffered_wgs84.iloc[0]
    if not isinstance(buffered_geometry, Polygon):
        raise TypeError(f"Expected a buffered Polygon boundary, got {type(buffered_geometry)}.")
    coords = list(buffered_geometry.exterior.coords)

    with open(boundary_file, "w") as f:
        f.write("boundary\n")
        for lon, lat in coords:
            f.write(f"   {lon:.6f}   {lat:.6f}\n")
        f.write("END\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a buffered convex-hull boundary .poly from GPX CSV points."
    )
    parser.add_argument("csv_file", nargs="?", default=DEFAULT_GPX_CSV)
    parser.add_argument("boundary_file", nargs="?", default=DEFAULT_BOUNDARY_POLY)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main(args.csv_file, args.boundary_file)
