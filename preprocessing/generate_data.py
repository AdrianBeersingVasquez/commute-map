import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import os

def preprocess_city_data(input_pkl, output_pkl, center):
    """
    Preprocess city data to generate interpolated meshgrid for heatmap.
    
    Args:
        input_pkl (str): Path to input .pkl file with ['city', 'dataframe'].
        output_pkl (str): Path to save preprocessed .pkl file.
        center (list): [latitude, longitude] of city center.
    """
    # Load existing .pkl
    data = pd.read_pickle(input_pkl)
    city_name = data["city"]
    df = pd.DataFrame(data["dataframe"])
    df = df.rename(columns={"travel_time": "travel_time_mins"})  # Adjust if needed

    # Extract data
    lats = df["lat"].values
    lons = df["lon"].values
    times = df["travel_time_mins"].values

    # Interpolation
    grid_res = 200  # Adjust resolution (lower for smaller files, e.g., 100)
    lon_range = lons.max() - lons.min()
    lat_range = lats.max() - lats.min()
    center_lat = (lats.max() + lats.min()) / 2
    aspect_ratio = np.cos(np.radians(center_lat))
    grid_res_lon = int(grid_res * aspect_ratio * lon_range / lat_range)
    lon_lin = np.linspace(lons.min(), lons.max(), grid_res_lon)
    lat_lin = np.linspace(lats.min(), lats.max(), grid_res)
    lon_grid, lat_grid = np.meshgrid(lon_lin, lat_lin)
    grid_z = griddata(
        points=(lons, lats),
        values=times,
        xi=(lon_grid, lat_grid),
        method='linear'
    )
    grid_z = gaussian_filter(grid_z, sigma=1.5)
    grid_z = np.nan_to_num(grid_z, nan=np.nanmax(grid_z))

    # Save preprocessed data
    output_data = {
        "city_name": city_name,
        "center": center,
        "grid_z": grid_z,
        "lon_lin": lon_lin,
        "lat_lin": lat_lin
    }
    pd.to_pickle(output_data, output_pkl)
    print(f"Saved preprocessed data to {output_pkl}")

# City configurations
cities = [
    {"name": "London", "center": [51.5074, -0.1278], "input_file": "data/london.pkl", "output_file": "data/london_processed.pkl"},
    {"name": "Manchester", "center": [53.4839, -2.2446], "input_file": "data/manchester.pkl", "output_file": "data/manchester_processed.pkl"},
    {"name": "Bristol", "center": [51.4545, -2.5879], "input_file": "data/bristol.pkl", "output_file": "data/bristol_processed.pkl"},
    {"name": "Birmingham", "center": [52.4862, -1.8904], "input_file": "data/birmingham.pkl", "output_file": "data/birmingham_processed.pkl"},
    {"name": "Bradford", "center": [53.7950, -1.7594], "input_file": "data/bradford.pkl", "output_file": "data/bradford_processed.pkl"}
]

# Generate .pkl files for all cities
def main():
    os.makedirs("data", exist_ok=True)
    for city in cities:
        if os.path.exists(city["input_file"]):
            preprocess_city_data(city["input_file"], city["output_file"], city["center"])
        else:
            print(f"Input file {city['input_file']} not found. Skipping {city['name']}.")

if __name__ == "__main__":
    main()
