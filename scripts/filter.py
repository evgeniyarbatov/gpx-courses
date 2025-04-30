import sys
import ast

import pandas as pd

def filter_df(df):
    df['ways'] = df['ways'].apply(ast.literal_eval)
    exploded = df.explode('ways')

    way_counts = exploded['ways'].value_counts()
    p50 = way_counts.quantile(0.5)
    
    popular_ways = set(way_counts[way_counts > p50].index)    
    df['has_popular_way'] = df['ways'].apply(lambda ways: any(way in popular_ways for way in ways))

    filtered_df = df[df['has_popular_way']].drop(columns='has_popular_way')
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
