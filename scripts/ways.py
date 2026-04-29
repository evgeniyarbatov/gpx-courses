import argparse
import osmium

import pandas as pd

DEFAULT_OSM_FILE = "osm/gpx.osm"
DEFAULT_WAYS_CSV = "data/osm-ways.csv"


class WayNodeHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.ways = {}

    def node(self, n):
        self.nodes[n.id] = (n.location.lat, n.location.lon)

    def way(self, w):
        self.ways[w.id] = [n.ref for n in w.nodes]


def write_csv(
    nodes,
    ways,
    filename,
):
    data = []

    for way_id, node_ids in ways.items():
        coords = [nodes.get(nid) for nid in node_ids if nid in nodes]
        data.append({"way_id": way_id, "nodes": coords})

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)


def main(
    osm_filename,
    osm_ways_filename,
):
    handler = WayNodeHandler()

    handler.apply_file(osm_filename, locations=True)

    write_csv(
        handler.nodes,
        handler.ways,
        osm_ways_filename,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract OSM way IDs and node coordinates into CSV."
    )
    parser.add_argument("osm_filename", nargs="?", default=DEFAULT_OSM_FILE)
    parser.add_argument("osm_ways_filename", nargs="?", default=DEFAULT_WAYS_CSV)
    args = parser.parse_args()
    main(args.osm_filename, args.osm_ways_filename)
