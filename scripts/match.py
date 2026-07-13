import argparse
import os

import pandas as pd
import requests

OSRM_URL = "http://localhost:6000/match/v1/foot/"
OVERPASS_API_URL = os.getenv("OVERPASS_API_URL", "http://localhost:18080/api/interpreter")
MATCH_RADIUS_METERS = 20
DEFAULT_GPX_CSV = "data/gpx.csv"
DEFAULT_MATCHED_CSV = "data/osm-gpx.csv"


def get_nodes(lat, lon):
    response = requests.get(f"http://127.0.0.1:6000/nearest/v1/foot/{lon},{lat}")
    response.raise_for_status()

    data = response.json()
    if "waypoints" not in data:
        return []

    waypoints = data["waypoints"]
    return [int(node) for wp in waypoints for node in wp["nodes"]]


def get_ways(nodes):
    node_1, node_2 = nodes
    overpass_query = f"""
        [out:json];
        node(id:{node_1},{node_2});
        way(bn);
        out ids;
    """

    response = requests.get(OVERPASS_API_URL, params={"data": overpass_query})
    data = response.json()

    way_ids = [element["id"] for element in data.get("elements", []) if element["type"] == "way"]
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

                matched_coords.append([lat, lon, ways])
        return matched_coords
    except requests.RequestException:
        return None


def main(csv_file, matched_csv_file):
    df = pd.read_csv(csv_file)

    matched_data = []
    for i in range(len(df) - 1):
        lat1, lon1 = df.iloc[i]["lat"], df.iloc[i]["lon"]
        lat2, lon2 = df.iloc[i + 1]["lat"], df.iloc[i + 1]["lon"]

        matched_coords = get_matched_pair((lat1, lon1), (lat2, lon2))
        if not matched_coords:
            continue

        for coord in matched_coords:
            lat, lon, ways = coord[0], coord[1], coord[2]
            if not ways:
                continue

            matched_data.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "ways": ways,
                }
            )

    matched_df = pd.DataFrame(matched_data)

    matched_df = matched_df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)

    matched_df.to_csv(matched_csv_file, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Match GPX points to OSM ways via local OSRM and Overpass."
    )
    parser.add_argument("csv_file", nargs="?", default=DEFAULT_GPX_CSV)
    parser.add_argument("matched_csv_file", nargs="?", default=DEFAULT_MATCHED_CSV)
    args = parser.parse_args()
    main(args.csv_file, args.matched_csv_file)
