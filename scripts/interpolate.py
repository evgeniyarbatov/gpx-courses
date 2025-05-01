import sys
import ast

import pandas as pd

from shapely.geometry import LineString, Point
from pyproj import Geod

geod = Geod(ellps="WGS84")

def interpolate_way(way_id, coords):
    if len(coords) < 2:
        return []

    line = LineString([(lon, lat) for lat, lon in coords])
    length = geod.geometry_length(line)
    
    result = []
    for dist_m in range(0, int(length), 1):
        point = line.interpolate(dist_m / length, normalized=True)
        result.append((point.y, point.x, way_id))

    return result

def get_ways(gpx_df):
    gpx_df['ways'] = gpx_df['ways'].apply(lambda x: [int(w) for w in ast.literal_eval(x)])

    unique_ways = set()
    for way_list in gpx_df['ways']:
        unique_ways.update(way_list)

    return unique_ways   

def get_way_nodes(way_id, osm_ways_df):
    row = osm_ways_df[osm_ways_df['way_id'] == way_id]
    if row.empty:
        return None 
    
    nodes_str = row.iloc[0]['nodes']
    nodes = ast.literal_eval(nodes_str)
    
    return nodes    

def main(
    osm_ways_filename,
	gpx_csv_file,
    interpolated_filename,
):
    osm_ways_df = pd.read_csv(osm_ways_filename)
    gpx_df = pd.read_csv(gpx_csv_file)
    
    all_points = []
    
    ways = get_ways(gpx_df)
    for way_id in ways:
        nodes = get_way_nodes(way_id, osm_ways_df)
        points = interpolate_way(way_id, nodes)
        all_points.extend(points)

    result_df = pd.DataFrame(all_points, columns=['lat', 'lon', 'way_id'])
    result_df.to_csv(interpolated_filename, index=False)
    
if __name__ == "__main__":
	main(*sys.argv[1:])