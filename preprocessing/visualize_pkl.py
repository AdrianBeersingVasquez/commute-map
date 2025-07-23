import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import folium
from matplotlib.colors import Normalize
import matplotlib.cm as cm
from PIL import Image

from generate_heatmap import load_pkl

def lerp(a, b, t):
    return a + t * (b - a)

def visualize_pkl(pkl_file):
    """
    Visualize the heatmap from a preprocessed .pkl file.
    
    Args:
        pkl_file (str): Path to .pkl file.
    """
    # Load data
    data = pd.read_pickle(pkl_file)
    city_name = data["city_name"]
    center = data["center"]
    grid_z = data["grid_z"]
    lon_lin = data["lon_lin"]
    lat_lin = data["lat_lin"]

    # Plot heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(
        grid_z,
        extent=[lon_lin.min(), lon_lin.max(), lat_lin.min(), lat_lin.max()],
        origin='lower',
        cmap='viridis',
        interpolation='nearest'
    )
    plt.colorbar(label='Travel Time (minutes)')
    plt.scatter(center[1], center[0], c='red', marker='x', s=200, label='City Center')
    plt.title(f"Travel Time Heatmap for {city_name}")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.show()

def add_contours(m, grid_z, lon_lin, lat_lin, contour_levels):
    """
    Add contour lines to a Folium map at specified travel time levels.
    
    Args:
        m: Folium map object.
        grid_z: 2D array of interpolated travel times.
        lon_lin: 1D array of longitude grid points.
        lat_lin: 1D array of latitude grid points.
        contour_levels: List of travel times (in minutes) for contours.
    
    Returns:
        Updated Folium map with contours.
    """
    try:
        # Filter valid contour levels
        valid_levels = [level for level in contour_levels if np.nanmin(grid_z) <= level <= np.nanmax(grid_z)]
        if not valid_levels:
            print("No valid contour levels within grid_z range")
            return m
        
        print(f"Adding contours at levels: {valid_levels}")
        
        # Create figure for contour plotting
        fig, ax = plt.subplots()
        cs = ax.contour(lon_lin, lat_lin, grid_z, levels=valid_levels)       
        
        # Debug: Save contour plot
        plt.savefig(f"preprocessing/{m.get_name()}_contours_debug.png")
        print(f"Saved contour debug plot to preprocessing/{m.get_name()}_contours_debug.png")
        
        # Debug: Inspect segments
        print(f"Contour segments per level: {[len(segs) for segs in cs.allsegs]}")

        # Define colors for contours
        cmap = plt.get_cmap('viridis')  # Updated colormap access
        norm = Normalize(vmin=min(valid_levels), vmax=max(valid_levels))
        contour_colors = [cmap(norm(level)) for level in valid_levels]
        
        # Add contours to Folium map
        contour_group = folium.FeatureGroup(name="Contours")
        for level, segments, color in zip(valid_levels, cs.allsegs, contour_colors):
            print(f"Processing contour level {level:.2f} with {len(segments)} segments")
            for path in segments:
                if len(path) > 1:
                    # Convert path vertices to lat/lon
                    x, y = path[:, 0], path[:, 1]
                    x_idx = (x - lon_lin.min()) / (lon_lin.max() - lon_lin.min()) * (len(lon_lin) - 1)
                    y_idx = (y - lat_lin.min()) / (lat_lin.max() - lat_lin.min()) * (len(lat_lin) - 1)
                    y_idx = len(lat_lin) - 1 - y_idx
                    coords = [
                        [np.interp(y_i, range(len(lat_lin)), lat_lin), np.interp(x_i, range(len(lon_lin)), lon_lin)]
                        for x_i, y_i in zip(x_idx, y_idx)
                        if 0 <= x_i <= len(lon_lin) - 1 and 0 <= y_i <= len(lat_lin) - 1
                    ]
                    if len(coords) > 1:
                        print(f"Adding PolyLine with {len(coords)} points")
                        folium.PolyLine(
                            locations=coords,
                            color=f'rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)})',
                            weight=4,
                            opacity=0.9,
                            popup=f"{level:.0f} min"
                        ).add_to(contour_group)
        
        contour_group.add_to(m)
        plt.close(fig)
        return m
    except Exception as e:
        print(f"Error adding contours: {str(e)}")
        return m

def plot_travel_heatmap_static(data, contour_levels):
    """Plot static heatmap from .pkl data on a Folium map using ImageOverlay with log transformation."""
    try:
        if not data:
            raise ValueError("Invalid .pkl data")
        
        # Extract grid data
        grid_z = data["grid_z"]
        lon_lin = data["lon_lin"]
        lat_lin = data["lat_lin"]
        center = data["center"]
        
        # Debug: Print grid_z stats
        print("Grid_z min/max:", np.nanmin(grid_z), np.nanmax(grid_z))
        
        # Apply log transformation
        grid_z_log = np.log1p(grid_z)
        print("Log-transformed grid_z min/max:", np.nanmin(grid_z_log), np.nanmax(grid_z_log))
        
        # Normalize log-transformed data
        norm = Normalize(vmin=np.nanmin(grid_z_log), vmax=np.nanmax(grid_z_log))
        cmap = plt.get_cmap('viridis')  # Updated colormap access
        
        # Convert log-transformed grid_z to RGBA image
        grid_normalized = norm(grid_z_log)
        grid_rgba = cmap(grid_normalized)
        
        # Set transparency for invalid areas
        alpha = np.ones(grid_z.shape)
        grid_rgba[..., 3] = alpha
        
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
            opacity=0.4,
            interactive=False,
            cross_origin=False,
        ).add_to(m)
        
        # Add contours
        if contour_levels:
            m = add_contours(m, grid_z, lon_lin, lat_lin, contour_levels)

        # Add layer control
        folium.LayerControl().add_to(m)
        
        
        # Add colorbar with original travel time scale
        min_time = np.nanmin(grid_z)
        max_time = np.nanmax(grid_z)
        colorbar_html = f"""
        <div style="position: fixed; bottom: 50px; right: 50px; width: 30px; height: 200px;
                    border: 2px solid black; z-index: 9999; background: linear-gradient(to top, #0000ff, #00ff00, #ffff00, #ff0000);">
            <div style="position: absolute; bottom: -20px; right: -40px; font-size: 12px;">{min_time:.0f} min</div>
            <div style="position: absolute; top: 100px; right: -40px; font-size: 12px;">
                {np.expm1(lerp(np.nanmin(grid_z_log), np.nanmax(grid_z_log), 0.33)):.0f} min</div>
            <div style="position: absolute; top: 50px; right: -40px; font-size: 12px;">
                {np.expm1(lerp(np.nanmin(grid_z_log), np.nanmax(grid_z_log), 0.67)):.0f} min</div>
            <div style="position: absolute; top: -20px; right: -40px; font-size: 12px;">{max_time:.0f} min</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(colorbar_html))
        
        return m
    except Exception as e:
        print(f"Error plotting heatmap: {str(e)}")
        return None

def main(city_name, zone):
    pkl_file = f"data/{city_name.lower()}_heatmap{zone}.pkl"
    
    data = load_pkl(pkl_file)
    
    # visualize_pkl(pkl_file)

    m = plot_travel_heatmap_static(data, contour_levels=[0.5, 15, 30, 60, 120])

    if m:
        heatmap_file = f"preprocessing/visualize_heatmap.html"
        m.save(heatmap_file)
        print(f"Saved heatmap to {heatmap_file}")
    
    print("Grid_z histogram:", np.histogram(data['grid_z'], bins=10)[0])

if __name__ == "__main__":
    main('Leeds', '')