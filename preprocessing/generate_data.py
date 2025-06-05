import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import os
import requests
import random
import time
from dotenv import load_dotenv
import folium
from folium.plugins import MarkerCluster


def get_google_api_key():
    """Retrieve Google API key from environment variable."""

    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Set the GOOGLE_MAPS_API_KEY environment variable.")
    return api_key

def fetch_sample_postcodes(district, n_samples=10):
    """Fetch random sample of postcodes for a given district prefix."""
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

def add_grid_points(df, grid_size=50, sample_frac=0.2):
    """Add randomly sampled grid points within the bounding box."""
    lat_min, lat_max = df["lat"].min(), df["lat"].max()
    lon_min, lon_max = df["lon"].min(), df["lon"].max()

    lat_vals = np.linspace(lat_min, lat_max, grid_size)
    lon_vals = np.linspace(lon_min, lon_max, grid_size)
    lat_grid, lon_grid = np.meshgrid(lat_vals, lon_vals)

    grid_df = pd.DataFrame({
        "lat": lat_grid.ravel(),
        "lon": lon_grid.ravel()
    })

    sample_size = int(sample_frac * len(grid_df))
    sampled_grid = grid_df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    sampled_grid["postcode"] = "grid"
    
    return pd.concat([df, sampled_grid], ignore_index=True)

def add_center_points(df, center_point, n_points=20):
    """Add multiple copies of the center point."""
    lat, lon = center_point
    center_df = pd.DataFrame({
        "lat": [lat] * n_points,
        "lon": [lon] * n_points,
        "postcode": ["center"] * n_points
    })
    return pd.concat([df, center_df], ignore_index=True)

def add_noise(df, center_point, scale="uniform", noise_level=0.001):
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

def place_markers(city_name, center, districts, per_district_sample=3):
    """Place markers for a city using postcodes, grid, and center points."""
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
    
    df = add_grid_points(df, grid_size=10, sample_frac=0.1)
    df = add_center_points(df, center, n_points=10)
    df = add_noise(df, center, scale="uniform", noise_level=0.01)
    
    return df

def calculate_travel_times(df, center, api_key, mode="transit"):
    """Calculate travel times from center to points using Google Maps API."""
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    origins = f"{center[0]},{center[1]}"
    travel_times = []

    for _, row in df.iterrows():
        destination = f"{row['lat']},{row['lon']}"
        params = {
            "origins": origins,
            "destinations": destination,
            "mode": mode,
            "key": api_key
        }
        response = requests.get(base_url, params=params)
        data = response.json()

        try:
            duration_seconds = data["rows"][0]["elements"][0]["duration"]["value"]
            travel_times.append(duration_seconds / 60)
        except (KeyError, IndexError, TypeError):
            travel_times.append(None)
        
        time.sleep(0.1)  # Reduced delay; adjust based on API limits

    df = df.copy()
    df["travel_time_mins"] = travel_times
    return df.dropna(subset=["travel_time_mins"])

def interpolate_meshgrid(df, center_lat):
    """
    Interpolate travel times onto a regular grid.
    
    Args:
        df: DataFrame with 'lat', 'lon', 'travel_time_mins' columns.
        center_lat: Latitude for aspect ratio correction.
    
    Returns:
        grid_z, lon_lin, lat_lin: Interpolated grid and grid coordinates.
    """
    lats = df["lat"].values
    lons = df["lon"].values
    times = df["travel_time_mins"].values

    grid_res = 200  # Adjust for file size vs. quality
    lon_lin = np.linspace(lons.min(), lons.max(), grid_res)
    lat_lin = np.linspace(lats.min(), lats.max(), grid_res)
    lon_grid, lat_grid = np.meshgrid(lon_lin, lat_lin)

    grid_z = griddata(
        points=(lons, lats),
        values=times,
        xi=(lon_grid, lat_grid),
        method='linear' # linear or cubic TEST OUT 
    )

    grid_z = gaussian_filter(grid_z, sigma=3) # Smooth the grid, test what works best

    return grid_z, lon_lin, lat_lin

def save_pkl(city_name, center, grid_z, lon_lin, lat_lin, output_pkl):
    """Save preprocessed .pkl for a city.

    Args:
        city_name (str): Name of the city (e.g., "Leeds").
        center (list): [latitude, longitude] of city center.
        grid_z (np.ndarray): 2D array of interpolated travel times.
        lon_lin (np.ndarray): 1D array of longitude grid points.
        lat_lin (np.ndarray): 1D array of latitude grid points.
        output_pkl (str): Path to save the .pkl file.
    """
            
    output_data = {
        "city_name": city_name,
        "center": center,
        "grid_z": grid_z,
        "lon_lin": lon_lin,
        "lat_lin": lat_lin
    }
    pd.to_pickle(output_data, output_pkl)
    print(f"Generated and saved {output_pkl}")

def load_pkl(pkl_file):
    """Load preprocessed .pkl file."""
    if not os.path.exists(pkl_file):
        raise FileNotFoundError(f"{pkl_file} does not exist.")
    return pd.read_pickle(pkl_file)

def plot_points(df, zoom_start=12, point_radius=4):
    """
    Plots all lat/lon points from a DataFrame on a folium map.
    
    Parameters:
        df (pd.DataFrame): Must contain 'lat' and 'lon' columns.
        zoom_start (int): Initial zoom level for the map.
        point_radius (int): Radius of the point markers.
    
    Returns:
        folium.Map: Interactive map with plotted points.
    """
    if df.empty or 'lat' not in df.columns or 'lon' not in df.columns:
        raise ValueError("DataFrame must contain 'lat' and 'lon' columns and not be empty.")

    center_point = [df['lat'].mean(), df['lon'].mean()]
    m = folium.Map(location=center_point, zoom_start=zoom_start, control_scale=True)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        folium.CircleMarker(
            location=(row['lat'], row['lon']),
            radius=point_radius,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.7
        ).add_to(m) # change to 'marker_cluster' for clustering when zoomed out

    return m


cities = [
    {"name": "London", 
     "center": [51.5074, -0.1278],
     "output_file": "data/london.pkl",
     "districts": ["N1", "N2", "NW1", "SE1", "SW1", "E1", "W1", "EC1", "WC1"]},

    {"name": "Manchester", 
     "center": [53.4839, -2.2446],
      "districts": ["M1", "M2", "M3", "M4", "M5"],
      "output_file": "data/manchester.pkl"},

    {"name": "Leeds", 
     "center": [53.8008, -1.5491],
     "districts": ["LS1", "LS2", "LS3", "LS4", "LS5", "LS6", "LS7", "LS8", "LS9", "LS10",
            "LS11", "LS12", "LS13", "LS14", "LS15", "LS16", "LS17", "LS18", "LS19",
            "LS20", "LS21", "LS22", "LS23", "LS24", "LS25", "LS26", "LS27", "LS28", "LS29"],
    "output_file": "data/leeds.pkl"},

    {"name": "Bristol", 
     "center": [51.4545, -2.5879],
     "districts": ["BS1", "BS2", "BS3", "BS4", "BS5", "BS6", "BS7", "BS8", "BS9"],
     "output_file": "data/bristol.pkl"},

    {"name": "Birmingham", 
     "center": [52.4862, -1.8904],
      "districts": ["B1", "B2", "B3", "B4", "B5"],
      "output_file": "data/birmingham.pkl"},

    {"name": "Bradford", 
     "center": [53.7950, -1.7594],
       "districts": ["BD1", "BD2", "BD3", "BD4", "BD5"],
       "output_file": "data/bradford.pkl"}
]


def main():
    os.makedirs("data", exist_ok=True)
    
    api_key = get_google_api_key()

    city = next(city for city in cities if city["name"] == "Leeds")

    df = place_markers(city["name"], city["center"], city["districts"])
    
    m = plot_points(df)
    m.save("preprocessing/markers.html")

    df = calculate_travel_times(df, city["center"], api_key, mode="transit")

    # generate_pkl(city["name"], city["center"], city["districts"], city["output_file"], api_key, per_district_sample=3)
if __name__ == "__main__":
    main()
