import sys
import requests
import json

import pandas as pd

from geopy.distance import geodesic

OSRM_URL = "http://localhost:6001/trip/v1/bicycle/"

def get_trip(df, trip_csv_file):
    coords = ';'.join(f"{row.lon},{row.lat}" for row in df.itertuples(index=False))

    url = f"{OSRM_URL}{coords}?geometries=polyline6&overview=full&annotations=false&steps=false"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")

    trip_data = response.json()
    
    # with open(trip_csv_file, "w") as file:
    #     json.dump(trip_data, file, indent=4)
    
    waypoints = trip_data['waypoints']
    
    sorted_waypoints = sorted(
        waypoints,
        key=lambda w: (w['trips_index'], w['waypoint_index'])
    )
    
    coords = []
    for waypoint in sorted_waypoints:
        lat = waypoint['location'][1]
        lon = waypoint['location'][0]
        
        trips_index = waypoint['trips_index']
        
        coords.append({
            'trips_index': trips_index,
            'lat': lat,
            'lon': lon,
        })
    
    trip_df = pd.DataFrame(coords)
    trip_df.to_csv(trip_csv_file, index=False)
    
def sort_df(df, start_lat, start_lon):
    starting_point = (start_lat, start_lon)
    
    def calculate_distance(row):
        return geodesic(starting_point, (row['lat'], row['lon'])).m

    df['distance'] = df.apply(calculate_distance, axis=1)
    df_sorted = df.sort_values(by='distance')
    
    df_sorted = df_sorted.drop(columns=['distance'])
    return df_sorted
    
def main(
    start_lat,
    start_lon,
    gpx_csv_file, 
    trip_csv_file,
):
    df = pd.read_csv(gpx_csv_file)
    
    df = sort_df(df, start_lat, start_lon)
    
    get_trip(df, trip_csv_file)

if __name__ == "__main__":
    main(*sys.argv[1:])
