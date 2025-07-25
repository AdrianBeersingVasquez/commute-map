import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import folium
from matplotlib.colors import Normalize
import matplotlib.cm as cm
from PIL import Image
from dotenv import load_dotenv

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

def add_contours(m, grid_z, lon_lin, lat_lin, contour_levels, cmap_color):
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
        cmap = plt.get_cmap(cmap_color)  # Updated colormap access
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

def plot_travel_heatmap_static(data, contour_levels, cmap_color, show_colorbar=True):
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
        cmap = plt.get_cmap(cmap_color)  # Updated colormap access
        
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
    
        # Calculates aesthetic center (not actual centre)
        min_idx = np.unravel_index(np.argmin(grid_z), grid_z.shape)
        y_min, x_min = min_idx
        y_max = len(lat_lin) - 1 - y_min  # Reverse the y-index
        center_lat = lat_lin[y_max] 
        center_lon = lon_lin[x_min]

        print(f"Center coordinates: ({center_lat}, {center_lon})")
        # Create Folium map
        m = folium.Map(location=[center_lat, center_lon],
                       zoom_start=11,
                       zoom_control=False,
                       max_bounds=True,
                       min_lat=lat_lin.min(),
                       min_lon=lon_lin.min(),
                       max_lat=lat_lin.max(),
                       max_lon=lon_lin.max())
        m.options['attributionControl'] = False
        m.options['layerControl'] = False

        jawg_api_key = get_jawg_api_key()
        folium.TileLayer(
            tiles=f'https://a.tile.jawg.io/jawg-dark/{{z}}/{{x}}/{{y}}.png?access-token={jawg_api_key}',
            attr='&copy; <a href="https://www.jawg.io/">Jawg Maps</a> contributors',
            control=False
        ).add_to(m)
        
        # Add ImageOverlay
        bounds = [[lat_lin.min(), lon_lin.min()], [lat_lin.max(), lon_lin.max()]]
        folium.raster_layers.ImageOverlay(
            image=np.array(img),
            bounds=bounds,
            opacity=0.5,
            interactive=False,
            cross_origin=False,
        ).add_to(m)
        
        # Add contours
        if contour_levels:
            m = add_contours(m, grid_z, lon_lin, lat_lin, contour_levels, cmap_color)

        # Add colorbar
        if show_colorbar:
            m = add_colorbar(m, grid_z, grid_z_log, cmap_color)

        return m
    except Exception as e:
        print(f"Error plotting heatmap: {str(e)}")
        return None
    
def add_colorbar(m, grid_z, grid_z_log, cmap_color):
    print("Adding colorbar to map...")
    # Add colorbar with original travel time scale

    colormap = plt.get_cmap(cmap_color)
    num_colors = 100
    colors = [colormap(i / num_colors) for i in range(num_colors)]

    gradient = 'linear-gradient(to top, ' + ', '.join(
    [f'rgba({int(c[0]*255)}, {int(c[1]*255)}, {int(c[2]*255)}, {c[3]})' for c in colors]) + ')'

    min_time = np.nanmin(grid_z)
    max_time = np.nanmax(grid_z)
    colorbar_html = f"""
    <div style="position: fixed; bottom: 20px; left: 20px; width: 15px; height: 100px;
                border: 2px solid black; z-index: 9999; background: {gradient};">
        <div style="position: absolute; bottom: -20px; right: -40px; font-size: 12px; color: white;">{min_time:.0f} min</div>
        <div style="position: absolute; top: 100px; right: -40px; font-size: 12px; color: white;">
            {np.expm1(lerp(np.nanmin(grid_z_log), np.nanmax(grid_z_log), 0.33)):.0f} min</div>
        <div style="position: absolute; top: 50px; right: -40px; font-size: 12px; color: white;">
            {np.expm1(lerp(np.nanmin(grid_z_log), np.nanmax(grid_z_log), 0.67)):.0f} min</div>
        <div style="position: absolute; top: -20px; right: -40px; font-size: 12px; color: white;">{max_time:.0f} min</div>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(colorbar_html))

    return m


def get_jawg_api_key():
    load_dotenv()

    jawg_api_key = os.getenv("JAWG_API_KEY")

    if jawg_api_key:
        print("JAWG API Key loaded successfully.")
    else:
        print("JAWG API Key is not set.")

    return jawg_api_key

def main(city_name, zone):
    pkl_file = f"data/{city_name.lower()}_heatmap{zone}.pkl"
    
    data = load_pkl(pkl_file)
    
    # visualize_pkl(pkl_file)

    m = plot_travel_heatmap_static(data, contour_levels=[10, 20, 30, 45, 60, 120], cmap_color='magma_r', show_colorbar=False)

    if m:
        heatmap_file = f"preprocessing/visualize_heatmap.html"
        m.save(heatmap_file)
        print(f"Saved heatmap to {heatmap_file}")
    
    print("Grid_z histogram:", np.histogram(data['grid_z'], bins=10)[0])

if __name__ == "__main__":
    main('Leeds', 'SOUTH')
# done mw (actually beeston), train, NE (actually stourton), SOUTH (actually burley)
