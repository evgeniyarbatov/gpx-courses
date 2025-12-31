import sys
import glob
import gpxpy
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx

from shapely.geometry import LineString


def plot(gpx_files, title, gpx_plot_filename):
    colors = plt.get_cmap("tab20", len(gpx_files))

    gdfs = []

    for idx, gpx_file in enumerate(gpx_files):
        with open(gpx_file, "r") as f:
            gpx = gpxpy.parse(f)

        lines = []
        for track in gpx.tracks:
            for segment in track.segments:
                coords = [(point.longitude, point.latitude) for point in segment.points]
                if len(coords) > 1:
                    lines.append(LineString(coords))

        if lines:
            gdf = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326")
            gdf["name"] = os.path.basename(gpx_file)
            gdfs.append((gdf, colors(idx)))

    fig, ax = plt.subplots(figsize=(12, 10))
    for gdf, color in gdfs:
        gdf.to_crs(epsg=3857).plot(
            ax=ax, color=color, linewidth=5, label=gdf["name"].iloc[0]
        )

    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, attribution=False)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(
        axis="both", which="both", bottom=False, top=False, left=False, right=False
    )

    plt.legend()
    plt.tight_layout()
    plt.title(title)
    plt.savefig(gpx_plot_filename, dpi=300, bbox_inches="tight")


def main(
    gpx_dir,
    title,
    gpx_plot_filename,
):
    gpx_files = glob.glob(os.path.join(gpx_dir, "*.gpx"))

    plot(gpx_files, title, gpx_plot_filename)


if __name__ == "__main__":
    main(*sys.argv[1:])
