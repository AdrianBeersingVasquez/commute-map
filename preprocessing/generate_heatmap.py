from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from folium.plugins import HeatMap
from place_markers import load_city_data
import numpy as np
import pandas as pd
import folium
import json
import os

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from io import BytesIO
from PIL import Image

def interpolate_meshgrid(df, center_lat, method='linear', grid_res=100):
    """
    Interpolate travel times onto a regular grid.
    
    Args:
        df: DataFrame with 'lat', 'lon', 'travel_time_mins' columns.
        center_lat: Latitude for aspect ratio correction.
        method: Interpolation method ('linear' or 'cubic').
    
    Returns:
        grid_z, lon_lin, lat_lin: Interpolated grid and grid coordinates.
    """
    try:
        lats = df["lat"].values
        lons = df["lon"].values
        times = df["travel_time_mins"].values

        grid_res = grid_res # 200  # Adjust for file size vs. quality
        lon_range = lons.max() - lons.min()
        lat_range = lats.max() - lats.min()
        aspect_ratio = np.cos(np.radians(center_lat))
        grid_res_lon = int(grid_res * aspect_ratio * lon_range / lat_range)
        lon_lin = np.linspace(lons.min(), lons.max(), grid_res_lon)
        lat_lin = np.linspace(lats.min(), lats.max(), grid_res)
        lon_grid, lat_grid = np.meshgrid(lon_lin, lat_lin)

        grid_z = griddata(
            points=(lons, lats),
            values=times,
            xi=(lon_grid, lat_grid),
            method=method # linear or cubic TO TEST OUT 
        )
        grid_z = np.nan_to_num(grid_z, nan=np.nanmax(grid_z))
        grid_z = gaussian_filter(grid_z, sigma=1) # Smooth the grid, test what works best

        print(grid_z)
        return grid_z, lon_lin, lat_lin
    
    except Exception as e:
        print(f"Error interpolating grid: {str(e)}")
        return None, None, None

def plot_travel_heatmap_static(data):
    """Plot static heatmap from .pkl data on a Folium map using ImageOverlay."""
    try:
        if not data:
            raise ValueError("Invalid .pkl data")
        
        # Extract grid data
        grid_z = data["grid_z"]
        lon_lin = data["lon_lin"]
        lat_lin = data["lat_lin"]
        center = data["center"]

        # Normalise travel times (0 to max minutes)
        norm = Normalize(vmin=np.nanmin(grid_z), vmax=np.nanmax(grid_z))
        cmap = cm.get_cmap('viridis')  # Blue (low) to yellow (high)
        
        # Convert grid_z to RGBA image
        grid_normalized = norm(grid_z)
        grid_rgba = cmap(grid_normalized)
        
        # Set transparency for invalid areas (if any)
        alpha = np.ones(grid_z.shape)  # Fully opaque by default
        grid_rgba[..., 3] = alpha  # Set alpha channel
        
        # Convert to uint8 for image
        grid_rgba = (grid_rgba * 255).astype(np.uint8)
        
        # Create PIL image
        img = Image.fromarray(grid_rgba, 'RGBA')
        
        # Save raw image for debugging
        debug_img_path = f"preprocessing/{data['city_name'].lower()}_heatmap_raw.png"
        img.save(debug_img_path)
        print(f"Saved raw heatmap image to {debug_img_path}")
        
        # Create Folium map
        m = folium.Map(location=center, zoom_start=12)
        
        # Add ImageOverlay
        bounds = [[lat_lin.min(), lon_lin.min()], [lat_lin.max(), lon_lin.max()]]
        folium.raster_layers.ImageOverlay(
            image=np.array(img),
            bounds=bounds,
            opacity=0.6,
            interactive=False,
            cross_origin=False,
        ).add_to(m)
        
        # Add colorbar (as HTML)
        colorbar_html = f"""
        <div style="position: fixed; bottom: 50px; right: 50px; width: 30px; height: 200px;
                    border: 2px solid black; z-index: 9999; background: linear-gradient(to top, #0000ff, #00ff00, #ffff00, #ff0000);">
            <div style="position: absolute; bottom: -20px; right: -40px; font-size: 12px;">{np.min(grid_z):.0f} min</div>
            <div style="position: absolute; top: -20px; right: -40px; font-size: 12px;">{np.max(grid_z):.0f} min</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(colorbar_html))
        
        return m
    except Exception as e:
        print(f"Error plotting heatmap: {str(e)}")
        return None

def plot_travel_heatmap(data):
    """Plot heatmap from .pkl data on a Folium map."""
    try:
        if not data:
            raise ValueError("Invalid .pkl data")
        m = folium.Map(location=data["center"], zoom_start=12)
        heat_data = []
        for i, lat in enumerate(data["lat_lin"]):
            for j, lon in enumerate(data["lon_lin"]):
                intensity = data["grid_z"][i, j]
                if not np.isnan(intensity):
                    heat_data.append([lat, lon, intensity])
        HeatMap(heat_data, radius=10).add_to(m)
        return m
    except Exception as e:
        print(f"Error plotting heatmap: {str(e)}")
        return None

def load_travel_times(city_name):
    """Load travel times from <city>_travel_times.csv."""
    csv_file = f"data/{city_name.lower()}_travel_times.csv"
    try:
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"{csv_file} does not exist")
        df = pd.read_csv(csv_file)
        required_cols = {"lat", "lon", "travel_time_mins"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Invalid CSV structure in {csv_file}. Expected columns: {required_cols}")
        print(f"Loaded {len(df)} travel times from {csv_file}")
        return df
    except Exception as e:
        print(f"Error loading travel times: {str(e)}")
        return None

def save_pkl(city_name, center, grid_z, lon_lin, lat_lin, output_pkl):
    """Save preprocessed .pkl for a city."""
    
    try:
        output_data = {
            "city_name": city_name,
            "center": center,
            "grid_z": grid_z,
            "lon_lin": lon_lin,
            "lat_lin": lat_lin
        }
        pd.to_pickle(output_data, output_pkl)
        print(f"Generated and saved {output_pkl}")
    except Exception as e:
        print(f"Error saving {output_pkl}: {str(e)}")

def load_pkl(pkl_file):
    """Load preprocessed .pkl file."""
    try:
        if not os.path.exists(pkl_file):
            raise FileNotFoundError(f"{pkl_file} does not exist.")
        data = pd.read_pickle(pkl_file)
        expected_keys = {"city_name", "center", "grid_z", "lon_lin", "lat_lin"}
        if not all(key in data for key in expected_keys):
            raise ValueError(f"Invalid .pkl structure in {pkl_file}")
        return data
    except Exception as e:
        print(f"Error loading {pkl_file}: {str(e)}")
        return None

def main(city_name, interpolation_method, grid_res):
    os.makedirs("data", exist_ok=True)
    os.makedirs("preprocessing", exist_ok=True)

    try:
        # Load city data and travel times
        city = load_city_data(city_name)
        if not city:
            raise ValueError("Failed to load city data")
        
        pkl_file = f"data/{city_name.lower()}_heatmap.pkl"
        if os.path.exists(pkl_file):
            print(f"{pkl_file} already exists. Loading existing heatmap.")
            data = load_pkl(pkl_file)
            if not data:
                raise ValueError("Failed to load existing .pkl file")
        else:
            df = load_travel_times(city_name)
            if df is None or df.empty:
                raise ValueError("Failed to load travel times")
            
            # Interpolate
            grid_z, lon_lin, lat_lin = interpolate_meshgrid(df, city["center"][0], method=interpolation_method, grid_res=grid_res)
            if grid_z is None:
                raise ValueError("Failed to interpolate grid")
            
            # Save .pkl
            save_pkl(city["name"], city["center"], grid_z, lon_lin, lat_lin, pkl_file)
            data = load_pkl(pkl_file)
            if not data:
                raise ValueError("Failed to load newly created .pkl file")
        
        # Plot heatmap
        m = plot_travel_heatmap_static(data)
        #m = plot_travel_heatmap(data)

        if m:
            heatmap_file = f"preprocessing/{city_name.lower()}_heatmap.html"
            m.save(heatmap_file)
            print(f"Saved heatmap to {heatmap_file}")
        else:
            raise ValueError("Failed to plot heatmap")
        
        print(f"Completed processing for {city_name}")

        print(city["center"])

    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main('Leeds', 'linear', 10000)
