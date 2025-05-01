import sys

import pandas as pd
import matplotlib.pyplot as plt
import contextily as ctx 

def make_plot(df, plot_filename):
    fig, ax = plt.subplots(1, 1, figsize=(20, 10), dpi=300)

    lons, lats = df['lon'], df['lat']
    ax.scatter(lons, lats, color='red', marker='o')
    ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik, attribution=False)
    
    ax.set_xlim(min(lons), max(lons))
    ax.set_ylim(min(lats), max(lats))
    
    ax.set_aspect('equal', adjustable='datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False)
    
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.margins(0)
    plt.savefig(plot_filename, bbox_inches='tight', pad_inches=0)
    
    plt.close()

def main(
    input_filename,
	plot_filename,
):
    df = pd.read_csv(input_filename)
    make_plot(df, plot_filename)
    
if __name__ == "__main__":
	main(*sys.argv[1:])