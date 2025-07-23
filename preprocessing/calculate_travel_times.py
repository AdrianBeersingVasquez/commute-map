from place_markers import load_city_data
from dotenv import load_dotenv
import requests
import pandas as pd
import os
import json
import time

def get_google_maps_api_key():
    load_dotenv()

    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

    if google_maps_api_key:
        print("Google Maps API Key loaded successfully.")
    else:
        print("Google Maps API Key is not set.")

    return google_maps_api_key

def load_coordinates(city_name):
    """Load coordinates from <city>_coordinates.csv."""
    csv_file = f"data/{city_name.lower()}_coordinates.csv"
    try:
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"{csv_file} does not exist")
        df = pd.read_csv(csv_file)
        required_cols = {"lat", "lon"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Invalid CSV structure in {csv_file}. Expected columns: {required_cols}")
        print(f"Loaded {len(df)} coordinates from {csv_file}")
        return df
    except Exception as e:
        print(f"Error loading coordinates: {str(e)}")
        return None


def add_travel_times(df, center, api_key, batch_size=25, output_csv="temp_travel_times.csv"):
    """
    Adds travel times in batches, appending to CSV after each batch.
    
    Parameters:
    - df: DataFrame with 'lat' and 'lon' columns.
    - center: Tuple of (latitude, longitude) for the origin.
    - api_key: Google Maps API key.
    - batch_size: Number of destinations per API request (max 25 for Google Maps).
    - output_csv: Temporary CSV to append results.
    
    Returns:
    - DataFrame with 'lat', 'lon', 'travel_time_mins'.
    """
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    origins = f"{center[0]},{center[1]}"
    result_df = pd.DataFrame(columns=["lat", "lon", "travel_time_mins"])
    
    # Append mode for incremental saving
    if os.path.exists(output_csv):
        result_df = pd.read_csv(output_csv)
        processed_coords = set(zip(result_df["lat"], result_df["lon"]))
        df = df[~df[["lat", "lon"]].apply(tuple, axis=1).isin(processed_coords)]
        print(f"Resuming: {len(result_df)} points already processed, {len(df)} remaining")
    
    # Process in batches
    for start in range(0, len(df), batch_size):
        batch = df.iloc[start:start + batch_size]
        destinations = "|".join(f"{row['lat']},{row['lon']}" for _, row in batch.iterrows())
        params = {
            "origins": origins,
            "destinations": destinations,
            "mode": "transit",
            "key": api_key
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            batch_times = []
            for i, element in enumerate(data["rows"][0]["elements"]):
                try:
                    duration_seconds = element["duration"]["value"]
                    batch_times.append(duration_seconds / 60)
                except (KeyError, TypeError):
                    batch_times.append(None)
            
            batch_result = batch[["lat", "lon"]].copy()
            batch_result["travel_time_mins"] = batch_times
            
            # Append to result_df and save to CSV
            result_df = pd.concat([result_df, batch_result], ignore_index=True)
            result_df.to_csv(output_csv, index=False)
            print(f"Saved batch {start // batch_size + 1}: {len(batch)} points to {output_csv}")
            
            time.sleep(0.1)  # Avoid rate limits
        except Exception as e:
            print(f"Error in batch {start // batch_size + 1}: {str(e)}")
            continue
    
    return result_df.dropna(subset=["travel_time_mins"])


def main(city_name='London'):

    city = load_city_data(city_name)
    os.makedirs("data", exist_ok=True)

    try:
        api_key = get_google_maps_api_key()

        # Load city data and coordinates
        city = load_city_data(city_name)
        if not city:
            raise ValueError("Failed to load city data")
        
        df = load_coordinates(city_name)
        if df is None or df.empty:
            raise ValueError("Failed to load coordinates")
        
        # Pause for inspection
        print(f"Loaded {len(df)} coordinates for {city_name}. Inspect data/{city_name.lower()}_coordinates.csv.")
        proceed = input("Proceed with travel time calculations? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Aborting. Edit the CSV and rerun.")
            return
        
        # Calculate travel times
        output_csv = f"data/{city_name.lower()}_travel_times.csv"
        result_df = add_travel_times(df, city["center"], api_key, batch_size=10, output_csv=output_csv)
        
        if result_df.empty:
            raise ValueError("No valid travel times calculated")
        
        # Save final CSV
        result_df.to_csv(output_csv, index=False)
        print(f"Saved {len(result_df)} travel times to {output_csv}")
    
    except Exception as e:
        print(f"Error in main: {str(e)}")
    

if __name__ == "__main__":
    main('Leeds')
