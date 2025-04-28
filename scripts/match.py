import sys
import requests

import pandas as pd

OSRM_URL = "http://localhost:6000/match/v1/foot/"
MATCH_RADIUS_METERS = 10

def get_matched_pair(coord1, coord2):
    coords_str = f"{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}"
    url = f"{OSRM_URL}{coords_str}?radiuses={MATCH_RADIUS_METERS};{MATCH_RADIUS_METERS}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        matched_coords = []
        if "tracepoints" in data:
            for tracepoint in data["tracepoints"]:
                (lon, lat) = tracepoint["location"]
                matched_coords.append((lat, lon))

        return matched_coords
    except requests.RequestException as e:
        return [coord1, coord2] 

def main(csv_file, matched_csv_file):
    df = pd.read_csv(csv_file)
    
    matched_data = set()
    for i in range(len(df) - 1):
        lat1, lon1 = df.iloc[i]['lat'], df.iloc[i]['lon']
        lat2, lon2 = df.iloc[i+1]['lat'], df.iloc[i+1]['lon']
        
        matched_coords = get_matched_pair(
            (lat1, lon1),
            (lat2, lon2),
        )
        
        for matched_coord in matched_coords:
            matched_data.add(matched_coord)    
    
    matched_df = pd.DataFrame(list(matched_data), columns=['lat', 'lon'])
    
    matched_df.to_csv(matched_csv_file, index=False)

if __name__ == "__main__":
    main(*sys.argv[1:])
