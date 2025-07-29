from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "dist/assets")), name="assets")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "dist"), html=True), name="frontend")

print("Registering /cities route")  # Debug print
@app.get("/cities")
async def get_cities():
    variations = ["leeds1", "leeds2", "leeds3", "leeds4", "london1", "london2", "london3", "london4", "london5"]
    return {"cities": variations}

@app.get("/static/preprocessing/{filename}")
async def serve_heatmap(filename: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "static", "preprocessing", f"{filename}")

    print(f"Looking for file at: {file_path}")  # Debug log
    print(f"Files in directory: {os.listdir(os.path.join(base_dir, 'static', 'preprocessing'))}")  # List files
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return HTMLResponse(content=content, media_type="text/html")
    return {"error": "File not found"}, 404


@app.get("/")
async def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "dist", "index.html"))

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    return FileResponse(os.path.join(os.path.dirname(__file__), "dist", "index.html"))
