import sys
import ast

import pandas as pd

def filter_df(df):
    df['ways'] = df['ways'].apply(lambda x: [int(w) for w in ast.literal_eval(x)])
    exploded = df.explode('ways')

    way_counts = exploded['ways'].value_counts()
    common_ways = set(way_counts[way_counts > 1].index)

    df['has_common_way'] = df['ways'].apply(
        lambda ways: all(way in common_ways for way in ways)
    )
    filtered_df = df[df['has_common_way']].drop(columns='has_common_way')
    
    return filtered_df

def main(
    gpx_csv_file, 
    filtered_gpx_csv_file,
):
    df = pd.read_csv(gpx_csv_file)

    df = filter_df(df)

    df.to_csv(filtered_gpx_csv_file, index=False)

if __name__ == "__main__":
    main(*sys.argv[1:])
