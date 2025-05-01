import sys
import requests
import ast

import pandas as pd

from haversine import haversine

OSRM_ROUTE_URL = "http://localhost:6000/route/v1/foot/"

def get_osrm_route_distance(start_lat, start_lon, end_lat, end_lon):
    url = f"{OSRM_ROUTE_URL}{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200 and 'routes' in data:
        return data['routes'][0]['distance']
    else:
        return float('inf')  # fallback if request fails
    
def get_closest_point_in_straight_line(df, lat, lon):
    df['distance'] = df.apply(
        lambda row: haversine((lat, lon), (row['lat'], row['lon'])),
        axis=1
    )
    
    closest_point_idx = df['distance'].idxmin()
    closest_point = df.loc[closest_point_idx]

    return closest_point['lat'], closest_point['lon']

def sort_df(df, start_lat, start_lon):
    df = df.copy()
    df['ways'] = df['ways'].apply(lambda x: [int(w) for w in ast.literal_eval(x)])

    sorted_rows = []
    
    current_lat, current_lon = get_closest_point_in_straight_line(
        df, 
        start_lat, 
        start_lon,
    )

    while not df.empty:
        print(len(df))

        if sorted_rows:
            current_ways = sorted_rows[-1]['ways']
        else:
            current_ways = df.iloc[0]['ways']

        df['shares_way'] = df['ways'].apply(lambda ws: any(w in current_ways for w in ws))
        shared_way_df = df[df['shares_way']]
        
        candidate_df = shared_way_df if not shared_way_df.empty else df
        candidate_df = candidate_df.copy()

        if not shared_way_df.empty:
            candidate_df['distance'] = candidate_df.apply(
                lambda row: get_osrm_route_distance(current_lat, current_lon, row['lat'], row['lon']),
                axis=1
            )
        else:
            candidate_df['distance'] = candidate_df.apply(
                lambda row: haversine((current_lat, current_lon), (row['lat'], row['lon'])),
                axis=1
            )

        next_point_idx = candidate_df['distance'].idxmin()
        next_point = df.loc[next_point_idx]

        sorted_rows.append(next_point)
        current_lat, current_lon = next_point['lat'], next_point['lon']
        df = df.drop(index=next_point_idx)

    return pd.DataFrame(sorted_rows)
        
def main(
    start_lat, 
    start_lon,
    gpx_csv_file, 
    sorted_gpx_csv_file,
):
    df = pd.read_csv(gpx_csv_file)

    df = sort_df(df, float(start_lat), float(start_lon))

    df.to_csv(sorted_gpx_csv_file, index=False)

if __name__ == "__main__":
    main(*sys.argv[1:])
