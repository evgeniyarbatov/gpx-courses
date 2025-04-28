import sys
import requests
import json

import pandas as pd

OSRM_URL = "http://localhost:6001/match/v1/bicycle/"

def get_trip(df, trip_csv_file):
    coords = ';'.join(f"{row.lon},{row.lat}" for row in df.itertuples(index=False))

    url = f"{OSRM_URL}{coords}?geometries=polyline6&overview=full&annotations=false&steps=false"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")

    trip_data = response.json()
    
    # with open(trip_csv_file, "w") as file:
    #     json.dump(trip_data, file, indent=4)
    
    coords = []
    if "tracepoints" in trip_data:
        for tracepoint in trip_data["tracepoints"]:
            if not tracepoint:
                continue
            
            (lon, lat) = tracepoint["location"]
            coords.append((lat, lon))
    
    trip_df = pd.DataFrame(coords, columns=['lat', 'lon'])
    trip_df.to_csv(trip_csv_file, index=False)

def main(csv_file, trip_csv_file):
    df = pd.read_csv(csv_file)
    get_trip(df, trip_csv_file)

if __name__ == "__main__":
    main(*sys.argv[1:])
