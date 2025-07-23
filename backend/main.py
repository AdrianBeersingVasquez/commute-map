from fastapi import FastAPI, staticfiles
from fastapi.responses import HTMLResponse
import json

app = FastAPI()

app.mount("/static", staticfiles.StaticFiles(directory="static"), name="static")

@app.get("/{city}_heatmap.html")
async def get_heatmap(city: str):
    with open(f"static/preprocessing/{city.lower()}_heatmap.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/cities")
async def get_cities():
    with open("data/cities.json", "r") as f:
        return {"cities": [city["name"].lower() for city in json.load(f)]}
