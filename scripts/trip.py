import sys
import requests
import json
import polyline

import pandas as pd

from geopy.distance import geodesic

OSRM_URL = "http://localhost:6000/trip/v1/foot/"

def get_trip(df, trip_csv_file):
    coords = ';'.join(f"{row.lon},{row.lat}" for row in df.itertuples(index=False))

    url = f"{OSRM_URL}{coords}?geometries=polyline6&overview=full&annotations=false&steps=false"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")

    trip_data = response.json()
    
    # with open(trip_csv_file, "w") as file:
    #     json.dump(trip_data, file, indent=4)
    
    encoded_geometry = trip_data['trips'][0]['geometry']
    coordinates = polyline.decode(encoded_geometry, precision=6) 
    
    df = pd.DataFrame(coordinates, columns=['lat', 'lon'])
    df.to_csv(trip_csv_file, index=False)
    
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
