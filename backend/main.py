from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pandas as pd
import json
import os

app = FastAPI()

#app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("../data/cities.json", "r") as f:
    cities = json.load(f)

@app.get("/")
async def root():
    return {"message": "Commute Map API"}

@app.get("/cities")
async def get_cities():
    return cities

@app.get("/city/{city}")
async def get_city_data(city_name: str):
    city = next((c for c in cities if c["name"].lower() == city_name.lower()), None)
    if city not in cities:
        return {"error": "City not found"}
    
    data_file = city["data_file"]
    if data_file.endswith(".pkl"):
        df = pd.read_pickle(data_file)
        data = df.to_dict(orient="records")
        
    elif data_file.endswith(".json"):
        with open(data_file, "r") as f:
            data = json.load(f)

    return {
        "city": city["name"],
        "center": city["center"]#,
        #"data": data
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
