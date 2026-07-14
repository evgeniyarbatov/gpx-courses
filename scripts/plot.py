import sys

import contextily as ctx
import matplotlib.pyplot as plt
import pandas as pd


def make_plot(df: pd.DataFrame, title: str, plot_filename: str) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(20, 10), dpi=300)

    lons, lats = df["lon"], df["lat"]
    ax.scatter(lons, lats, color="red", marker="o")
    ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.CartoDB.Positron, attribution=False)

    ax.set_xlim(min(lons), max(lons))
    ax.set_ylim(min(lats), max(lats))

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(axis="both", which="both", bottom=False, top=False, left=False, right=False)

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.margins(0)

    plt.title(title)
    plt.savefig(plot_filename, bbox_inches="tight")

    plt.close()


def main(
    input_filename: str,
    title: str,
    plot_filename: str,
) -> None:
    df = pd.read_csv(input_filename)
    make_plot(df, title, plot_filename)


if __name__ == "__main__":
    main(*sys.argv[1:])
