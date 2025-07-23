import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import requests
import random
import time
import os
import folium
from folium.plugins import HeatMap
import json


def fetch_sample_postcodes(district, n_samples=10):
    """Fetch random sample of postcodes for a given district."""
    url = f"https://api.postcodes.io/postcodes?q={district}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Failed to fetch postcodes for {district}: {r.status_code}")
        return []
    results = r.json().get("result", [])
    all_postcodes = [r["postcode"] for r in results if r["postcode"].startswith(district)]
    return random.sample(all_postcodes, min(n_samples, len(all_postcodes)))

def bulk_geocode(postcodes):
    """Geocode a batch of postcodes using Postcodes.io API."""
    url = "https://api.postcodes.io/postcodes"
    headers = {"Content-Type": "application/json"}
    payload = {"postcodes": postcodes}
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code != 200:
        print(f"Geocode failed: {r.status_code}")
        return []
    results = r.json()["result"]
    return [
        {
            "postcode": res["query"],
            "lat": res["result"]["latitude"] if res["result"] else None,
            "lon": res["result"]["longitude"] if res["result"] else None
        }
        for res in results
    ]

def place_markers(city_name, center, districts, per_district_sample=3, use_csv=True):
    """Place markers for a city using postcodes, grid, and center points."""

    csv_file = f"data/{city_name.lower()}_coordinates.csv"

    # Use city-specific CSV file if it exists
    if use_csv and os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        required_cols = {"lat", "lon"}
        if not required_cols.issubset(df.columns):
            print(f"Invalid CSV structure in {csv_file}. Using automated points.")
        else:
            print(f"Loaded {len(df)} points from {csv_file}")
            return df
    
    # If CSV does not exist or is invalid, generate points
    # add points based on postcode sampling (move to a separate function)
    sampled_postcodes = []
    for d in districts:
        sampled_postcodes.extend(fetch_sample_postcodes(d, per_district_sample))
    
    batches = [sampled_postcodes[i:i+100] for i in range(0, len(sampled_postcodes), 100)]
    geo_data = []
    for batch in batches:
        geo_data.extend(bulk_geocode(batch))
    
    df = pd.DataFrame(geo_data).dropna()
    if df.empty:
        raise ValueError(f"No valid geocoded data for {city_name}")
    
    df = add_grid_points(df, grid_size=20, sample_frac=0.9)
    df = add_center_points(df, center)
    df = add_noise(df, center, scale="uniform", noise_level=0.05)
    df = add_center_points(df, center, n_points=1)
    df = add_grid_points(df, grid_size=10, sample_frac=1)
    
    # Save to CSV for future use
    df.to_csv(csv_file, index=False)
    print(f"Generated {len(df)} points for {city_name} and saved to {csv_file}")

    return df

def add_grid_points(df, grid_size=10, sample_frac=0.4):
    """Add randomly sampled grid points within the bounding box."""
    lat_min, lat_max = df["lat"].min(), df["lat"].max()
    lon_min, lon_max = df["lon"].min(), df["lon"].max()
    lat_vals = np.linspace(lat_min, lat_max, grid_size)
    lon_vals = np.linspace(lon_min, lon_max, grid_size)
    lat_grid, lon_grid = np.meshgrid(lat_vals, lon_vals)
    grid_df = pd.DataFrame({
        "lat": lat_grid.ravel(),
        "lon": lon_grid.ravel(),
        "postcode": "grid",
        "source": "grid"
    })
    sample_size = int(sample_frac * len(grid_df))
    sampled_grid = grid_df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    return pd.concat([df, sampled_grid], ignore_index=True)

def add_center_points(df, center_point, n_points=10):
    """Add multiple copies of the center point."""
    lat, lon = center_point
    center_df = pd.DataFrame({
        "lat": [lat] * n_points,
        "lon": [lon] * n_points,
        "postcode": "center",
        "source": "center"
    })
    return pd.concat([df, center_df], ignore_index=True)

def add_noise(df, center_point, scale="uniform", noise_level=0.5):
    """Add noise to coordinates to avoid clustering."""
    df = df.copy()
    if scale == "uniform":
        df["lat"] += np.random.uniform(-noise_level, noise_level, size=len(df))
        df["lon"] += np.random.uniform(-noise_level, noise_level, size=len(df))
    elif scale == "distance_scaled":
        center_lat, center_lon = center_point
        distances = np.sqrt((df["lat"] - center_lat)**2 + (df["lon"] - center_lon)**2)
        scaled_noise = noise_level * distances / distances.max()
        df["lat"] += np.random.uniform(-1, 1, size=len(df)) * scaled_noise
        df["lon"] += np.random.uniform(-1, 1, size=len(df)) * scaled_noise
    else:
        raise ValueError("scale must be 'uniform' or 'distance_scaled'")
    return df

def plot_points(df):
    """Plot markers on a Folium map."""
    try:
        if df is None or df.empty:
            raise ValueError("Empty or invalid DataFrame")
        center_lat = df["lat"].mean()
        center_lon = df["lon"].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        for _, row in df.iterrows():
            folium.Circle(
                location=[row["lat"], row["lon"]],
                radius=200,
                fill=True,
                fill_opacity=0.2,
                popup=f"({row['source']}, {row['lat']}, {row['lon']})"
            ).add_to(m)
        return m
    except Exception as e:
        print(f"Error plotting points: {str(e)}")
        return None

def load_city_data(city_name):
    """Load city data from JSON file."""
    with open("data/cities.json", "r") as file:
        cities = json.load(file)
    
    city = next((city for city in cities if city["name"].lower() == city_name.lower()), None)
    if not city:
        raise ValueError(f"City '{city_name}' not found in data.")

    return city


def main():
    os.makedirs("data", exist_ok=True)

    city_name = "Leeds"
    city = load_city_data(city_name)

    df = place_markers(city["name"], city["center"], city["districts"], per_district_sample=3, use_csv=True)

    m = plot_points(df)
    m.save("preprocessing/markers.html")


    print('\nMarkers placed:', len(df))
    print("Markers placed and map saved to preprocessing/markers.html")

if __name__ == "__main__":
    main()

