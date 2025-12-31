import sys

import pandas as pd
import geopandas as gpd


def main(csv_file, boundary_file):
    df = pd.read_csv(csv_file)

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )

    # Step 3: Project to meters (so buffer is accurate)
    gdf_meters = gdf.to_crs(epsg=3857)  # Web Mercator (meters)

    # Step 4: Create convex hull around all points
    hull = gdf_meters.geometry.union_all().convex_hull

    # Step 5: Add 100 meter buffer
    buffered = hull.buffer(100)

    # Step 6: Convert back to lat/lon
    buffered_wgs84 = gpd.GeoSeries(buffered, crs="EPSG:3857").to_crs(epsg=4326)

    # Step 7: Extract coordinates
    coords = list(buffered_wgs84.iloc[0].exterior.coords)

    with open(boundary_file, "w") as f:
        f.write("boundary\n")
        for lon, lat in coords:
            f.write(f"   {lon:.6f}   {lat:.6f}\n")
        f.write("END\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
