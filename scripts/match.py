import sys
import requests
import json

import pandas as pd

OSRM_URL = "http://localhost:6000/match/v1/foot/"
MATCH_RADIUS_METERS = 10

def get_nodes(lat, lon):
    response = requests.get(f"http://127.0.0.1:6000/nearest/v1/foot/{lon},{lat}")
    response.raise_for_status()

    data = response.json()
    if not 'waypoints' in data:
        return []

    waypoints = data['waypoints']
    return [node for wp in waypoints for node in wp['nodes']]
      
def get_ways(nodes):
    node_1, node_2 = nodes
    overpass_query = f"""
        [out:json];
        node(id:{node_1},{node_2});
        way(bn);
        out ids;
    """
    print(overpass_query)
    response = requests.get(
        "http://localhost:8000/api/interpreter", 
        params={'data': overpass_query}
    )
    data = response.json()

    way_ids = [element['id'] for element in data.get('elements', []) if element['type'] == 'way']
    return way_ids
      
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
                
                nodes = get_nodes(lat, lon)
                ways = get_ways(nodes)
                
                matched_coords.append((lat, lon, ways))
        return matched_coords
    except requests.RequestException as e:
        return [coord1, coord2, []] 

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
        print(matched_coords)
        
        for matched_coord in matched_coords:
            matched_data.add(matched_coord)    
    
    matched_df = pd.DataFrame(list(matched_data), columns=['lat', 'lon', 'ways'])
    
    matched_df.to_csv(matched_csv_file, index=False)

if __name__ == "__main__":
    main(*sys.argv[1:])
