import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python visualize_pkl.py <path_to_pkl>")
        sys.exit(1)
    visualize_pkl(sys.argv[1])