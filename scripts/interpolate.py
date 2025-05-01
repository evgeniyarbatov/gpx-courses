import sys
import ast
import csv

import pandas as pd

from shapely.geometry import LineString, Point
from pyproj import Geod

INTERPOLATE_DISTANCE_METERS = 10
MIN_WAY_LENGTH_METERS = 200

geod = Geod(ellps="WGS84")

def find_closest_index(line_coords, target):
    return min(range(len(line_coords)), key=lambda i: Point(line_coords[i][1], line_coords[i][0]).distance(Point(target[1], target[0])))

def interpolate_way(way_id, way_coords, points_by_way):    
    indices = [find_closest_index(way_coords, pt) for pt in points_by_way[way_id]]
    start_idx, stop_idx = min(indices), max(indices)

    segment_coords = way_coords[start_idx:stop_idx+1]
    if len(segment_coords) < 2:
        return []

    line = LineString([(lon, lat) for lat, lon in segment_coords])
    
    length = geod.geometry_length(line)
    if length < MIN_WAY_LENGTH_METERS:
        return []
    
    result = []
    for dist_m in range(0, int(length), INTERPOLATE_DISTANCE_METERS):
        point = line.interpolate(dist_m / length, normalized=True)
        result.append((point.y, point.x, [way_id]))

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

def get_points_by_way(csv_file):
    points_by_way = {}

    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["lat"])
            lon = float(row["lon"])
            way_ids = ast.literal_eval(row["ways"])
            for way_id in way_ids:
                points_by_way.setdefault(way_id, []).append((lat, lon))
                
    return points_by_way    
    
def main(
    osm_ways_filename,
	gpx_csv_file,
    interpolated_filename,
):
    osm_ways_df = pd.read_csv(osm_ways_filename)
    gpx_df = pd.read_csv(gpx_csv_file)
    
    all_points = []
    points_by_way = get_points_by_way(gpx_csv_file)
    
    ways = get_ways(gpx_df)
    for way_id in ways:
        nodes = get_way_nodes(way_id, osm_ways_df)
        points = interpolate_way(way_id, nodes, points_by_way)
        
        if points:
            all_points.extend(points)

    result_df = pd.DataFrame(all_points, columns=['lat', 'lon', 'ways'])
    result_df.to_csv(interpolated_filename, index=False)
    
if __name__ == "__main__":
	main(*sys.argv[1:])